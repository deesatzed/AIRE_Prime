import pytest

from aire_prime.measurement.ablation import AblationKind, run_standard_ablations


def test_standard_ablation_report_retains_targeted_and_every_sham_control() -> None:
    report = run_standard_ablations(
        activations=((1.0, 2.0, 3.0), (2.0, 4.0, 6.0), (3.0, 6.0, 9.0)),
        targeted_dimensions=(0,),
        seed=17,
    )

    assert {result.kind for result in report.results} == set(AblationKind)
    assert len(report.results) == 4
    assert report.targeted.kind is AblationKind.TARGETED
    assert {result.kind for result in report.sham_controls} == {
        AblationKind.RANDOM_SUBSPACE,
        AblationKind.ACTIVATION_PERMUTATION,
        AblationKind.REPRESENTATION_REPLACEMENT,
    }


def test_random_subspace_is_seeded_and_equal_size() -> None:
    arguments = {
        "activations": ((1.0, 2.0, 3.0, 4.0), (4.0, 3.0, 2.0, 1.0)),
        "targeted_dimensions": (0, 1),
        "seed": 23,
    }

    first = run_standard_ablations(**arguments)
    second = run_standard_ablations(**arguments)
    random_control = next(
        result
        for result in first.results
        if result.kind is AblationKind.RANDOM_SUBSPACE
    )

    assert first == second
    assert len(random_control.selected_dimensions) == 2
    assert random_control.selected_dimensions != (0, 1)
    assert first.activation_content_id
    assert first.target_content_id


def test_equal_size_random_sham_rejects_insufficient_non_target_dimensions() -> None:
    with pytest.raises(ValueError, match="enough non-target dimensions"):
        run_standard_ablations(
            activations=((1.0, 2.0, 3.0), (3.0, 2.0, 1.0)),
            targeted_dimensions=(0, 1),
            seed=23,
        )
