import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aire_prime.agents import AgentRequest, AgentResponse, MessageKind
from aire_prime.core.canonical import content_id
from aire_prime.experiments.e2 import ablations, baselines
from aire_prime.experiments.e2.ablations import build_ablation_packets
from aire_prime.experiments.e2.baselines import build_baseline_packets
from aire_prime.experiments.e2.discoverer import discover_operator, operator_constructor
from aire_prime.experiments.e2.run import run_e2
from aire_prime.experiments.e2.world import generate_causal_world
from aire_prime.measurement.decision import DecisionStatus
from aire_prime.measurement.resources import MeasurementState
from aire_prime.objects.evidence import GroundingClass, OccurrenceMaturity
from aire_prime.registry.store import RegistryStore


def test_fresh_recipient_transfers_to_new_controller_and_permuted_actions(
    tmp_path: Path,
) -> None:
    result = run_e2(seed=202, output=tmp_path / "e2")

    assert result.receiver_id == "agent:e2-recipient-fresh"
    assert result.agent_response.content_ids == (result.prediction_artifact_id,)
    assert result.heldout_accuracy == 1.0
    assert result.transformed_accuracy == 1.0
    assert result.independent_reproduction_accuracy == 1.0
    assert result.measurement_decision.status is DecisionStatus.UNDETERMINED
    assert result.report.failed_gates == ("heldout-gain", "matched-controls")
    assert result.occurrence_report.evidence_state.occurrence is OccurrenceMaturity.CLAIMED
    assert result.occurrence_report.evidence_state.grounding is GroundingClass.SIMULATED
    controls = "\n".join(result.evaluation_contract.controls)
    for split in (*generate_causal_world(202).splits, *generate_causal_world(10_202).splits):
        assert split.content_id in controls


def test_matched_alternatives_and_targeted_ablation_fail_systematic_transfer(
    tmp_path: Path,
) -> None:
    result = run_e2(seed=202, output=tmp_path / "e2")

    assert {baseline.kind for baseline in result.baselines} == {
        "frozen-lookup-policy",
        "bandwidth-matched-opaque-tensor",
        "conventional-feature-schema",
    }
    assert all(
        baseline.packet_bytes == result.transfer_packet_bytes for baseline in result.baselines
    )
    assert all(
        baseline.transformed_accuracy < result.transformed_accuracy for baseline in result.baselines
    )
    assert result.ablation.targeted_drop > max(result.ablation.sham_drops)


def test_named_controls_and_shams_are_distinct_executable_packets() -> None:
    baseline_packets = build_baseline_packets(packet_bytes=4096)
    baseline_payloads = [packet for _, packet in baseline_packets]
    dependencies = {packet["constructor"]["dependencies"][0] for packet in baseline_payloads}
    physical_tables = {
        str(packet["constructor"]["operations"][0]["lookup_table"]) for packet in baseline_payloads
    }
    assert dependencies == {"probe_success", "raw_observation"}
    assert len(physical_tables) == 2
    assert len({packet["method_spec"]["algorithm"] for packet in baseline_payloads}) == 3

    world = generate_causal_world(202)
    constructor = operator_constructor(discover_operator(world.discovery_packet()))
    packets = build_ablation_packets(constructor=constructor, packet_bytes=4096)
    assert len({str(packet["constructor"]) for _, _, packet in packets}) == 4
    for kind, dimensions, packet in packets[1:]:
        assert dimensions == (1,), kind
        assert packet["constructor"]["operations"][0] == constructor.to_wire()["operations"][0]
        assert packet["constructor"]["operations"][1] != constructor.to_wire()["operations"][1]


@pytest.mark.parametrize("module_name", ("baseline", "ablation"))
@pytest.mark.parametrize("message_kind", (MessageKind.FAILURE, MessageKind.RESPONSE))
def test_failed_control_execution_cannot_be_scored(
    monkeypatch: pytest.MonkeyPatch, module_name: str, message_kind: MessageKind
) -> None:
    failed = SimpleNamespace(
        response=SimpleNamespace(
            message_kind=message_kind,
            content_ids=() if message_kind is MessageKind.FAILURE else ("sha256:" + "9" * 64,),
        ),
        expected_artifact_id="sha256:" + "0" * 64,
    )
    world = generate_causal_world(202)
    if module_name == "baseline":
        monkeypatch.setattr(baselines, "run_recipient", lambda **_: failed)
        with pytest.raises(RuntimeError, match="contained baseline failed"):
            baselines.evaluate_baselines(
                packets=build_baseline_packets(packet_bytes=4096),
                hidden=world.hidden_test,
                transformed=world.transformed_test,
                task_payload={},
                claim_id="sha256:" + "1" * 64,
                object_id="sha256:" + "2" * 64,
            )
    else:
        constructor = operator_constructor(discover_operator(world.discovery_packet()))
        monkeypatch.setattr(ablations, "run_recipient", lambda **_: failed)
        with pytest.raises(RuntimeError, match="contained ablation failed"):
            ablations.evaluate_e2_ablations(
                packets=build_ablation_packets(constructor=constructor, packet_bytes=4096),
                operator_packet_id="sha256:" + "3" * 64,
                seed=202,
                hidden=world.hidden_test,
                transformed=world.transformed_test,
                task_payload={},
                claim_id="sha256:" + "1" * 64,
                object_id="sha256:" + "2" * 64,
                candidate_accuracy=1.0,
            )


def test_e2_is_canonically_deterministic(tmp_path: Path) -> None:
    first = run_e2(seed=202, output=tmp_path / "a")
    second = run_e2(seed=202, output=tmp_path / "b")

    assert first.report.content_id == second.report.content_id
    assert first.evaluation_contract.content_id == second.evaluation_contract.content_id
    assert first.registry_head == second.registry_head
    assert first.report.classification == "simulated-alien-sense-transfer-not-established"
    assert first.report.evidence_state == "O0/G-S"
    first_files = {
        path.name: path.read_bytes()
        for path in sorted((tmp_path / "a").iterdir())
        if path.name != "resource_observations.json"
    }
    second_files = {
        path.name: path.read_bytes()
        for path in sorted((tmp_path / "b").iterdir())
        if path.name != "resource_observations.json"
    }
    assert first_files == second_files


def test_resource_observations_are_saved_as_noncanonical_host_metadata(tmp_path: Path) -> None:
    result = run_e2(seed=202, output=tmp_path / "e2")
    observations = json.loads((tmp_path / "e2" / "resource_observations.json").read_bytes())

    assert [item["arm"] for item in observations] == [
        "candidate",
        "baseline:frozen-lookup-policy",
        "baseline:bandwidth-matched-opaque-tensor",
        "baseline:conventional-feature-schema",
        "reproduction",
    ]
    assert len(result.resource_observations) == len(observations)


def test_transfer_packet_contains_only_constructor_not_discovered_mapping(
    tmp_path: Path,
) -> None:
    run_e2(seed=202, output=tmp_path / "e2")
    packet = json.loads((tmp_path / "e2" / "operator_packet.json").read_text())

    assert len((tmp_path / "e2" / "operator_packet.json").read_bytes()) == 4096
    assert "probe_success_to_physical_action" not in packet
    assert packet["constructor"]["operations"][0]["primitive"] == "lookup"


def test_unobserved_host_resources_remain_undetermined(tmp_path: Path) -> None:
    result = run_e2(seed=202, output=tmp_path / "e2")

    for baseline in result.baselines:
        assert baseline.resources.peak_resident_bytes.state is MeasurementState.UNDETERMINED
        assert baseline.resources.elapsed_time.state is MeasurementState.UNDETERMINED


def test_reproduction_chain_resolves_through_registry(tmp_path: Path) -> None:
    output = tmp_path / "e2"
    result = run_e2(seed=202, output=output)
    registered = {event.object_id for event in RegistryStore(output / "registry.jsonl").verify()}
    request = AgentRequest.from_jsonl((output / "reproduction_request.jsonl").read_bytes())
    response = AgentResponse.from_jsonl((output / "reproduction_response.jsonl").read_bytes())
    discovery_request = AgentRequest.from_jsonl(
        (output / "reproduction_discovery_request.jsonl").read_bytes()
    )
    discovery_response = AgentResponse.from_jsonl(
        (output / "reproduction_discovery_response.jsonl").read_bytes()
    )
    packet = json.loads((output / "reproduction_operator_packet.json").read_text())

    assert {
        request.content_id,
        response.content_id,
        discovery_request.content_id,
        discovery_response.content_id,
        content_id(packet),
        *(baseline.exchange.request.content_id for baseline in result.baselines),
        *(baseline.exchange.response.content_id for baseline in result.baselines),
        *(exchange.request.content_id for exchange in result.ablation.exchanges),
        *(exchange.response.content_id for exchange in result.ablation.exchanges),
        *result.measurement_decision.control_samples_ids,
    } <= registered


def test_forced_gate_failure_downgrades_and_suppresses_positive_evidence(
    tmp_path: Path,
) -> None:
    result = run_e2(
        seed=202,
        output=tmp_path / "e2",
        forced_failures=("independent-reproduction",),
    )

    assert result.report.classification.endswith("not-established")
    assert result.report.failed_gates == (
        "heldout-gain",
        "independent-reproduction",
        "matched-controls",
    )
    assert result.occurrence_report.evidence_state.occurrence is not OccurrenceMaturity.TRANSFERRED
    assert result.occurrence_report.replication_evidence == ()
