from datetime import UTC, datetime
from pathlib import Path

from aire_prime.cli import run_cli
from aire_prime.objects.evidence import EvidenceState, GroundingClass, OccurrenceMaturity
from aire_prime.objects.reports import OccurrenceReport
from aire_prime.registry.lifecycle import LifecycleState
from aire_prime.registry.store import RegistryStore


def test_schema_check_and_registry_verify_commands(tmp_path: Path, capsys: object) -> None:
    assert run_cli(["schema", "check"]) == 0
    registry_path = tmp_path / "registry.jsonl"
    store = RegistryStore(registry_path, clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    event = store.append(
        actor_role="validator",
        actor_id="agent:test",
        object_payload={"value": 1},
        event_type=LifecycleState.DRAFT,
        event_payload={"test": True},
    )

    assert run_cli(["registry", "verify", str(registry_path)]) == 0
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert event.event_content_id in output


def test_registry_corruption_returns_nonzero(tmp_path: Path) -> None:
    path = tmp_path / "registry.jsonl"
    path.write_text('{"not":"an event"}\n', encoding="utf-8")

    assert run_cli(["registry", "verify", str(path)]) != 0


def test_report_show_rejects_invalid_grounding_escalation(tmp_path: Path) -> None:
    report = OccurrenceReport(
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        validity_region=("test",),
        proposal_id="sha256:" + "1" * 64,
        contract_id="sha256:" + "2" * 64,
        validator_id="agent:validator",
        evidence_state=EvidenceState(
            occurrence=OccurrenceMaturity.CLAIMED, grounding=GroundingClass.PHYSICAL
        ),
        evidence_attachments=("sha256:" + "3" * 64,),
        resource_measurements=(("bytes", 1.0),),
    )
    path = tmp_path / "occurrence_report.json"
    path.write_text(report.model_dump_json(), encoding="utf-8")

    assert run_cli(["report", "show", str(path)]) != 0


def test_run_returns_nonzero_on_containment_refusal(tmp_path: Path, monkeypatch: object) -> None:
    import aire_prime.cli as cli_module

    def refuse(*, seed: int, output: Path) -> None:
        del seed, output
        raise RuntimeError("ContainmentUnavailable")

    monkeypatch.setattr(cli_module, "run_e1", refuse)  # type: ignore[attr-defined]
    assert run_cli(["e1", "run", "--seed", "1", "--output", str(tmp_path / "e1")]) != 0
