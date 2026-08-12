import subprocess
import sys
from pathlib import Path

from aire_prime.experiments.e3.pilot import (
    build_pilot_manifest,
    run_pilot,
)


def test_pilot_has_only_baselines_and_development_seed_domain() -> None:
    manifest = build_pilot_manifest(root_seed=301)

    assert manifest.split == "development"
    assert "candidate" not in manifest.arm_ids
    assert manifest.arm_ids == ("B0", "B1", "B2", "B3", "B4", "B5", "B6", "B9")
    assert manifest.confirmatory_seed_domain is None
    assert manifest.candidate_access is False


def test_pilot_produces_complete_world_recipient_arm_matrix_and_variance() -> None:
    result = run_pilot(root_seed=301)

    assert len(result.blocks) == 6 * 4 * 8
    assert {block.arm_id for block in result.blocks} == set(result.manifest.arm_ids)
    assert {block.recipient_id for block in result.blocks} == {
        "recipient-linear",
        "recipient-recurrent",
        "recipient-feedforward",
        "recipient-interpreter",
    }
    assert result.oracle_headroom > 0
    assert result.world_variance >= 0
    assert result.capacity_gap is True
    assert all(block.valid for block in result.blocks)


def test_pilot_cannot_run_confirmatory_split_or_candidate_artifact() -> None:
    result = run_pilot(root_seed=301)
    assert result.manifest.split == "development"
    candidate_path = (
        Path(__file__).parents[3]
        / "aire_prime"
        / "experiments"
        / "e3"
        / "candidate.py"
    )
    assert not candidate_path.exists()


def test_pilot_module_writes_a_replayable_result(tmp_path: Path) -> None:
    output = tmp_path / "pilot"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "aire_prime.experiments.e3.pilot",
            "--seed",
            "301",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip().startswith("sha256:")
    assert (output / "pilot_manifest.json").exists()
    assert (output / "pilot_result.json").exists()
