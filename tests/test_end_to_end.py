import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from aire_prime.agents import AgentRequest, AgentResponse
from aire_prime.cli import run_cli
from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.experiments.e1.run import E1Report
from aire_prime.experiments.e2.run import E2Report
from aire_prime.objects.contracts import BridgeContract, EvaluationContract
from aire_prime.objects.evidence import GroundingClass
from aire_prime.objects.proposals import RealityObject, SenseProposal
from aire_prime.objects.reports import OccurrenceReport
from aire_prime.registry.lifecycle import LifecycleState
from aire_prime.registry.store import RegistryStore


def _wire(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text())
    assert isinstance(value, dict)
    return value


def test_cli_reproduces_and_inspects_e1_e2_evidence(tmp_path: Path) -> None:
    e1 = tmp_path / "e1"
    e2 = tmp_path / "e2"
    assert run_cli(["e1", "run", "--seed", "101", "--output", str(e1)]) == 0
    assert run_cli(["e2", "run", "--seed", "202", "--output", str(e2)]) == 0
    for directory, report_type, report_name in (
        (e1, E1Report, "e1_report.json"),
        (e2, E2Report, "e2_report.json"),
    ):
        assert run_cli(["registry", "verify", str(directory / "registry.jsonl")]) == 0
        assert run_cli(["report", "show", str(directory)]) == 0
        report = report_type.from_wire(_wire(directory / report_name))
        contract = EvaluationContract.from_wire(_wire(directory / "evaluation_contract.json"))
        bridge = BridgeContract.from_wire(_wire(directory / "bridge_contract.json"))
        occurrence = OccurrenceReport.from_wire(_wire(directory / "occurrence_report.json"))
        request_path = (
            directory / "agent_requests.jsonl"
            if report_name == "e1_report.json"
            else directory / "discovery_request.jsonl"
        )
        first_request = AgentRequest.from_jsonl(request_path.read_bytes().splitlines()[0] + b"\n")
        events = RegistryStore(directory / "registry.jsonl").verify()
        before_verify = (directory / "registry.jsonl").read_bytes()
        RegistryStore(directory / "registry.jsonl").verify()
        assert (directory / "registry.jsonl").read_bytes() == before_verify
        sequence = {event.object_id: event.sequence for event in events}
        assert sequence[contract.content_id] < sequence[report.content_id]
        assert report.evaluation_contract_id == contract.content_id
        assert report.bridge_contract_id == bridge.content_id
        assert report.content_id == content_id(report.identity_payload())
        assert (
            len({first_request.sender.agent_id, occurrence.validator_id, bridge.authority_id}) == 3
        )
        receipts = json.loads((directory / "realization_receipts.json").read_text())
        assert all("resources" in receipt and "failures" in receipt for receipt in receipts)
    e2_report = E2Report.from_wire(_wire(e2 / "e2_report.json"))
    assert e2_report.evidence_state.endswith("/G-S")
    assert e2_report.evidence_state.split("/", 1)[0] in {"O0", "O1", "O2", "O3", "O4"}
    assert e2_report.failed_gates == ("heldout-gain", "matched-controls")


def test_report_inspection_rejects_contract_and_resource_tampering(tmp_path: Path) -> None:
    source = tmp_path / "e1-source"
    assert run_cli(["e1", "run", "--seed", "101", "--output", str(source)]) == 0
    output = tmp_path / "e1-contract"
    shutil.copytree(source, output)
    contract_path = output / "evaluation_contract.json"
    contract = _wire(contract_path)
    contract["claim"] = "tampered"
    contract_path.write_text(json.dumps(contract))
    assert run_cli(["report", "show", str(output)]) != 0

    output2 = tmp_path / "e1-budget"
    shutil.copytree(source, output2)
    receipts = json.loads((output2 / "realization_receipts.json").read_text())
    receipts[0]["failures"] = [
        {"code": "ResourceInfeasible", "message": "forced budget violation", "counterexample": None}
    ]
    (output2 / "realization_receipts.json").write_text(json.dumps(receipts))
    assert run_cli(["report", "show", str(output2)]) != 0

    missing = tmp_path / "e1-missing"
    shutil.copytree(source, missing)
    (missing / "realization_receipts.json").unlink()
    assert run_cli(["report", "show", str(missing)]) != 0


def test_report_inspection_rejects_e2_substitution_and_unregistered_exchange(
    tmp_path: Path,
) -> None:
    from aire_prime.measurement.decision import ImprovementDecision

    source = tmp_path / "e2-source"
    assert run_cli(["e2", "run", "--seed", "202", "--output", str(source)]) == 0

    missing = tmp_path / "e2-missing-response"
    shutil.copytree(source, missing)
    (missing / "baseline_0_response.jsonl").unlink()
    assert run_cli(["report", "show", str(missing)]) != 0

    substituted = tmp_path / "e2-substituted-decision"
    shutil.copytree(source, substituted)
    decision_path = substituted / "measurement_decision.json"
    decision = ImprovementDecision.model_validate(json.loads(decision_path.read_bytes()))
    changed = decision.model_copy(update={"seed": decision.seed + 1})
    decision_path.write_bytes(canonical_bytes(changed))
    assert run_cli(["report", "show", str(substituted)]) != 0

    unregistered = tmp_path / "e2-unregistered-response"
    shutil.copytree(source, unregistered)
    response_path = unregistered / "baseline_0_response.jsonl"
    response = AgentResponse.from_jsonl(response_path.read_bytes())
    changed_response = response.model_copy(update={"content_ids": ("sha256:" + "8" * 64,)})
    response_path.write_bytes(changed_response.to_jsonl())
    assert run_cli(["report", "show", str(unregistered)]) != 0

    wrong_link = tmp_path / "e2-wrong-request-link"
    shutil.copytree(source, wrong_link)
    response_path = wrong_link / "baseline_0_response.jsonl"
    response = AgentResponse.from_jsonl(response_path.read_bytes())
    changed_response = response.model_copy(update={"request_content_id": "sha256:" + "7" * 64})
    response_path.write_bytes(changed_response.to_jsonl())
    assert run_cli(["report", "show", str(wrong_link)]) != 0

    physical_sense = tmp_path / "e2-physical-sense"
    shutil.copytree(source, physical_sense)
    sense_path = physical_sense / "sense_proposal.json"
    sense = SenseProposal.from_wire(_wire(sense_path))
    sense_path.write_text(
        sense.model_copy(update={"grounding_claim": GroundingClass.PHYSICAL}).model_dump_json()
    )
    assert run_cli(["report", "show", str(physical_sense)]) != 0

    substituted_reality = tmp_path / "e2-substituted-reality"
    shutil.copytree(source, substituted_reality)
    reality_path = substituted_reality / "reality_object.json"
    reality = RealityObject.from_wire(_wire(reality_path))
    reality_path.write_text(
        reality.model_copy(update={"uncertainty": "substituted"}).model_dump_json()
    )
    assert run_cli(["report", "show", str(substituted_reality)]) != 0

    malformed_metric = tmp_path / "e2-malformed-metric"
    shutil.copytree(source, malformed_metric)
    (malformed_metric / "metric_proposal.json").write_text('{"malformed":true}')
    assert run_cli(["report", "show", str(malformed_metric)]) != 0


def test_append_only_supersession_preserves_failure_evidence(tmp_path: Path) -> None:
    store = RegistryStore(
        tmp_path / "lineage.jsonl", clock=lambda: datetime(2026, 1, 1, tzinfo=UTC)
    )
    old = {"kind": "report", "version": 1, "known_failures": ["failed-gate"]}
    new = {"kind": "report", "version": 2, "known_failures": []}
    for state in (
        LifecycleState.DRAFT,
        LifecycleState.SUBMITTED,
        LifecycleState.CONTRACT_BOUND,
        LifecycleState.VALIDATION_PENDING,
        LifecycleState.PROVISIONAL,
    ):
        store.append(
            actor_role="validator",
            actor_id="agent:validator",
            object_payload=old,
            event_type=state,
            event_payload={},
        )
    prefix = store.path.read_bytes()
    successor = store.append(
        actor_role="proposer",
        actor_id="agent:proposer",
        object_payload=new,
        event_type=LifecycleState.DRAFT,
        event_payload={"supersedes": content_id(old)},
    )
    store.append(
        actor_role="authorizer",
        actor_id="agent:authorizer",
        object_payload=old,
        event_type=LifecycleState.SUPERSEDED,
        event_payload={"successor_object_id": successor.object_id},
    )
    events = store.verify()
    assert store.path.read_bytes().startswith(prefix)
    assert any("failed-gate" in event.object_payload_json for event in events)
