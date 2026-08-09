import json
from pathlib import Path

import pytest

from aire_prime.experiments.e1.run import run_e1


def test_fresh_recipient_adapts_composes_repairs_and_passes_withheld_tests(
    tmp_path: Path,
) -> None:
    result = run_e1(seed=101, output=tmp_path / "e1")

    assert result.receiver_id == "agent:e1-recipient-fresh"
    assert result.transfer.success
    assert result.composition.success
    assert result.repair.success
    assert result.withheld_conformance_passed
    assert result.realization_receipts
    assert all(receipt.success for receipt in result.realization_receipts)
    assert {response.content_ids[0] for response in result.agent_responses} == {
        result.transfer.artifact_content_id,
        result.composition.artifact_content_id,
        result.repair.artifact_content_id,
    }
    assert all(
        response.sender.agent_id == result.receiver_id
        for response in result.agent_responses
    )
    assert all(
        response.receiver.agent_id == "agent:e1-proposer"
        for response in result.agent_responses
    )
    assert "world-seed:101" in result.evaluation_contract.controls
    packet = json.loads((tmp_path / "e1" / "transfer_packet.json").read_text())
    assert "withheld_tests" not in packet["contract"]
    assert not any(
        test_name in (tmp_path / "e1" / "transfer_packet.json").read_text()
        for test_name in (
            "resource-substitution",
            "port-continuity",
            "single-component-repair",
        )
    )
    assert "tasks" not in packet
    assert len(result.agent_requests) == len(result.agent_responses) == 3
    assert all(
        response.request_content_id == request.content_id
        for request, response in zip(
            result.agent_requests, result.agent_responses, strict=True
        )
    )


def test_frozen_alternatives_are_bandwidth_matched_and_changed_resource_fails(
    tmp_path: Path,
) -> None:
    result = run_e1(seed=101, output=tmp_path / "e1")

    assert {baseline.kind for baseline in result.baselines} == {
        "fixed-instance",
        "demonstration-list",
        "lookup-policy",
        "random-opaque-packet",
        "conventional-feature-schema",
    }
    assert all(
        baseline.packet_bytes == result.transfer_packet_bytes for baseline in result.baselines
    )
    assert not next(
        baseline for baseline in result.baselines if baseline.kind == "fixed-instance"
    ).changed_resource_success
    assert all(baseline.failed_tests for baseline in result.baselines)
    assert all(response.request_content_id for response in result.baseline_responses)
    assert result.evaluation_contract.baseline_ids == result.report.baseline_packet_ids
    assert result.report.baseline_ids != result.report.baseline_packet_ids
    budget = dict(result.evaluation_contract.resource_budget)
    assert budget["interactions"] == 3
    assert all(baseline.interactions == 3 for baseline in result.baselines)
    assert all(
        baseline.transmitted_input_bytes == budget["transmitted_input_bytes"]
        for baseline in result.baselines
    )
    assert len(result.baseline_requests) == len(result.baseline_responses) == 15
    assert all("language" not in baseline.kind for baseline in result.baselines)


def test_e1_emits_typed_reports_registry_events_and_deterministic_ids(tmp_path: Path) -> None:
    first = run_e1(seed=101, output=tmp_path / "a")
    second = run_e1(seed=101, output=tmp_path / "b")

    assert first.report.content_id == second.report.content_id
    assert first.evaluation_contract.content_id == second.evaluation_contract.content_id
    assert first.reality_object.content_id == second.reality_object.content_id
    assert first.bridge_contract.content_id == second.bridge_contract.content_id
    assert first.improvement_report.content_id == second.improvement_report.content_id
    assert first.registry_head == second.registry_head
    assert first.sense_proposal is None

    output = tmp_path / "a"
    expected_files = {
        "bridge_contract.json",
        "agent_requests.jsonl",
        "agent_responses.jsonl",
        "baseline_requests.jsonl",
        "baseline_responses.jsonl",
        "baseline_results.json",
        "e1_report.json",
        "evaluation_contract.json",
        "improvement_report.json",
        "reality_object.json",
        "realization_receipts.json",
        "registry.jsonl",
        "registry.jsonl.head",
        "transfer_packet.json",
    }
    assert expected_files <= {path.name for path in output.iterdir()}
    report_payload = json.loads((output / "e1_report.json").read_text())
    assert report_payload["content_id"] == first.report.content_id
    assert report_payload["classification"] == "simulated-capability-transfer"


def test_e1_rejects_a_nonempty_output_directory(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    (output / "unrelated.txt").write_text("preserve me")

    with pytest.raises(ValueError, match="must be empty"):
        run_e1(seed=101, output=output)

    assert (output / "unrelated.txt").read_text() == "preserve me"
