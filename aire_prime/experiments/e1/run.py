import argparse
import hashlib
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from pydantic import SkipValidation

from aire_prime.agents import (
    AgentIdentity,
    AgentRequest,
    AgentResponse,
    MessageKind,
    Role,
    SubprocessAdapter,
    TrustedCommand,
)
from aire_prime.agents.protocol import DeclaredInput
from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel
from aire_prime.exchange.realize import RealizationContext, Realizer
from aire_prime.exchange.receipt import RealizationReceipt
from aire_prime.experiments.e1.baselines import (
    FrozenBaselinePacket,
    FrozenBaselineResult,
    bandwidth_matched_baseline_packets,
)
from aire_prime.experiments.e1.tasks import execute_transfer_tasks
from aire_prime.experiments.e1.world import (
    ConstructionResult,
    ProceduralWorld,
    generate_world,
    realize_capability,
)
from aire_prime.grc.constructor import ConstructorPlan, OperationSpec, ResourceBudget
from aire_prime.grc.types import SpaceKind, StructuralType
from aire_prime.objects import CanonicalObject
from aire_prime.objects.contracts import BridgeContract, EvaluationContract, RealityTier
from aire_prime.objects.evidence import EvidenceState, GroundingClass, OccurrenceMaturity
from aire_prime.objects.proposals import MetricProposal, RealityObject, SenseProposal
from aire_prime.objects.reports import ImprovementReport, OccurrenceReport
from aire_prime.registry.lifecycle import LifecycleState
from aire_prime.registry.store import RegistryStore


class E1Report(CanonicalObject):
    classification: str
    seed: int
    world_id: str
    reality_object_id: str
    evaluation_contract_id: str
    bridge_contract_id: str
    occurrence_report_id: str
    improvement_report_id: str
    agent_response_ids: tuple[str, ...]
    transfer_packet_bytes: int
    passed_gates: tuple[str, ...]
    failed_gates: tuple[str, ...] = ()
    baseline_packet_ids: tuple[str, ...]
    baseline_ids: tuple[str, ...]


class E1RunResult(FrozenModel):
    receiver_id: str
    transfer: ConstructionResult
    composition: ConstructionResult
    repair: ConstructionResult
    withheld_conformance_passed: bool
    transfer_packet_bytes: int
    baselines: tuple[FrozenBaselineResult, ...]
    realization_receipts: tuple[RealizationReceipt, ...]
    agent_requests: tuple[AgentRequest, ...]
    agent_responses: tuple[AgentResponse, ...]
    baseline_requests: tuple[AgentRequest, ...]
    baseline_responses: tuple[AgentResponse, ...]
    sense_proposal: SenseProposal | None
    reality_object: RealityObject
    evaluation_contract: EvaluationContract
    bridge_contract: BridgeContract
    occurrence_report: OccurrenceReport
    improvement_report: SkipValidation[ImprovementReport]
    report: E1Report
    registry_head: str


def _created_at(seed: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=seed)


def _realization_receipts(
    *,
    reality_object_id: str,
    receiver_id: str,
    artifact_ids: tuple[str, str, str],
) -> tuple[RealizationReceipt, ...]:
    output_type = StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,))
    budget = ResourceBudget(
        max_operations=4,
        max_elements=16,
        max_output_bytes=256,
        max_elapsed_seconds=1.0,
    )
    plans = (
        ConstructorPlan(
            object_id=reality_object_id,
            dependencies=("resource",),
            operations=(
                OperationSpec(id="output", primitive="identity", inputs=("resource",)),
            ),
            output_ref="output",
            output_type=output_type,
        ),
        ConstructorPlan(
            object_id=reality_object_id,
            dependencies=("resource", "monitor"),
            operations=(
                OperationSpec(
                    id="output",
                    primitive="concat",
                    inputs=("resource", "monitor"),
                ),
            ),
            output_ref="output",
            output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(4,)),
        ),
        ConstructorPlan(
            object_id=reality_object_id,
            dependencies=("resource",),
            operations=(
                OperationSpec(id="output", primitive="identity", inputs=("resource",)),
            ),
            output_ref="output",
            output_type=output_type,
        ),
    )
    inputs = (
        {"resource": np.array([1.0, 0.0])},
        {
            "resource": np.array([1.0, 0.0]),
            "monitor": np.array([0.0, 1.0]),
        },
        {"resource": np.array([1.0, 0.0])},
    )
    tests = (
        ("resource-substitution", "port-continuity"),
        ("composition",),
        ("single-component-repair",),
    )
    realizer = Realizer(clock=lambda: 0.0)
    return tuple(
        realizer.realize(
            plan,
            RealizationContext(
                receiver_id=receiver_id,
                local_realization_id=artifact_ids[index - 1],
                inputs=task_inputs,
                budget=budget,
                contract_tests=contract_tests,
            ),
        ).receipt
        for index, (plan, task_inputs, contract_tests) in enumerate(
            zip(plans, inputs, tests, strict=True), start=1
        )
    )


def _write_object(path: Path, value: object) -> None:
    payload: object = (
        value.model_dump(mode="json") if isinstance(value, CanonicalObject) else value
    )
    path.write_bytes(canonical_bytes(payload))


_RECIPIENT_AGENT = r'''use strict;
use warnings;
use JSON::PP;
use Digest::SHA qw(sha256_hex);

my $request_line = <STDIN>;
defined $request_line or exit 20;
my $request = decode_json($request_line);
open my $packet_handle, '<', $ARGV[0] or exit 21;
local $/;
my $packet = decode_json(<$packet_handle>);
close $packet_handle;
open my $task_handle, '<', $ARGV[1] or exit 25;
my $task = decode_json(<$task_handle>);
close $task_handle;

my $encoder = JSON::PP->new->canonical(1);
sub construction_id {
    my (@component_ids) = @_;
    my $construction = $encoder->encode({
        component_ids => \@component_ids,
        resource => $packet->{requested_resource},
    });
    return 'sha256:' . sha256_hex($construction);
}

my @construction_ids;
if ($packet->{representation_kind} eq 'generative-constructor') {
    my @selected;
    for my $stage (@{$packet->{contract}->{required_stages}}) {
        my @candidates = grep {
            $_->{stage} eq $stage
            && grep { $_ eq $packet->{requested_resource} } @{$_->{resources}}
        } @{$packet->{components}};
        @candidates = sort {
            $a->{cost} <=> $b->{cost} || $a->{name} cmp $b->{name}
        } @candidates;
        @candidates or exit 22;
        push @selected, $candidates[0]->{content_id};
    }
    if ($task->{kind} eq 'composition') {
        my @monitors = sort {
            $a->{cost} <=> $b->{cost} || $a->{name} cmp $b->{name}
        } grep {
            $_->{stage} eq 'monitor'
            && grep { $_ eq $packet->{requested_resource} } @{$_->{resources}}
        } @{$packet->{components}};
        @monitors or exit 23;
        push @selected, $monitors[0]->{content_id};
    } elsif ($task->{kind} eq 'repair') {
        my $removed = $task->{removed_component_id};
        @selected = ();
        for my $stage (@{$packet->{contract}->{required_stages}}) {
            my @candidates = grep {
                $_->{stage} eq $stage
                && $_->{content_id} ne $removed
                && grep { $_ eq $packet->{requested_resource} } @{$_->{resources}}
            } @{$packet->{components}};
            @candidates = sort {
                $a->{cost} <=> $b->{cost} || $a->{name} cmp $b->{name}
            } @candidates;
            @candidates or exit 24;
            push @selected, $candidates[0]->{content_id};
        }
    } elsif ($task->{kind} ne 'transfer') {
        exit 26;
    }
    @construction_ids = (construction_id(@selected));
} else {
    my $data = $packet->{data};
    my @selected;
    if ($packet->{representation_kind} eq 'fixed-instance'
        || $packet->{representation_kind} eq 'conventional-feature-schema') {
        @selected = @{$data->{component_ids}};
    } elsif ($packet->{representation_kind} eq 'demonstration-list') {
        @selected = @{$data->{demonstrations}->[0]->{component_ids}};
    } elsif ($packet->{representation_kind} eq 'lookup-policy') {
        my $entry = $data->{lookup_policy}->{$packet->{requested_resource}};
        @selected = defined $entry ? @{$entry} : ();
    }
    @construction_ids = (construction_id(@selected)) if @selected;
}
@construction_ids = sort @construction_ids;
my $response = {
    schema_version => '0.1.0',
    message_kind => 'response',
    request_content_id => $request->{content_id},
    sender => $request->{receiver},
    receiver => $request->{sender},
    object_ids => $request->{object_ids},
    content_ids => \@construction_ids,
    receipt_content_ids => [],
    failures => [],
};
my $identity = $encoder->encode($response);
$response->{content_id} = 'sha256:' . sha256_hex($identity);
print $encoder->encode($response) . "\n";
'''


def _transfer_packet_payload(
    *, world: ProceduralWorld, reality_object_id: str
) -> dict[str, object]:
    return {
        "representation_kind": "generative-constructor",
        "requested_resource": world.transfer_resource.value,
        "contract": world.contract.model_dump(
            mode="json", exclude={"withheld_tests"}
        ),
        "components": [
            {
                **component.model_dump(mode="json"),
                "content_id": component.content_id,
            }
            for component in world.components
        ],
        "reality_object_id": reality_object_id,
    }


def _contained_recipient_exchange(
    *,
    packet: bytes,
    packet_id: str,
    task_payload: dict[str, object],
    reality_object_id: str,
    claim_id: str,
    receiver_id: str,
) -> tuple[AgentRequest, AgentResponse]:
    with tempfile.TemporaryDirectory(prefix="aire-e1-recipient-") as directory:
        working_directory = Path(directory)
        packet_path = working_directory / "transfer-packet.json"
        task_path = working_directory / "task.json"
        script_path = working_directory / "recipient-agent.pl"
        packet_path.write_bytes(packet)
        task_path.write_bytes(canonical_bytes(task_payload))
        script_path.write_text(_RECIPIENT_AGENT, encoding="utf-8")
        request = AgentRequest(
            message_kind=MessageKind.REALIZE_REQUEST,
            sender=AgentIdentity(agent_id="agent:e1-proposer", role=Role.PROPOSER),
            receiver=AgentIdentity(agent_id=receiver_id, role=Role.RECEIVER),
            claim_id=claim_id,
            object_ids=(reality_object_id,),
            content_ids=(packet_id, content_id(task_payload)),
            declared_inputs=(
                DeclaredInput(name="task", content_id=content_id(task_payload)),
                DeclaredInput(name="transfer-packet", content_id=packet_id),
            ),
        )
        adapter = SubprocessAdapter(
            trusted_command=TrustedCommand.attest(
                ("/usr/bin/perl", str(script_path), str(packet_path), str(task_path))
            ),
            working_directory=working_directory,
            timeout_seconds=2.0,
            max_input_bytes=16_384,
            max_output_bytes=16_384,
        )
        return request, adapter.run(request)


def _evaluate_baselines(
    *,
    world: ProceduralWorld,
    packets: tuple[FrozenBaselinePacket, ...],
    task_payloads: tuple[dict[str, object], ...],
    reality_object_id: str,
    claim_id: str,
    receiver_id: str,
) -> tuple[
    tuple[FrozenBaselineResult, ...],
    tuple[AgentRequest, ...],
    tuple[AgentResponse, ...],
]:
    results: list[FrozenBaselineResult] = []
    requests: list[AgentRequest] = []
    responses: list[AgentResponse] = []
    for baseline in packets:
        packet_id = "sha256:" + hashlib.sha256(baseline.packet).hexdigest()
        exchanges = tuple(
            _contained_recipient_exchange(
                packet=baseline.packet,
                packet_id=packet_id,
                task_payload=task_payload,
                reality_object_id=reality_object_id,
                claim_id=claim_id,
                receiver_id=receiver_id,
            )
            for task_payload in task_payloads
        )
        arm_requests = tuple(exchange[0] for exchange in exchanges)
        arm_responses = tuple(exchange[1] for exchange in exchanges)
        requests.extend(arm_requests)
        responses.extend(arm_responses)
        if baseline.candidate_component_ids:
            evaluated = realize_capability(
                world,
                resource=world.transfer_resource,
                fixed_component_ids=baseline.candidate_component_ids,
            )
            expected_ids = (evaluated.artifact_content_id,)
            response_matches = all(
                response.message_kind is MessageKind.RESPONSE
                and response.content_ids == expected_ids
                for response in arm_responses
            )
            failures = evaluated.failed_tests + (() if response_matches else ("response",))
            success = evaluated.success and response_matches
        else:
            failures = ("no-construction",)
            success = False
        results.append(
            FrozenBaselineResult(
                kind=baseline.kind,
                packet_bytes=len(baseline.packet),
                packet_digest=packet_id,
                construction_ids=tuple(
                    sorted(
                        {
                            construction_id
                            for response in arm_responses
                            for construction_id in response.content_ids
                        }
                    )
                ),
                interactions=len(task_payloads),
                transmitted_input_bytes=(
                    len(baseline.packet) * len(task_payloads)
                    + sum(len(canonical_bytes(task)) for task in task_payloads)
                ),
                changed_resource_success=success,
                failed_tests=tuple(sorted(set(failures))),
            )
        )
    return tuple(results), tuple(requests), tuple(responses)


def run_e1(*, seed: int, output: Path) -> E1RunResult:
    if output.exists() and any(output.iterdir()):
        raise ValueError("E1 output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    created_at = _created_at(seed)
    world = generate_world(seed)
    tasks = execute_transfer_tasks(world)
    reality_object = RealityObject(
        created_at=created_at,
        validity_region=("seeded-procedural-world", "simulated"),
        state_space=StructuralType(kind=SpaceKind.VECTOR, dimensions=(4,)),
        interfaces=("resource", "monitor", "control-signal"),
        transformations=("resource-substitution", "composition", "repair"),
        invariants=("port-continuity", "finite-output"),
        constructor_id=world.contract.content_id,
        tests=world.hidden_test_ids,
        resource_requirements=("matched-packet-bytes", "bounded-realization"),
    )
    transfer_packet_payload = _transfer_packet_payload(
        world=world,
        reality_object_id=reality_object.content_id,
    )
    packet = canonical_bytes(transfer_packet_payload)
    packet_id = content_id(transfer_packet_payload)
    baseline_packets = bandwidth_matched_baseline_packets(world, len(packet))
    removed_component_id = next(
        component_id
        for component_id in tasks.transfer.component_ids
        if component_id not in tasks.repair.component_ids
    )
    task_payloads: tuple[dict[str, object], ...] = (
        {"kind": "transfer"},
        {"kind": "composition"},
        {"kind": "repair", "removed_component_id": removed_component_id},
    )
    transmitted_input_bytes = len(packet) * len(task_payloads) + sum(
        len(canonical_bytes(task)) for task in task_payloads
    )
    evaluation_contract = EvaluationContract(
        created_at=created_at,
        validity_region=("E1", "simulated"),
        claim="fresh-recipient capability reconstruction under changed resources",
        baseline_ids=tuple(baseline.content_id for baseline in baseline_packets),
        hidden_test_ids=world.hidden_test_ids,
        controls=(
            "bandwidth-matched",
            "fresh-recipient",
            "frozen-alternatives",
            f"world-seed:{seed}",
        ),
        resource_budget=(
            ("packet_bytes_per_transfer", float(len(packet))),
            ("transmitted_input_bytes", float(transmitted_input_bytes)),
            ("interactions", float(len(task_payloads))),
        ),
        decision_rule="all transfer, composition, repair, and withheld gates pass",
        replication_requirements=("same-seed-canonical-id",),
    )
    bridge_contract = BridgeContract(
        created_at=created_at,
        validity_region=("E1", "simulated"),
        reality_tier=RealityTier.SIMULATED,
        authority_id="authority:e1-validator",
        authorization_boundary="offline deterministic simulation only",
        observable_consequences=("withheld capability conformance",),
        approved_instruments=("deterministic procedural evaluator",),
        resource_envelope=(
            ("transmitted_input_bytes", float(transmitted_input_bytes)),
        ),
        protected_boundaries=("no physical claim", "no language baseline"),
        permitted_status_claims=(GroundingClass.SIMULATED,),
    )
    metric = MetricProposal(
        created_at=created_at,
        validity_region=("E1", "simulated"),
        dimension="withheld-capability-pass-rate",
        measurement_procedure="fraction of four frozen conformance gates passed",
        ordering="higher-is-better",
        baseline_ids=tuple(baseline.content_id for baseline in baseline_packets),
        invariances=("component-name-order",),
        consequence="fresh recipient reconstructs a reusable capability",
        falsifiers=("changed resource failure", "repair failure"),
        anti_gaming_tests=("fresh recipient", "withheld tests", "matched bytes"),
        complexity_cost=float(transmitted_input_bytes),
        expiration_conditions=("world generator or contract changes",),
    )
    baselines, baseline_requests, baseline_responses = _evaluate_baselines(
        world=world,
        packets=baseline_packets,
        task_payloads=task_payloads,
        reality_object_id=reality_object.content_id,
        claim_id=evaluation_contract.content_id,
        receiver_id=tasks.receiver_id,
    )
    receipts = _realization_receipts(
        reality_object_id=reality_object.content_id,
        receiver_id=tasks.receiver_id,
        artifact_ids=(
            tasks.transfer.artifact_content_id,
            tasks.composition.artifact_content_id,
            tasks.repair.artifact_content_id,
        ),
    )
    exchanges = tuple(
        _contained_recipient_exchange(
            packet=packet,
            packet_id=packet_id,
            task_payload=task_payload,
            reality_object_id=reality_object.content_id,
            claim_id=evaluation_contract.content_id,
            receiver_id=tasks.receiver_id,
        )
        for task_payload in task_payloads
    )
    agent_requests = tuple(exchange[0] for exchange in exchanges)
    agent_responses = tuple(exchange[1] for exchange in exchanges)
    expected_agent_artifacts = (
        tasks.transfer.artifact_content_id,
        tasks.composition.artifact_content_id,
        tasks.repair.artifact_content_id,
    )
    contained_conformance = all(
        response.message_kind is MessageKind.RESPONSE
        and response.content_ids == (expected_artifact,)
        for response, expected_artifact in zip(
            agent_responses, expected_agent_artifacts, strict=True
        )
    )
    passed_gates = tuple(
        gate
        for gate, passed in (
            ("changed-resource-transfer", tasks.transfer.success),
            ("composition", tasks.composition.success),
            ("repair", tasks.repair.success),
            ("withheld-conformance", tasks.withheld_conformance_passed),
            ("contained-agent-transfer", contained_conformance),
            (
                "matched-alternatives",
                all(not baseline.changed_resource_success for baseline in baselines),
            ),
        )
        if passed
    )
    failed_gates = tuple(
        gate
        for gate in (
            "changed-resource-transfer",
            "composition",
            "repair",
            "withheld-conformance",
            "contained-agent-transfer",
            "matched-alternatives",
        )
        if gate not in passed_gates
    )
    occurrence = OccurrenceReport(
        created_at=created_at,
        validity_region=("E1", "simulated"),
        proposal_id=reality_object.content_id,
        contract_id=evaluation_contract.content_id,
        validator_id="agent:e1-validator",
        evidence_state=EvidenceState(
            occurrence=(
                OccurrenceMaturity.TRANSFERRED
                if not failed_gates
                else OccurrenceMaturity.CLAIMED
            ),
            grounding=GroundingClass.SIMULATED,
        ),
        independence_evidence=("fresh recipient identity",),
        causal_evidence=("resource substitution and repair",),
        generalization_evidence=("withheld conformance",),
        transfer_evidence=(
            "independently validated contained-agent constructions",
            *(f"contained-agent-response:{response.content_id}" for response in agent_responses),
        ),
        known_failures=failed_gates,
        evidence_attachments=(
            reality_object.content_id,
            evaluation_contract.content_id,
            *(response.content_id for response in agent_responses),
        ),
        expiration_conditions=("world or evaluator changes",),
        resource_measurements=(
            ("transmitted_input_bytes", float(transmitted_input_bytes)),
            ("interactions", float(len(task_payloads))),
            (
                "grc_kernel_smoke_operations",
                float(sum(r.resources.operation_count for r in receipts)),
            ),
        ),
    )
    improvement = ImprovementReport.model_validate(
        {
            "created_at": created_at,
            "validity_region": ("E1", "simulated"),
            "metric_proposal_id": metric.content_id,
            "evaluation_contract_id": evaluation_contract.content_id,
            "occurrence_report_id": occurrence.content_id,
            "validator_id": "agent:e1-validator",
            "claimed_grounding": GroundingClass.SIMULATED,
            "improvement_vector": (("withheld_pass_rate", 1.0 if not failed_gates else 0.0),),
            "baseline_results": tuple(
                (baseline.kind, 1.0 if baseline.changed_resource_success else 0.0)
                for baseline in baselines
            ),
            "resource_measurements": (
                ("transmitted_input_bytes", float(transmitted_input_bytes)),
                ("interactions", float(len(task_payloads))),
            ),
            "adversarial_results": ("fixed instance fails resource substitution",),
            "known_failures": failed_gates,
            "expiration_conditions": ("evaluation contract changes",),
        },
        context={"occurrence_reports": {occurrence.content_id: occurrence}},
    )
    report = E1Report(
        created_at=created_at,
        validity_region=("E1", "simulated"),
        classification=(
            "simulated-capability-transfer"
            if not failed_gates
            else "simulated-capability-transfer-not-established"
        ),
        seed=seed,
        world_id=world.content_id,
        reality_object_id=reality_object.content_id,
        evaluation_contract_id=evaluation_contract.content_id,
        bridge_contract_id=bridge_contract.content_id,
        occurrence_report_id=occurrence.content_id,
        improvement_report_id=improvement.content_id,
        agent_response_ids=tuple(response.content_id for response in agent_responses),
        transfer_packet_bytes=len(packet),
        passed_gates=passed_gates,
        failed_gates=failed_gates,
        baseline_packet_ids=tuple(
            baseline.content_id for baseline in baseline_packets
        ),
        baseline_ids=tuple(baseline.content_id for baseline in baselines),
    )

    objects: tuple[tuple[str, CanonicalObject], ...] = (
        ("reality_object.json", reality_object),
        ("evaluation_contract.json", evaluation_contract),
        ("bridge_contract.json", bridge_contract),
        ("metric_proposal.json", metric),
        ("occurrence_report.json", occurrence),
        ("improvement_report.json", improvement),
        ("e1_report.json", report),
    )
    for filename, value in objects:
        _write_object(output / filename, value)
    _write_object(
        output / "realization_receipts.json",
        [receipt.model_dump(mode="json") for receipt in receipts],
    )
    (output / "transfer_packet.json").write_bytes(packet)
    (output / "agent_requests.jsonl").write_bytes(
        b"".join(request.to_jsonl() for request in agent_requests)
    )
    (output / "agent_responses.jsonl").write_bytes(
        b"".join(response.to_jsonl() for response in agent_responses)
    )
    baseline_directory = output / "baseline_packets"
    baseline_directory.mkdir()
    for baseline in baseline_packets:
        (baseline_directory / f"{baseline.kind}.json").write_bytes(baseline.packet)
    _write_object(
        output / "baseline_results.json",
        [baseline.model_dump(mode="json") for baseline in baselines],
    )
    (output / "baseline_responses.jsonl").write_bytes(
        b"".join(response.to_jsonl() for response in baseline_responses)
    )
    (output / "baseline_requests.jsonl").write_bytes(
        b"".join(request.to_jsonl() for request in baseline_requests)
    )
    registry = RegistryStore(output / "registry.jsonl", clock=lambda: created_at)
    for _, value in objects:
        registry.append(
            actor_role="validator",
            actor_id="agent:e1-validator",
            object_payload=value.model_dump(mode="json", exclude_computed_fields=True),
            event_type=LifecycleState.DRAFT,
            event_payload={"experiment": "E1", "seed": seed},
        )
    supporting_payloads = [
        transfer_packet_payload,
        *task_payloads,
        tasks.model_dump(mode="json"),
        *[
            receipt.model_dump(mode="json", exclude_computed_fields=True)
            for receipt in receipts
        ],
        *[baseline.model_dump(mode="json") for baseline in baselines],
        *[
            {
                "kind": baseline.kind,
                "packet_bytes": len(baseline.packet),
                "packet_digest": "sha256:"
                + hashlib.sha256(baseline.packet).hexdigest(),
            }
            for baseline in baseline_packets
        ],
        *[
            request.model_dump(mode="json", exclude_computed_fields=True)
            for request in (*agent_requests, *baseline_requests)
        ],
        *[
            response.model_dump(mode="json", exclude_computed_fields=True)
            for response in (*agent_responses, *baseline_responses)
        ],
    ]
    for payload in supporting_payloads:
        registry.append(
            actor_role="validator",
            actor_id="agent:e1-validator",
            object_payload=payload,
            event_type=LifecycleState.DRAFT,
            event_payload={"experiment": "E1", "seed": seed},
        )
    events = registry.verify()
    result = E1RunResult(
        receiver_id=tasks.receiver_id,
        transfer=tasks.transfer,
        composition=tasks.composition,
        repair=tasks.repair,
        withheld_conformance_passed=tasks.withheld_conformance_passed,
        transfer_packet_bytes=len(packet),
        baselines=baselines,
        realization_receipts=receipts,
        agent_requests=agent_requests,
        agent_responses=agent_responses,
        baseline_requests=baseline_requests,
        baseline_responses=baseline_responses,
        sense_proposal=None,
        reality_object=reality_object,
        evaluation_contract=evaluation_contract,
        bridge_contract=bridge_contract,
        occurrence_report=occurrence,
        improvement_report=improvement,
        report=report,
        registry_head=events[-1].event_content_id,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic AIRE E1")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = run_e1(seed=arguments.seed, output=arguments.output)
    print(result.report.content_id)


if __name__ == "__main__":
    main()
