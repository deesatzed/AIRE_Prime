import random
from dataclasses import dataclass
from typing import Protocol

import pytest

from aire_prime.core.canonical import content_id
from aire_prime.measurement.comparison import ComparisonArm, ComparisonStatus, compare_arms
from aire_prime.measurement.decision import (
    CandidateSamples,
    ControlContract,
    ControlSamples,
    DecisionStatus,
    ImprovementDecision,
    ProtectedContract,
    ProtectedDimension,
    ProtectedRequirement,
    decide_improvement,
)
from aire_prime.measurement.resources import ResourceMeasurement, ResourceVector


@dataclass(frozen=True)
class GamingAttempt:
    objective_samples: tuple[float, ...]
    task_outcomes: tuple[float, ...]
    observation_access: tuple[str, ...] = ("observation:x",)
    receiver_prior_id: str = "prior:none"
    protected_floor: float = 0.75


class GamingAgent(Protocol):
    name: str

    def run(self) -> GamingAttempt: ...


class RandomNoveltyAgent:
    name = "novelty-by-random-output"

    def run(self) -> GamingAttempt:
        generator = random.Random(19)
        outputs = tuple(generator.randrange(2) for _ in range(16))
        novelty = tuple(
            float(index == 0 or value != outputs[index - 1])
            for index, value in enumerate(outputs)
        )
        task_outcomes = tuple(float(value == 1) for value in outputs)
        return GamingAttempt(
            objective_samples=novelty,
            task_outcomes=task_outcomes,
            protected_floor=0.9,
        )


class AllStateEmpowermentAgent:
    name = "empowerment-by-consuming-all-state"

    def run(self) -> GamingAttempt:
        return GamingAttempt(
            objective_samples=(1.0,) * 16,
            task_outcomes=(1.0,) * 16,
            observation_access=("observation:x", "hidden:all-state"),
        )


class RefusalPredictionAgent:
    name = "prediction-by-refusing-difficult-cases"

    def run(self) -> GamingAttempt:
        predictions: tuple[int | None, ...] = tuple(
            1 if index % 2 == 0 else None for index in range(16)
        )
        answered_scores = tuple(1.0 for prediction in predictions if prediction is not None)
        coverage = tuple(float(prediction is not None) for prediction in predictions)
        return GamingAttempt(
            objective_samples=answered_scores,
            task_outcomes=coverage,
            protected_floor=0.9,
        )


class UndeclaredPriorEfficiencyAgent:
    name = "packet-efficiency-by-undeclared-prior"

    def run(self) -> GamingAttempt:
        return GamingAttempt(
            objective_samples=(1.0,) * 16,
            task_outcomes=(1.0,) * 16,
            receiver_prior_id="prior:undeclared-specialist",
        )


def _resources() -> ResourceVector:
    observed = ResourceMeasurement.observed
    return ResourceVector(
        packet_bytes=observed(100.0),
        peak_resident_bytes=observed(1000.0),
        operation_count=observed(10.0),
        interaction_count=observed(3.0),
        elapsed_time=observed(2.0),
        external_calls=observed(0.0),
        declared_energy_proxy=observed(20.0),
        declared_bandwidth=observed(100.0),
    )


def _arm(
    arm_id: str,
    *,
    access: tuple[str, ...] = ("observation:x",),
    prior: str = "prior:none",
) -> ComparisonArm:
    return ComparisonArm(
        arm_id=arm_id,
        resources=_resources(),
        observation_access=access,
        receiver_prior_id=prior,
    )


def _decision(
    *,
    candidate: ComparisonArm,
    control: ComparisonArm,
    candidate_values: tuple[float, ...] = (1.0,) * 16,
    control_values: tuple[float, ...] = (0.0,) * 16,
    protected_values: tuple[float, ...] = (1.0,) * 16,
    protected_floor: float = 0.75,
) -> ImprovementDecision:
    control_samples = ControlSamples(
        name="frozen-control",
        samples=control_values,
        control_arm_id=control.content_id,
        measurement_artifact_id=content_id({"samples": control_values}),
        candidate_arm=candidate,
        control_arm=control,
        comparison=compare_arms(candidate, control),
    )
    protected = ProtectedDimension(
        name="task-completion",
        samples=protected_values,
        floor=protected_floor,
        measurement_artifact_id=content_id({"protected": protected_values}),
    )
    return decide_improvement(
        candidate_samples=CandidateSamples(
            name="candidate",
            samples=candidate_values,
            candidate_arm_id=candidate.content_id,
            measurement_artifact_id=content_id({"candidate": candidate_values}),
            metric_id="metric:adversarial:v1",
        ),
        controls=(control_samples,),
        control_contract=ControlContract(required_control_ids=(control.content_id,)),
        protected_dimensions=(protected,),
        protected_contract=ProtectedContract(
            requirements=(
                ProtectedRequirement(name=protected.name, floor=protected.floor),
            )
        ),
        delta=0.1,
        alpha=0.05,
        seed=77,
        bootstrap_iterations=200,
    )


def _evaluate_gaming_agent(agent: GamingAgent) -> ImprovementDecision:
    attempt = agent.run()
    return _decision(
        candidate=_arm(
            f"candidate:{agent.name}",
            access=attempt.observation_access,
            prior=attempt.receiver_prior_id,
        ),
        control=_arm(f"control:{agent.name}"),
        candidate_values=attempt.objective_samples,
        protected_values=attempt.task_outcomes,
        protected_floor=attempt.protected_floor,
    )


@pytest.mark.parametrize(
    ("agent", "expected_status", "expected_reason"),
    (
        (
            RandomNoveltyAgent(),
            DecisionStatus.REJECTED,
            "protected-dimension-regression",
        ),
        (
            AllStateEmpowermentAgent(),
            DecisionStatus.UNDETERMINED,
            "resource-comparison-frozen-control-invalid",
        ),
        (
            RefusalPredictionAgent(),
            DecisionStatus.REJECTED,
            "protected-dimension-regression",
        ),
        (
            UndeclaredPriorEfficiencyAgent(),
            DecisionStatus.UNDETERMINED,
            "resource-comparison-frozen-control-invalid",
        ),
    ),
)
def test_metric_gaming_is_rejected_by_frozen_contracts(
    agent: GamingAgent,
    expected_status: DecisionStatus,
    expected_reason: str,
) -> None:
    decision = _evaluate_gaming_agent(agent)

    assert decision.status is expected_status, agent.name
    assert expected_reason in decision.reasons, agent.name
    if expected_status is DecisionStatus.UNDETERMINED:
        assert decision.comparison_ids


def test_observation_and_prior_gaming_are_hard_mismatches_not_adjustable() -> None:
    candidate = _arm(
        "candidate:covert",
        access=("observation:x", "hidden:all-state"),
        prior="prior:undeclared-specialist",
    )
    control = _arm("control:covert")

    comparison = compare_arms(candidate, control)

    assert comparison.status is ComparisonStatus.INVALID
    assert "observation_access" in comparison.mismatched_dimensions
    assert "receiver_prior_id" in comparison.mismatched_dimensions
    assert not comparison.adjusted_dimensions
