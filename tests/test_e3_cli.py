import json
from pathlib import Path

from aire_prime.cli import run_cli
from aire_prime.experiments.e3.report import write_e3_result
from aire_prime.experiments.e3.run import run_e3_evaluation


def test_e3_pilot_cli_writes_baseline_only_artifacts(tmp_path: Path, capsys) -> None:
    output = tmp_path / "pilot"
    assert run_cli(["e3", "pilot", "--seed", "301", "--output", str(output)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pilot_id"].startswith("sha256:")
    assert (output / "pilot_result.json").exists()


def test_e3_report_show_rejects_grounding_escalation(tmp_path: Path, capsys) -> None:
    output = tmp_path / "e3"
    write_e3_result(run_e3_evaluation(split="development", root_seed=301), output)
    assert run_cli(["report", "show", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["grounding"] == "G-S"
    report = json.loads((output / "e3_report.json").read_bytes())
    report["grounding"] = "G-P"
    (output / "e3_report.json").write_text(json.dumps(report), encoding="utf-8")
    assert run_cli(["report", "show", str(output)]) == 2
