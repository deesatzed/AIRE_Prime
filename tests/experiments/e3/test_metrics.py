import pytest

from aire_prime.experiments.e3.analysis import (
    E3Block,
    adaptation_auc,
    analyze_confirmatory,
    holm_adjust,
)


def _blocks() -> tuple[E3Block, ...]:
    rows: list[E3Block] = []
    for world_index, (candidate, baseline_a, baseline_b) in enumerate(
        ((0.90, 0.55, 0.75), (0.85, 0.60, 0.70), (0.95, 0.65, 0.80))
    ):
        for arm_id, auc in (
            ("candidate", candidate),
            ("baseline-a", baseline_a),
            ("baseline-b", baseline_b),
        ):
            rows.append(
                E3Block(
                    arm_id=arm_id,
                    world_id=f"world-{world_index}",
                    shift_family="surface",
                    recipient_id="recipient-linear",
                    auc=auc,
                    valid=True,
                    resource_state="observed",
                )
            )
    return tuple(rows)


def test_adaptation_auc_is_normalized_trapezoidal_area() -> None:
    assert adaptation_auc((0.0, 1.0, 1.0)) == pytest.approx(0.75)


def test_bootstrap_resamples_worlds_and_selects_maximum_baseline_per_replicate() -> None:
    result = analyze_confirmatory(_blocks(), seed=991, bootstrap_replicates=128)

    assert result.resampling_unit == "world"
    assert result.maximum_baseline == "baseline-b"
    assert len(result.bootstrap_distribution) == 128
    assert result.point_effect > 0


def test_invalid_or_missing_resource_evidence_is_undetermined() -> None:
    blocks = list(_blocks())
    blocks[-1] = blocks[-1].model_copy(update={"resource_state": "undetermined"})

    result = analyze_confirmatory(tuple(blocks), seed=991, bootstrap_replicates=32)

    assert result.status == "undetermined"


def test_holm_adjustment_is_deterministic_and_monotone() -> None:
    adjusted = holm_adjust((0.01, 0.04, 0.20))

    assert adjusted == pytest.approx((0.03, 0.08, 0.20))
    assert adjusted[0] <= adjusted[1] <= adjusted[2]
