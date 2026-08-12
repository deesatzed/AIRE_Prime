import hashlib

import pytest

from aire_prime.experiments.e3.run import (
    E3_ELIGIBLE_ARM_IDS,
    derive_confirmatory_seed,
    run_e3_evaluation,
)


def test_confirmatory_seed_derivation_is_domain_and_commit_bound() -> None:
    first = derive_confirmatory_seed("abc123")
    second = derive_confirmatory_seed("abc123")
    assert first == second
    assert first == hashlib.sha256(b"AIRE-E3-CONFIRMATORY-V1abc123").hexdigest()
    assert first != derive_confirmatory_seed("abc124")


def test_development_runner_has_complete_candidate_baseline_recipient_matrix() -> None:
    result = run_e3_evaluation(split="development", root_seed=301)

    assert result.manifest.confirmatory_seed is None
    assert set(E3_ELIGIBLE_ARM_IDS) <= set(result.manifest.arm_ids)
    assert "B9" in result.manifest.arm_ids
    assert len(result.blocks) == 6 * (len(E3_ELIGIBLE_ARM_IDS) + 1) * 4
    assert all(block.valid for block in result.blocks)
    assert all(block.resource_state == "observed" for block in result.blocks)
    assert result.candidate_packet_id.startswith("sha256:")


def test_confirmatory_runner_requires_pushed_freeze_commit() -> None:
    with pytest.raises(ValueError, match="frozen commit"):
        run_e3_evaluation(split="confirmatory", root_seed=301)
