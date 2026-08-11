import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from pydantic import SkipValidation

from aire_prime.agents import AgentResponse, MessageKind
from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel
from aire_prime.exchange.realize import RealizationContext, Realizer
from aire_prime.experiments.e2.ablations import (
    E2AblationEvidence,
    build_ablation_packets,
    evaluate_e2_ablations,
)
from aire_prime.experiments.e2.baselines import (
    E2BaselineResult,
    build_baseline_packets,
    correctness_samples,
    evaluate_baselines,
    resources,
)
from aire_prime.experiments.e2.discoverer import (
    discover_operator,
    fixed_size_packet,
    operator_constructor,
    run_contained_discovery,
)
from aire_prime.experiments.e2.recipient import (
    RecipientExchange,
    ResourceObservationRecord,
    run_recipient,
)
from aire_prime.experiments.e2.world import CausalSplit, generate_causal_world
from aire_prime.grc.constructor import ResourceBudget
from aire_prime.grc.types import SpaceKind, StructuralType
from aire_prime.measurement.comparison import ComparisonArm, ComparisonStatus, compare_arms
from aire_prime.measurement.decision import (
    CandidateSamples,
    ControlContract,
    ControlSamples,
    ImprovementDecision,
    ProtectedContract,
    ProtectedDimension,
    ProtectedRequirement,
    decide_improvement,
)
from aire_prime.objects import CanonicalObject
from aire_prime.objects.contracts import BridgeContract, EvaluationContract, RealityTier
from aire_prime.objects.evidence import EvidenceState, GroundingClass, OccurrenceMaturity
from aire_prime.objects.proposals import MetricProposal, RealityObject, SenseProposal
from aire_prime.objects.reports import ImprovementReport, OccurrenceReport
from aire_prime.registry.lifecycle import LifecycleState
from aire_prime.registry.store import RegistryStore

PACKET_BYTES = 4096
REQUIRED_E2_GATES = (
    "causal-ablation",
    "fresh-recipient",
    "heldout-gain",
    "independent-reproduction",
    "matched-controls",
    "transformed-generalization",
)


class E2Report(CanonicalObject):
    classification: str
    evidence_state: str
    seed: int
    sense_proposal_id: str
    reality_object_id: str
    evaluation_contract_id: str
    bridge_contract_id: str
    occurrence_report_id: str
    improvement_report_id: str
    measurement_decision_id: str
    transfer_packet_bytes: int
    heldout_accuracy: float
    transformed_accuracy: float
    independent_reproduction_accuracy: float
    passed_gates: tuple[str, ...]
    failed_gates: tuple[str, ...] = ()


class E2RunResult(FrozenModel):
    receiver_id: str
    prediction_artifact_id: str
    agent_response: AgentResponse
    heldout_accuracy: float
    transformed_accuracy: float
    independent_reproduction_accuracy: float
    transfer_packet_bytes: int
    baselines: tuple[E2BaselineResult, ...]
    ablation: E2AblationEvidence
    measurement_decision: ImprovementDecision
    evaluation_contract: EvaluationContract
    occurrence_report: OccurrenceReport
    improvement_report: SkipValidation[ImprovementReport]
    report: E2Report
    registry_head: str
    resource_observations: tuple[ResourceObservationRecord, ...] = ()


def _created_at(seed: int) -> datetime:
    return datetime(2026, 2, 1, tzinfo=UTC) + timedelta(seconds=seed)


def _task_payload(*splits: CausalSplit) -> dict[str, object]:
    return {
        "task": "new-controller-heldout-control",
        "episodes": tuple(
            {
                "episode_id": episode.episode_id,
                "raw_observation": episode.raw_observation,
                "probe_success": episode.probe_success,
                "physical_to_external": split.action_label_map,
            }
            for split in splits
            for episode in split.episodes
        ),
    }


def _response_valid(exchange: RecipientExchange) -> bool:
    return (
        exchange.response.message_kind is MessageKind.RESPONSE
        and exchange.response.content_ids == (exchange.expected_artifact_id,)
    )


def classify_e2(gates: dict[str, bool]) -> tuple[OccurrenceMaturity, tuple[str, ...]]:
    if set(gates) != set(REQUIRED_E2_GATES):
        raise ValueError("classification requires the exact E2 gate set")
    failed = tuple(gate for gate in REQUIRED_E2_GATES if not gates[gate])
    if not failed:
        return OccurrenceMaturity.TRANSFERRED, ()
    if all(
        gates[gate]
        for gate in (
            "heldout-gain",
            "causal-ablation",
            "matched-controls",
            "transformed-generalization",
        )
    ):
        return OccurrenceMaturity.GENERALIZED, failed
    if gates["heldout-gain"] and gates["causal-ablation"]:
        return OccurrenceMaturity.CAUSALLY_USED, failed
    if gates["heldout-gain"]:
        return OccurrenceMaturity.ASSOCIATED, failed
    return OccurrenceMaturity.CLAIMED, failed


def _write(path: Path, value: object) -> None:
    payload = value.model_dump(mode="json") if isinstance(value, CanonicalObject) else value
    path.write_bytes(canonical_bytes(payload))


def run_e2(*, seed: int, output: Path, forced_failures: tuple[str, ...] = ()) -> E2RunResult:
    unknown = set(forced_failures) - set(REQUIRED_E2_GATES)
    if unknown:
        raise ValueError(f"unknown forced E2 failures: {sorted(unknown)}")
    if output.exists() and any(output.iterdir()):
        raise ValueError("E2 output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    created_at = _created_at(seed)
    world = generate_causal_world(seed)
    reproduction_world = generate_causal_world(seed + 10_000)

    # Freeze expected artifacts and all control packets before contained discovery runs.
    discovery_packet = world.discovery_packet()
    expected_operator = discover_operator(discovery_packet)
    constructor = operator_constructor(expected_operator)
    packet = fixed_size_packet(
        constructor=constructor,
        training_commitment=world.train.content_id,
        variant="candidate",
        size=PACKET_BYTES,
    )
    packet_id = content_id(packet)
    combined_task = _task_payload(world.hidden_test, world.transformed_test)
    baseline_packets = build_baseline_packets(packet_bytes=PACKET_BYTES)
    ablation_packets = build_ablation_packets(constructor=constructor, packet_bytes=PACKET_BYTES)
    reproduction_expected_operator = discover_operator(reproduction_world.discovery_packet())
    reproduction_constructor = operator_constructor(reproduction_expected_operator)
    reproduction_packet = fixed_size_packet(
        constructor=reproduction_constructor,
        training_commitment=reproduction_world.train.content_id,
        variant="candidate-reproduction",
        size=PACKET_BYTES,
    )
    reproduction_task = _task_payload(
        reproduction_world.hidden_test, reproduction_world.transformed_test
    )
    candidate_resources = resources(
        PACKET_BYTES, len(world.hidden_test.episodes) + len(world.transformed_test.episodes)
    )
    candidate_arm = ComparisonArm(
        arm_id="arm:e2-operator",
        resources=candidate_resources,
        observation_access=("raw-observation", "probe-intervention", "probe-outcome"),
        receiver_prior_id="prior:none",
    )
    control_arms = tuple(
        ComparisonArm(
            arm_id=f"arm:e2-{kind}",
            resources=resources(
                PACKET_BYTES, len(world.hidden_test.episodes) + len(world.transformed_test.episodes)
            ),
            observation_access=candidate_arm.observation_access,
            receiver_prior_id="prior:none",
        )
        for kind, _ in baseline_packets
    )
    control_contract = ControlContract(
        required_control_ids=tuple(arm.content_id for arm in control_arms)
    )
    protected_contract = ProtectedContract(
        requirements=(ProtectedRequirement(name="heldout-accuracy-floor", floor=0.9),)
    )
    evaluation_contract = EvaluationContract(
        created_at=created_at,
        validity_region=("E2", "simulated"),
        claim="intervention-derived probe operator transfers to held-out simulated control",
        baseline_ids=tuple(content_id(packet) for _, packet in baseline_packets),
        hidden_test_ids=(
            world.hidden_test.content_id,
            world.transformed_test.content_id,
            reproduction_world.hidden_test.content_id,
            reproduction_world.transformed_test.content_id,
        ),
        controls=(
            *(f"primary-split:{split.name}:{split.content_id}" for split in world.splits),
            *(
                f"reproduction-split:{split.name}:{split.content_id}"
                for split in reproduction_world.splits
            ),
            f"candidate-packet:{packet_id}",
            f"reproduction-packet:{content_id(reproduction_packet)}",
            f"task:{content_id(combined_task)}",
            f"reproduction-task:{content_id(reproduction_task)}",
            f"control-contract:{control_contract.content_id}",
            f"protected-contract:{protected_contract.content_id}",
            *(
                f"baseline-packet:{content_id(control_packet)}"
                for _, control_packet in baseline_packets
            ),
            *(
                f"ablation-packet:{content_id(ablation_packet)}"
                for _, _, ablation_packet in ablation_packets
            ),
            "evaluator:aire:e2-contained-heldout-control:v3",
            "identical-task-and-contained-recipient",
            "fixed-4096-byte-packets",
            "seed-isolated-reproduction",
        ),
        ablations=(
            "targeted-latent-operator",
            "equal-size-random-subspace",
            "activation-permutation",
            "representation-replacement",
        ),
        resource_budget=(
            ("packet_bytes", float(PACKET_BYTES)),
            ("recipient_interactions_per_arm", 1.0),
            ("external_calls", 0.0),
        ),
        decision_rule="all exact E2 gates pass; missing or unexpected gates are invalid",
        replication_requirements=("distinct-seed-contained-discovery-and-recipient",),
    )
    discovery = run_contained_discovery(
        training_packet=discovery_packet, claim_id=evaluation_contract.content_id
    )
    operator = discovery.operator
    if operator != expected_operator:
        raise RuntimeError("contained operator differs from frozen validator commitment")
    baselines = evaluate_baselines(
        packets=baseline_packets,
        hidden=world.hidden_test,
        transformed=world.transformed_test,
        task_payload=combined_task,
        claim_id=evaluation_contract.content_id,
        object_id=packet_id,
    )

    sense = SenseProposal(
        created_at=created_at,
        validity_region=("E2", "simulated"),
        distinction="probe-conditioned latent transition class",
        domain="seeded binary causal control world",
        probe="intervene on both actions, retain outcomes, choose later control actions",
        transformations=("held-out episodes", "action-label permutation"),
        expected_utility=("held-out prediction", "new-controller control"),
        grounding_claim=GroundingClass.UNGROUNDED,
    )
    reality = RealityObject(
        created_at=created_at,
        validity_region=("E2", "simulated"),
        state_space=StructuralType(kind=SpaceKind.VECTOR, dimensions=(1,)),
        interfaces=operator.interface,
        transformations=("action-label rebinding", "new-controller use"),
        invariants=("probe-response mapping",),
        constructor_id=content_id(constructor.to_wire()),
        tests=(world.hidden_test.content_id, world.transformed_test.content_id),
        resource_requirements=("fixed packet bytes", "one recipient interaction per arm"),
    )
    bridge = BridgeContract(
        created_at=created_at,
        validity_region=("E2", "simulated"),
        reality_tier=RealityTier.SIMULATED,
        authority_id="authority:e2-validator",
        authorization_boundary="offline seeded simulation only",
        observable_consequences=("held-out control accuracy",),
        approved_instruments=("deterministic hidden evaluator",),
        resource_envelope=(("packet_bytes", float(PACKET_BYTES)),),
        protected_boundaries=("no physical-world claim", "no QEC claim"),
        permitted_status_claims=(GroundingClass.SIMULATED,),
    )

    exchange = run_recipient(
        operator_payload=packet,
        task_payload=combined_task,
        claim_id=evaluation_contract.content_id,
        object_id=reality.content_id,
        receiver_id="agent:e2-recipient-fresh",
    )
    candidate_samples = (
        correctness_samples(
            hidden=world.hidden_test,
            transformed=world.transformed_test,
            actions=exchange.expected_actions,
        )
        if _response_valid(exchange)
        else (0.0,) * 80
    )
    heldout_count = len(world.hidden_test.episodes)
    heldout_accuracy = sum(candidate_samples[:heldout_count]) / heldout_count
    transformed_accuracy = sum(candidate_samples[heldout_count:]) / len(
        world.transformed_test.episodes
    )

    reproduction_discovery = run_contained_discovery(
        training_packet=reproduction_world.discovery_packet(),
        claim_id=evaluation_contract.content_id,
    )
    if reproduction_discovery.operator != reproduction_expected_operator:
        raise RuntimeError("contained reproduction differs from frozen validator commitment")
    reproduction = run_recipient(
        operator_payload=reproduction_packet,
        task_payload=reproduction_task,
        claim_id=evaluation_contract.content_id,
        object_id=reality.content_id,
        receiver_id="agent:e2-reproducer-seed-isolated",
    )
    reproduction_samples = (
        correctness_samples(
            hidden=reproduction_world.hidden_test,
            transformed=reproduction_world.transformed_test,
            actions=reproduction.expected_actions,
        )
        if _response_valid(reproduction)
        else (0.0,) * 80
    )
    reproduction_accuracy = sum(reproduction_samples) / len(reproduction_samples)

    resource_observations = tuple(
        ResourceObservationRecord(arm=arm, observation=exchange.resource_observation)
        for arm, exchange in (
            ("candidate", exchange),
            *(
                (f"baseline:{baseline.kind}", baseline.exchange)
                for baseline in baselines
            ),
            ("reproduction", reproduction),
        )
    )

    controls = tuple(
        ControlSamples(
            name=baseline.kind,
            samples=baseline.samples,
            control_arm_id=arm.content_id,
            measurement_artifact_id=baseline.measurement_artifact_id,
            candidate_arm=candidate_arm,
            control_arm=arm,
            comparison=compare_arms(candidate_arm, arm),
        )
        for baseline, arm in zip(baselines, control_arms, strict=True)
    )
    protected = (
        ProtectedDimension(
            name="heldout-accuracy-floor",
            samples=candidate_samples[:heldout_count],
            floor=0.9,
            measurement_artifact_id=content_id(
                {
                    "samples": candidate_samples[:heldout_count],
                    "split": world.hidden_test.content_id,
                }
            ),
        ),
    )
    measurement_decision = decide_improvement(
        candidate_samples=CandidateSamples(
            name="E2-control-accuracy",
            samples=candidate_samples,
            candidate_arm_id=candidate_arm.content_id,
            measurement_artifact_id=exchange.expected_artifact_id,
            metric_id="metric:e2-per-episode-control-accuracy:v2",
        ),
        controls=controls,
        control_contract=control_contract,
        protected_dimensions=protected,
        protected_contract=protected_contract,
        delta=0.1,
        alpha=0.05,
        seed=seed,
        bootstrap_iterations=500,
    )
    candidate_accuracy = sum(candidate_samples) / len(candidate_samples)
    ablation = evaluate_e2_ablations(
        packets=ablation_packets,
        operator_packet_id=packet_id,
        seed=seed,
        hidden=world.hidden_test,
        transformed=world.transformed_test,
        task_payload=combined_task,
        claim_id=evaluation_contract.content_id,
        object_id=reality.content_id,
        candidate_accuracy=candidate_accuracy,
    )

    gates = {
        "causal-ablation": ablation.targeted_drop > max(ablation.sham_drops),
        "fresh-recipient": _response_valid(exchange),
        "heldout-gain": heldout_accuracy > max(b.hidden_accuracy for b in baselines)
        and measurement_decision.status.value == "provisional",
        "independent-reproduction": reproduction_accuracy == 1.0 and _response_valid(reproduction),
        "matched-controls": all(
            control.comparison.status is ComparisonStatus.VALID for control in controls
        ),
        "transformed-generalization": transformed_accuracy == 1.0,
    }
    for gate in forced_failures:
        gates[gate] = False
    maturity, failed_gates = classify_e2(gates)
    passed_gates = tuple(gate for gate in REQUIRED_E2_GATES if gates[gate])

    receipts = tuple(
        Realizer(clock=lambda: 0.0)
        .realize(
            constructor,
            RealizationContext(
                receiver_id="agent:e2-recipient-fresh",
                local_realization_id=operator.content_id,
                inputs={"probe_success": np.array([float(probe)])},
                budget=ResourceBudget(
                    max_operations=2, max_elements=8, max_output_bytes=128, max_elapsed_seconds=1.0
                ),
                contract_tests=("allow-listed-lookup", f"probe:{probe}"),
            ),
        )
        .receipt
        for probe in (0, 1)
    )
    metric = MetricProposal(
        created_at=created_at,
        validity_region=("E2", "simulated"),
        dimension="held-out-control-accuracy",
        measurement_procedure="per-episode correctness from contained recipient response",
        ordering="higher-is-better",
        baseline_ids=tuple(b.packet_digest for b in baselines),
        invariances=("action-label permutation with declared rebinding",),
        consequence="simulated controller selects rewarding action",
        falsifiers=("targeted ablation has no effect", "transformed accuracy fails"),
        anti_gaming_tests=("hidden goals", "matched controls", "protected floor"),
        complexity_cost=float(PACKET_BYTES),
        expiration_conditions=("world generator, evaluator, or operator changes",),
    )
    occurrence = OccurrenceReport(
        created_at=created_at,
        validity_region=("E2", "simulated"),
        proposal_id=sense.content_id,
        contract_id=evaluation_contract.content_id,
        validator_id="agent:e2-validator",
        evidence_state=EvidenceState(occurrence=maturity, grounding=GroundingClass.SIMULATED),
        independence_evidence=(
            ("contained discovery and fresh recipient identities",)
            if gates["fresh-recipient"]
            else ()
        ),
        causal_evidence=(
            ("executable targeted ablation exceeds executable shams",)
            if gates["causal-ablation"]
            else ()
        ),
        generalization_evidence=(
            ("held-out action-label transformation passed",)
            if gates["transformed-generalization"]
            else ()
        ),
        transfer_evidence=(
            (f"recipient-response:{exchange.response.content_id}",)
            if gates["fresh-recipient"]
            else ()
        ),
        replication_evidence=(
            (f"distinct-seed-response:{reproduction.response.content_id}",)
            if gates["independent-reproduction"]
            else ()
        ),
        known_failures=failed_gates,
        evidence_attachments=(
            packet_id,
            evaluation_contract.content_id,
            measurement_decision.content_id,
            discovery.response.content_id,
        ),
        expiration_conditions=("E2 contract or evaluator changes",),
        resource_measurements=(
            ("packet_bytes", float(PACKET_BYTES)),
            ("discovery_interactions", 2.0),
            ("recipient_interactions", 2.0),
        ),
    )
    improvement = ImprovementReport.model_validate(
        {
            "created_at": created_at,
            "validity_region": ("E2", "simulated"),
            "metric_proposal_id": metric.content_id,
            "evaluation_contract_id": evaluation_contract.content_id,
            "occurrence_report_id": occurrence.content_id,
            "validator_id": "agent:e2-validator",
            "claimed_grounding": GroundingClass.SIMULATED,
            "improvement_vector": (
                ("heldout_accuracy", heldout_accuracy),
                ("transformed_accuracy", transformed_accuracy),
            ),
            "baseline_results": tuple((b.kind, b.transformed_accuracy) for b in baselines),
            "resource_measurements": (("fixed_packet_envelope_bytes", float(PACKET_BYTES)),),
            "protected_effects": (("heldout_accuracy_floor", heldout_accuracy),),
            "adversarial_results": tuple(
                x
                for ok, x in (
                    (gates["causal-ablation"], "executable targeted ablation exceeds shams"),
                    (gates["transformed-generalization"], "declared action labels rebound"),
                )
                if ok
            ),
            "replications": (
                (reproduction.response.content_id,) if gates["independent-reproduction"] else ()
            ),
            "known_failures": failed_gates,
            "evidence_attachments": (measurement_decision.content_id, ablation.content_id),
            "expiration_conditions": ("E2 contract or evaluator changes",),
        },
        context={"occurrence_reports": {occurrence.content_id: occurrence}},
    )
    report = E2Report(
        created_at=created_at,
        validity_region=("E2", "simulated"),
        classification=(
            "simulated-alien-sense-transfer"
            if maturity is OccurrenceMaturity.TRANSFERRED
            else "simulated-alien-sense-transfer-not-established"
        ),
        evidence_state=EvidenceState(
            occurrence=maturity, grounding=GroundingClass.SIMULATED
        ).display,
        seed=seed,
        sense_proposal_id=sense.content_id,
        reality_object_id=reality.content_id,
        evaluation_contract_id=evaluation_contract.content_id,
        bridge_contract_id=bridge.content_id,
        occurrence_report_id=occurrence.content_id,
        improvement_report_id=improvement.content_id,
        measurement_decision_id=measurement_decision.content_id,
        transfer_packet_bytes=PACKET_BYTES,
        heldout_accuracy=heldout_accuracy,
        transformed_accuracy=transformed_accuracy,
        independent_reproduction_accuracy=reproduction_accuracy,
        passed_gates=passed_gates,
        failed_gates=failed_gates,
    )

    objects: tuple[tuple[str, CanonicalObject], ...] = (
        ("sense_proposal.json", sense),
        ("reality_object.json", reality),
        ("evaluation_contract.json", evaluation_contract),
        ("bridge_contract.json", bridge),
        ("metric_proposal.json", metric),
        ("occurrence_report.json", occurrence),
        ("improvement_report.json", improvement),
        ("e2_report.json", report),
    )
    for filename, value in objects:
        _write(output / filename, value)
    (output / "operator_packet.json").write_bytes(canonical_bytes(packet))
    (output / "reproduction_operator_packet.json").write_bytes(canonical_bytes(reproduction_packet))
    for prefix, item in (
        ("discovery", discovery),
        ("recipient", exchange),
        ("reproduction_discovery", reproduction_discovery),
        ("reproduction", reproduction),
    ):
        (output / f"{prefix}_request.jsonl").write_bytes(item.request.to_jsonl())
        (output / f"{prefix}_response.jsonl").write_bytes(item.response.to_jsonl())
    for index, baseline in enumerate(baselines):
        (output / f"baseline_{index}_request.jsonl").write_bytes(
            baseline.exchange.request.to_jsonl()
        )
        (output / f"baseline_{index}_response.jsonl").write_bytes(
            baseline.exchange.response.to_jsonl()
        )
    for index, ablation_exchange in enumerate(ablation.exchanges):
        (output / f"ablation_{index}_request.jsonl").write_bytes(
            ablation_exchange.request.to_jsonl()
        )
        (output / f"ablation_{index}_response.jsonl").write_bytes(
            ablation_exchange.response.to_jsonl()
        )
    _write(output / "measurement_decision.json", measurement_decision)
    (output / "resource_observations.json").write_bytes(
        canonical_bytes([record.model_dump(mode="json") for record in resource_observations])
    )
    _write(
        output / "baseline_results.json",
        [b.model_dump(mode="json", exclude_computed_fields=True) for b in baselines],
    )
    _write(
        output / "ablation_evidence.json",
        ablation.model_dump(mode="json", exclude_computed_fields=True),
    )
    _write(output / "realization_receipts.json", [r.model_dump(mode="json") for r in receipts])
    registry = RegistryStore(output / "registry.jsonl", clock=lambda: created_at)
    payloads = tuple(
        json.loads(canonical_bytes(value.identity_payload())) for _, value in objects
    ) + (
        world.model_dump(mode="json"),
        reproduction_world.model_dump(mode="json"),
        operator.model_dump(mode="json"),
        constructor.model_dump(mode="json"),
        packet,
        discovery.request.model_dump(mode="json", exclude_computed_fields=True),
        discovery.response.model_dump(mode="json", exclude_computed_fields=True),
        exchange.request.model_dump(mode="json", exclude_computed_fields=True),
        exchange.response.model_dump(mode="json", exclude_computed_fields=True),
        reproduction_discovery.request.model_dump(mode="json", exclude_computed_fields=True),
        reproduction_discovery.response.model_dump(mode="json", exclude_computed_fields=True),
        reproduction.request.model_dump(mode="json", exclude_computed_fields=True),
        reproduction.response.model_dump(mode="json", exclude_computed_fields=True),
        reproduction_packet,
        json.loads(canonical_bytes(measurement_decision)),
        ablation.model_dump(mode="json", exclude_computed_fields=True),
        *(json.loads(canonical_bytes(control)) for control in controls),
        *(control_packet for _, control_packet in baseline_packets),
        *(ablation_packet for _, _, ablation_packet in ablation_packets),
        *(
            payload
            for baseline in baselines
            for payload in (
                baseline.exchange.request.model_dump(mode="json", exclude_computed_fields=True),
                baseline.exchange.response.model_dump(mode="json", exclude_computed_fields=True),
            )
        ),
        *(
            payload
            for ablation_exchange in ablation.exchanges
            for payload in (
                ablation_exchange.request.model_dump(mode="json", exclude_computed_fields=True),
                ablation_exchange.response.model_dump(mode="json", exclude_computed_fields=True),
            )
        ),
        *(b.model_dump(mode="json", exclude_computed_fields=True) for b in baselines),
        *(r.model_dump(mode="json") for r in receipts),
    )
    for payload in payloads:
        registry.append(
            actor_role="validator",
            actor_id="agent:e2-validator",
            object_payload=payload,
            event_type=LifecycleState.DRAFT,
            event_payload={"experiment": "E2", "seed": seed},
        )
    events = registry.verify()
    return E2RunResult(
        receiver_id="agent:e2-recipient-fresh",
        prediction_artifact_id=exchange.expected_artifact_id,
        agent_response=exchange.response,
        heldout_accuracy=heldout_accuracy,
        transformed_accuracy=transformed_accuracy,
        independent_reproduction_accuracy=reproduction_accuracy,
        transfer_packet_bytes=PACKET_BYTES,
        baselines=baselines,
        ablation=ablation,
        measurement_decision=measurement_decision,
        evaluation_contract=evaluation_contract,
        occurrence_report=occurrence,
        improvement_report=improvement,
        report=report,
        registry_head=events[-1].event_content_id,
        resource_observations=resource_observations,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic simulated AIRE E2")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(run_e2(seed=arguments.seed, output=arguments.output).report.content_id)


if __name__ == "__main__":
    main()
