import pytest

from aire_prime.core.canonical import content_id
from aire_prime.measurement.comparison import (
    ComparisonArm,
    ComparisonStatus,
    DeclaredAdjustment,
    ResourceComparison,
    compare_arms,
)
from aire_prime.measurement.decision import (
    CandidateSamples,
    ControlContract,
    ControlSamples,
    DecisionStatus,
    ProtectedContract,
    ProtectedDimension,
    ProtectedRequirement,
    decide_improvement,
)
from aire_prime.measurement.resources import ResourceMeasurement, ResourceVector


def observed(value: float) -> ResourceMeasurement:
    return ResourceMeasurement.observed(value)


def complete_resources(**overrides: float) -> ResourceVector:
    values = {
        "packet_bytes": 100.0,
        "peak_resident_bytes": 1_000.0,
        "operation_count": 10.0,
        "interaction_count": 3.0,
        "elapsed_time": 2.0,
        "external_calls": 0.0,
        "declared_energy_proxy": 20.0,
        "declared_bandwidth": 120.0,
    }
    values.update(overrides)
    return ResourceVector(**{name: observed(value) for name, value in values.items()})


def arm(
    *,
    resources: ResourceVector,
    prior: str = "prior:none",
    arm_id: str = "arm:candidate",
) -> ComparisonArm:
    return ComparisonArm(
        arm_id=arm_id,
        resources=resources,
        observation_access=("observation:x", "intervention:y"),
        receiver_prior_id=prior,
    )


def matched_control(
    *,
    name: str,
    samples: tuple[float, ...],
    candidate: ComparisonArm,
) -> ControlSamples:
    control_arm = arm(
        resources=candidate.resources,
        arm_id=f"arm:control-{name}",
    )
    comparison = compare_arms(candidate, control_arm)
    return ControlSamples(
        name=name,
        samples=samples,
        control_arm_id=control_arm.content_id,
        measurement_artifact_id=content_id({"control": name, "samples": samples}),
        candidate_arm=candidate,
        control_arm=control_arm,
        comparison=comparison,
    )


def control_contract(controls: tuple[ControlSamples, ...]) -> ControlContract:
    return ControlContract(
        required_control_ids=tuple(control.control_arm_id for control in controls)
    )


def candidate_measurements(
    candidate: ComparisonArm, samples: tuple[float, ...]
) -> CandidateSamples:
    return CandidateSamples(
        name="proposed",
        samples=samples,
        candidate_arm_id=candidate.content_id,
        measurement_artifact_id=content_id(
            {"candidate_id": candidate.content_id, "samples": samples}
        ),
        metric_id="metric:test-effect:v1",
    )


def protected_measurement(
    *, name: str, samples: tuple[float, ...], floor: float
) -> ProtectedDimension:
    return ProtectedDimension(
        name=name,
        samples=samples,
        floor=floor,
        measurement_artifact_id=content_id({"name": name, "samples": samples, "floor": floor}),
    )


def protected_contract(
    dimensions: tuple[ProtectedDimension, ...],
) -> ProtectedContract:
    return ProtectedContract(
        requirements=tuple(
            ProtectedRequirement(name=dimension.name, floor=dimension.floor)
            for dimension in dimensions
        )
    )


@pytest.mark.parametrize(
    ("dimension", "value"),
    (
        ("packet_bytes", 101.0),
        ("interaction_count", 4.0),
        ("elapsed_time", 3.0),
        ("declared_bandwidth", 121.0),
    ),
)
def test_unadjusted_resource_mismatch_is_invalid(dimension: str, value: float) -> None:
    candidate = arm(resources=complete_resources())
    control = arm(resources=complete_resources(**{dimension: value}))

    comparison = compare_arms(candidate, control)

    assert comparison.status is ComparisonStatus.INVALID
    assert dimension in comparison.mismatched_dimensions


def test_observation_or_hidden_prior_mismatch_is_invalid() -> None:
    resources = complete_resources()
    candidate = arm(resources=resources)
    observation_control = arm(resources=resources).model_copy(
        update={"observation_access": ("observation:x",)}
    )
    prior_control = arm(resources=resources, prior="prior:privileged")

    assert compare_arms(candidate, observation_control).status is ComparisonStatus.INVALID
    assert compare_arms(candidate, prior_control).status is ComparisonStatus.INVALID
    with pytest.raises(ValueError, match="resource dimensions"):
        DeclaredAdjustment(
            dimension="receiver_prior_id",
            method="declared offset",
            rationale="must remain forbidden",
            maximum_absolute_difference=1.0,
        )


def test_missing_measurement_stays_undetermined_and_is_never_zero() -> None:
    candidate = arm(resources=complete_resources())
    control_resources = complete_resources().model_copy(
        update={"elapsed_time": ResourceMeasurement.undetermined()}
    )

    comparison = compare_arms(candidate, arm(resources=control_resources))

    assert comparison.status is ComparisonStatus.UNDETERMINED
    assert comparison.undetermined_dimensions == ("elapsed_time",)
    assert control_resources.elapsed_time.value is None


def test_declared_adjustment_makes_a_resource_difference_explicit() -> None:
    candidate = arm(resources=complete_resources())
    control = arm(resources=complete_resources(packet_bytes=110.0))

    comparison = compare_arms(
        candidate,
        control,
        declared_adjustments=(
            DeclaredAdjustment(
                dimension="packet_bytes",
                method="predeclared padding correction",
                rationale="ten-byte framing difference",
                maximum_absolute_difference=10.0,
            ),
        ),
    )

    assert comparison.status is ComparisonStatus.VALID
    assert comparison.adjusted_dimensions == ("packet_bytes",)


def test_bootstrap_decision_is_deterministic_and_uses_maximum_control() -> None:
    candidate = arm(resources=complete_resources())
    controls = (
        matched_control(
            name="random-subspace",
            samples=(0.10, 0.12, 0.11, 0.09),
            candidate=candidate,
        ),
        matched_control(
            name="activation-permutation",
            samples=(0.20, 0.18, 0.19, 0.21),
            candidate=candidate,
        ),
        matched_control(
            name="replacement",
            samples=(0.05, 0.04, 0.06, 0.05),
            candidate=candidate,
        ),
    )
    protected = (
        protected_measurement(name="safety", samples=(0.95, 0.96, 0.94, 0.95), floor=0.90),
    )

    first = decide_improvement(
        candidate_samples=candidate_measurements(candidate, (0.8, 0.9, 0.85, 0.88)),
        controls=controls,
        control_contract=control_contract(controls),
        protected_dimensions=protected,
        protected_contract=protected_contract(protected),
        delta=0.10,
        alpha=0.05,
        seed=101,
        bootstrap_iterations=500,
    )
    second = decide_improvement(
        candidate_samples=candidate_measurements(candidate, (0.8, 0.9, 0.85, 0.88)),
        controls=controls,
        control_contract=control_contract(controls),
        protected_dimensions=protected,
        protected_contract=protected_contract(protected),
        delta=0.10,
        alpha=0.05,
        seed=101,
        bootstrap_iterations=500,
    )

    assert first == second
    assert first.status is DecisionStatus.PROVISIONAL
    assert first.control_samples_ids == tuple(
        control.content_id for control in sorted(controls, key=lambda item: item.name)
    )
    assert len(first.margin_summary.sorted_bootstrap_effects) == 500
    assert tuple(result.name for result in first.control_summaries) == (
        "activation-permutation",
        "random-subspace",
        "replacement",
    )

    changed_controls = (
        controls[0].model_copy(
            update={"measurement_artifact_id": content_id({"replacement-artifact": True})}
        ),
        *controls[1:],
    )
    changed = decide_improvement(
        candidate_samples=candidate_measurements(candidate, (0.8, 0.9, 0.85, 0.88)),
        controls=changed_controls,
        control_contract=control_contract(changed_controls),
        protected_dimensions=protected,
        protected_contract=protected_contract(protected),
        delta=0.10,
        alpha=0.05,
        seed=101,
        bootstrap_iterations=500,
    )
    assert changed.control_samples_ids != first.control_samples_ids
    assert changed.content_id != first.content_id


def test_protected_regression_rejects_and_missing_samples_are_undetermined() -> None:
    candidate = arm(resources=complete_resources())
    controls = (
        matched_control(
            name="sham",
            samples=(0.1, 0.1, 0.1),
            candidate=candidate,
        ),
    )
    rejected = decide_improvement(
        candidate_samples=candidate_measurements(candidate, (0.9, 0.9, 0.9)),
        controls=controls,
        control_contract=control_contract(controls),
        protected_dimensions=(
            protected_measurement(name="safety", samples=(0.5, 0.6, 0.5), floor=0.8),
        ),
        protected_contract=ProtectedContract(
            requirements=(ProtectedRequirement(name="safety", floor=0.8),)
        ),
        delta=0.1,
        alpha=0.05,
        seed=7,
        bootstrap_iterations=200,
    )
    undetermined = decide_improvement(
        candidate_samples=candidate_measurements(candidate, ()),
        controls=controls,
        control_contract=control_contract(controls),
        protected_dimensions=(),
        protected_contract=ProtectedContract(),
        delta=0.1,
        alpha=0.05,
        seed=7,
        bootstrap_iterations=200,
    )

    assert rejected.status is DecisionStatus.REJECTED
    assert "protected-dimension-regression" in rejected.reasons
    assert undetermined.status is DecisionStatus.UNDETERMINED
    assert "missing-measurements" in undetermined.reasons


def test_unfavorable_control_cannot_be_dropped_and_invalid_match_is_undetermined() -> None:
    resources = complete_resources()
    candidate = arm(resources=resources)
    controls = (
        matched_control(
            name="favorable-low",
            samples=(0.1, 0.1, 0.1, 0.1),
            candidate=candidate,
        ),
        matched_control(
            name="unfavorable-high",
            samples=(0.85, 0.86, 0.84, 0.85),
            candidate=candidate,
        ),
    )

    rejected = decide_improvement(
        candidate_samples=candidate_measurements(candidate, (0.8, 0.82, 0.81, 0.83)),
        controls=controls,
        control_contract=control_contract(controls),
        protected_dimensions=(),
        protected_contract=ProtectedContract(),
        delta=0.01,
        alpha=0.05,
        seed=13,
        bootstrap_iterations=300,
    )
    invalid_control_arm = arm(
        resources=complete_resources(packet_bytes=101.0),
        arm_id="arm:control-favorable-low",
    )
    invalid_controls = (
        ControlSamples(
            name=controls[0].name,
            samples=controls[0].samples,
            control_arm_id=invalid_control_arm.content_id,
            measurement_artifact_id=controls[0].measurement_artifact_id,
            candidate_arm=candidate,
            control_arm=invalid_control_arm,
            comparison=compare_arms(candidate, invalid_control_arm),
        ),
        controls[1],
    )
    undetermined = decide_improvement(
        candidate_samples=candidate_measurements(candidate, (0.8, 0.82, 0.81, 0.83)),
        controls=invalid_controls,
        control_contract=control_contract(invalid_controls),
        protected_dimensions=(),
        protected_contract=ProtectedContract(),
        delta=0.01,
        alpha=0.05,
        seed=13,
        bootstrap_iterations=300,
    )

    assert rejected.status is DecisionStatus.REJECTED
    assert tuple(summary.name for summary in rejected.control_summaries) == (
        "favorable-low",
        "unfavorable-high",
    )
    assert undetermined.status is DecisionStatus.UNDETERMINED
    assert undetermined.reasons == ("resource-comparison-favorable-low-invalid",)


def test_inconsistent_comparison_cannot_forge_valid_status() -> None:
    matched = (
        "declared_bandwidth",
        "declared_energy_proxy",
        "elapsed_time",
        "external_calls",
        "interaction_count",
        "observation_access",
        "operation_count",
        "peak_resident_bytes",
        "receiver_prior_id",
    )
    with pytest.raises(ValueError, match="status"):
        ResourceComparison(
            candidate_id="sha256:" + "1" * 64,
            control_id="sha256:" + "2" * 64,
            status=ComparisonStatus.VALID,
            matched_dimensions=matched,
            mismatched_dimensions=("packet_bytes",),
        )


def test_precommitted_unfavorable_control_cannot_be_omitted() -> None:
    candidate = arm(resources=complete_resources())
    controls = (
        matched_control(
            name="favorable-low",
            samples=(0.1, 0.1, 0.1, 0.1),
            candidate=candidate,
        ),
        matched_control(
            name="required-high",
            samples=(0.9, 0.9, 0.9, 0.9),
            candidate=candidate,
        ),
    )
    contract = control_contract(controls)

    decision = decide_improvement(
        candidate_samples=candidate_measurements(candidate, (0.8, 0.8, 0.8, 0.8)),
        controls=(controls[0],),
        control_contract=contract,
        protected_dimensions=(),
        protected_contract=ProtectedContract(),
        delta=0.01,
        alpha=0.05,
        seed=19,
        bootstrap_iterations=200,
    )

    assert decision.status is DecisionStatus.UNDETERMINED
    assert decision.reasons == (f"missing-control:{controls[1].control_arm_id}",)


def test_discrete_resources_reject_fractional_counts() -> None:
    with pytest.raises(ValueError, match="packet_bytes must be an integral count"):
        ResourceVector(packet_bytes=observed(1.5))


def test_candidate_samples_must_match_the_compared_candidate_arm() -> None:
    candidate = arm(resources=complete_resources())
    controls = (
        matched_control(
            name="sham",
            samples=(0.1, 0.1, 0.1),
            candidate=candidate,
        ),
    )
    other_candidate = arm(
        resources=complete_resources(operation_count=11.0),
        arm_id="arm:other-candidate",
    )

    decision = decide_improvement(
        candidate_samples=candidate_measurements(other_candidate, (0.9, 0.9, 0.9)),
        controls=controls,
        control_contract=control_contract(controls),
        protected_dimensions=(),
        protected_contract=ProtectedContract(),
        delta=0.1,
        alpha=0.05,
        seed=5,
        bootstrap_iterations=200,
    )

    assert decision.status is DecisionStatus.UNDETERMINED
    assert decision.reasons == ("candidate-samples-arm-mismatch",)


def test_precommitted_failing_protected_dimension_cannot_be_omitted() -> None:
    candidate = arm(resources=complete_resources())
    controls = (
        matched_control(
            name="sham",
            samples=(0.1, 0.1, 0.1),
            candidate=candidate,
        ),
    )
    contract = ProtectedContract(requirements=(ProtectedRequirement(name="safety", floor=0.8),))

    decision = decide_improvement(
        candidate_samples=candidate_measurements(candidate, (0.9, 0.9, 0.9)),
        controls=controls,
        control_contract=control_contract(controls),
        protected_dimensions=(),
        protected_contract=contract,
        delta=0.1,
        alpha=0.05,
        seed=5,
        bootstrap_iterations=200,
    )

    assert decision.status is DecisionStatus.UNDETERMINED
    assert decision.reasons == ("missing-protected:safety",)


def test_adjustment_beyond_its_precommitted_bound_remains_invalid() -> None:
    candidate = arm(resources=complete_resources())
    control = arm(
        resources=complete_resources(packet_bytes=120.0),
        arm_id="arm:adjusted-control",
    )
    comparison = compare_arms(
        candidate,
        control,
        declared_adjustments=(
            DeclaredAdjustment(
                dimension="packet_bytes",
                method="bounded padding correction",
                rationale="precommitted maximum",
                maximum_absolute_difference=10.0,
            ),
        ),
    )

    assert comparison.status is ComparisonStatus.INVALID
    assert comparison.mismatched_dimensions == ("packet_bytes",)
