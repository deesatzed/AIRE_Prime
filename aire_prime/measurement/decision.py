import math
import random
from enum import StrEnum
from statistics import fmean
from typing import Self

from pydantic import field_validator, model_validator

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.measurement.comparison import (
    ComparisonArm,
    ComparisonStatus,
    DeclaredAdjustment,
    ResourceComparison,
    compare_arms,
)
from aire_prime.objects import ContentID


class DecisionStatus(StrEnum):
    PROVISIONAL = "provisional"
    REJECTED = "rejected"
    UNDETERMINED = "undetermined"


class NamedSamples(FrozenModel):
    name: str
    samples: tuple[float, ...]

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("sample name must be trimmed and nonblank")
        return value

    @field_validator("samples")
    @classmethod
    def require_finite_samples(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if any(not math.isfinite(sample) for sample in value):
            raise ValueError("samples must be finite")
        return value

    @property
    def content_id(self) -> str:
        return content_id(self)


class CandidateSamples(NamedSamples):
    candidate_arm_id: ContentID
    measurement_artifact_id: ContentID
    metric_id: str

    @field_validator("metric_id")
    @classmethod
    def require_metric_id(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("candidate metric ID must be trimmed and nonblank")
        return value


class ProtectedDimension(NamedSamples):
    floor: float
    measurement_artifact_id: ContentID

    @field_validator("floor")
    @classmethod
    def require_finite_floor(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("protected floor must be finite")
        return value


class ProtectedRequirement(FrozenModel):
    name: str
    floor: float

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("protected requirement name must be trimmed and nonblank")
        return value

    @field_validator("floor")
    @classmethod
    def require_floor(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("protected requirement floor must be finite")
        return value


class ProtectedContract(FrozenModel):
    requirements: tuple[ProtectedRequirement, ...] = ()

    @field_validator("requirements")
    @classmethod
    def normalize_requirements(
        cls, value: tuple[ProtectedRequirement, ...]
    ) -> tuple[ProtectedRequirement, ...]:
        names = [requirement.name for requirement in value]
        if len(names) != len(set(names)):
            raise ValueError("protected requirement names must be unique")
        return tuple(sorted(value, key=lambda requirement: requirement.name))

    @property
    def content_id(self) -> str:
        return content_id(self)


class ControlSamples(NamedSamples):
    control_arm_id: ContentID
    candidate_arm: ComparisonArm
    control_arm: ComparisonArm
    declared_adjustments: tuple[DeclaredAdjustment, ...] = ()
    comparison: ResourceComparison

    @model_validator(mode="after")
    def bind_samples_to_comparison(self) -> Self:
        expected = compare_arms(
            self.candidate_arm,
            self.control_arm,
            declared_adjustments=self.declared_adjustments,
        )
        if self.control_arm_id != self.control_arm.content_id:
            raise ValueError("control samples must bind to their compared control arm")
        if self.comparison != expected:
            raise ValueError("control comparison must be recomputed from its frozen arms")
        return self


class ControlContract(FrozenModel):
    required_control_ids: tuple[ContentID, ...]

    @field_validator("required_control_ids")
    @classmethod
    def normalize_required_controls(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("control contract requires unique control IDs")
        return tuple(sorted(value))

    @property
    def content_id(self) -> str:
        return content_id(self)


class BootstrapSummary(FrozenModel):
    name: str
    sample_count: int
    bootstrap_iterations: int
    observed_mean: float
    lower_confidence_bound: float
    upper_confidence_bound: float
    sorted_bootstrap_effects: tuple[float, ...]

    @model_validator(mode="after")
    def require_consistent_distribution(self) -> Self:
        if self.sample_count <= 0 or self.bootstrap_iterations <= 0:
            raise ValueError("bootstrap summary counts must be positive")
        if len(self.sorted_bootstrap_effects) != self.bootstrap_iterations:
            raise ValueError("bootstrap summary must retain every generated effect")
        if self.sorted_bootstrap_effects != tuple(sorted(self.sorted_bootstrap_effects)):
            raise ValueError("bootstrap effects must be sorted")
        values = (
            self.observed_mean,
            self.lower_confidence_bound,
            self.upper_confidence_bound,
            *self.sorted_bootstrap_effects,
        )
        if any(not math.isfinite(value) for value in values):
            raise ValueError("bootstrap summary values must be finite")
        return self


class ImprovementDecision(FrozenModel):
    status: DecisionStatus
    seed: int
    alpha: float
    delta: float
    control_contract_id: ContentID
    protected_contract_id: ContentID
    candidate_samples_id: ContentID
    comparison_ids: tuple[str, ...]
    proposed_summary: BootstrapSummary | None = None
    control_summaries: tuple[BootstrapSummary, ...] = ()
    protected_summaries: tuple[BootstrapSummary, ...] = ()
    margin_summary: BootstrapSummary | None = None
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_status_evidence(self) -> Self:
        summaries_present = self.proposed_summary is not None and self.margin_summary is not None
        if self.status is DecisionStatus.PROVISIONAL and (
            not summaries_present or self.reasons
        ):
            raise ValueError("provisional decision requires summaries and no failure reasons")
        if self.status is DecisionStatus.REJECTED and (
            not summaries_present or not self.reasons
        ):
            raise ValueError("rejected decision requires summaries and failure reasons")
        if self.status is DecisionStatus.UNDETERMINED and not self.reasons:
            raise ValueError("undetermined decision requires reasons")
        return self

    @property
    def content_id(self) -> str:
        return content_id(self)


def _quantile(sorted_values: tuple[float, ...], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _bootstrap_means(
    samples: tuple[float, ...], *, generator: random.Random, iterations: int
) -> tuple[float, ...]:
    return tuple(
        fmean(samples[generator.randrange(len(samples))] for _ in samples)
        for _ in range(iterations)
    )


def _summary(
    name: str,
    samples: tuple[float, ...],
    effects: tuple[float, ...],
    *,
    alpha: float,
) -> BootstrapSummary:
    ordered = tuple(sorted(effects))
    return BootstrapSummary(
        name=name,
        sample_count=len(samples),
        bootstrap_iterations=len(effects),
        observed_mean=fmean(samples),
        lower_confidence_bound=_quantile(ordered, alpha),
        upper_confidence_bound=_quantile(ordered, 1.0 - alpha),
        sorted_bootstrap_effects=ordered,
    )


def decide_improvement(
    *,
    candidate_samples: CandidateSamples,
    controls: tuple[ControlSamples, ...],
    control_contract: ControlContract,
    protected_dimensions: tuple[ProtectedDimension, ...],
    protected_contract: ProtectedContract,
    delta: float,
    alpha: float,
    seed: int,
    bootstrap_iterations: int,
) -> ImprovementDecision:
    if not 0 < alpha < 0.5 or not math.isfinite(delta) or delta < 0:
        raise ValueError("decision requires 0 < alpha < 0.5 and finite nonnegative delta")
    if bootstrap_iterations < 100:
        raise ValueError("decision requires at least 100 bootstrap iterations")
    if len({control.name for control in controls}) != len(controls):
        raise ValueError("control names must be unique")
    if len({control.control_arm_id for control in controls}) != len(controls):
        raise ValueError("control arm IDs must be unique")
    if len({item.name for item in protected_dimensions}) != len(protected_dimensions):
        raise ValueError("protected dimension names must be unique")

    supplied_ids = {control.control_arm_id for control in controls}
    required_ids = set(control_contract.required_control_ids)
    if supplied_ids != required_ids:
        missing = tuple(sorted(required_ids - supplied_ids))
        unexpected = tuple(sorted(supplied_ids - required_ids))
        return ImprovementDecision(
            status=DecisionStatus.UNDETERMINED,
            seed=seed,
            alpha=alpha,
            delta=delta,
            control_contract_id=control_contract.content_id,
            protected_contract_id=protected_contract.content_id,
            candidate_samples_id=candidate_samples.content_id,
            comparison_ids=(),
            reasons=(
                *(f"missing-control:{control_id}" for control_id in missing),
                *(f"unexpected-control:{control_id}" for control_id in unexpected),
            ),
        )
    invalid_comparisons = tuple(
        control
        for control in controls
        if control.comparison.status is not ComparisonStatus.VALID
    )
    comparison_ids = tuple(
        control.comparison.content_id for control in sorted(controls, key=lambda item: item.name)
    )
    candidate_ids = {control.comparison.candidate_id for control in controls}
    if len(candidate_ids) != 1:
        return ImprovementDecision(
            status=DecisionStatus.UNDETERMINED,
            seed=seed,
            alpha=alpha,
            delta=delta,
            control_contract_id=control_contract.content_id,
            protected_contract_id=protected_contract.content_id,
            candidate_samples_id=candidate_samples.content_id,
            comparison_ids=comparison_ids,
            reasons=("inconsistent-candidate-arms",),
        )
    if candidate_samples.candidate_arm_id not in candidate_ids:
        return ImprovementDecision(
            status=DecisionStatus.UNDETERMINED,
            seed=seed,
            alpha=alpha,
            delta=delta,
            control_contract_id=control_contract.content_id,
            protected_contract_id=protected_contract.content_id,
            candidate_samples_id=candidate_samples.content_id,
            comparison_ids=comparison_ids,
            reasons=("candidate-samples-arm-mismatch",),
        )
    supplied_protected = {item.name: item.floor for item in protected_dimensions}
    required_protected = {
        requirement.name: requirement.floor
        for requirement in protected_contract.requirements
    }
    if supplied_protected != required_protected:
        missing = tuple(sorted(set(required_protected) - set(supplied_protected)))
        unexpected = tuple(sorted(set(supplied_protected) - set(required_protected)))
        floor_mismatch = tuple(
            sorted(
                name
                for name in set(required_protected) & set(supplied_protected)
                if supplied_protected[name] != required_protected[name]
            )
        )
        return ImprovementDecision(
            status=DecisionStatus.UNDETERMINED,
            seed=seed,
            alpha=alpha,
            delta=delta,
            control_contract_id=control_contract.content_id,
            protected_contract_id=protected_contract.content_id,
            candidate_samples_id=candidate_samples.content_id,
            comparison_ids=comparison_ids,
            reasons=(
                *(f"missing-protected:{name}" for name in missing),
                *(f"unexpected-protected:{name}" for name in unexpected),
                *(f"protected-floor-mismatch:{name}" for name in floor_mismatch),
            ),
        )
    if invalid_comparisons:
        return ImprovementDecision(
            status=DecisionStatus.UNDETERMINED,
            seed=seed,
            alpha=alpha,
            delta=delta,
            control_contract_id=control_contract.content_id,
            protected_contract_id=protected_contract.content_id,
            candidate_samples_id=candidate_samples.content_id,
            comparison_ids=comparison_ids,
            reasons=tuple(
                f"resource-comparison-{control.name}-{control.comparison.status.value}"
                for control in sorted(invalid_comparisons, key=lambda item: item.name)
            ),
        )
    if (
        not candidate_samples.samples
        or not controls
        or any(not control.samples for control in controls)
        or any(not item.samples for item in protected_dimensions)
    ):
        return ImprovementDecision(
            status=DecisionStatus.UNDETERMINED,
            seed=seed,
            alpha=alpha,
            delta=delta,
            control_contract_id=control_contract.content_id,
            protected_contract_id=protected_contract.content_id,
            candidate_samples_id=candidate_samples.content_id,
            comparison_ids=comparison_ids,
            reasons=("missing-measurements",),
        )

    generator = random.Random(seed)
    proposed_effects = _bootstrap_means(
        candidate_samples.samples, generator=generator, iterations=bootstrap_iterations
    )
    ordered_controls = tuple(sorted(controls, key=lambda control: control.name))
    control_effects = tuple(
        _bootstrap_means(
            control.samples, generator=generator, iterations=bootstrap_iterations
        )
        for control in ordered_controls
    )
    margin_effects = tuple(
        proposed_effects[index]
        - max(effects[index] for effects in control_effects)
        - delta
        for index in range(bootstrap_iterations)
    )
    proposed_summary = _summary(
        candidate_samples.name, candidate_samples.samples, proposed_effects, alpha=alpha
    )
    control_summaries = tuple(
        _summary(control.name, control.samples, effects, alpha=alpha)
        for control, effects in zip(ordered_controls, control_effects, strict=True)
    )
    margin_summary = _summary(
        "proposed-minus-maximum-control-minus-delta",
        margin_effects,
        margin_effects,
        alpha=alpha,
    )
    protected_summaries = tuple(
        _summary(
            item.name,
            item.samples,
            _bootstrap_means(
                item.samples, generator=generator, iterations=bootstrap_iterations
            ),
            alpha=alpha,
        )
        for item in sorted(protected_dimensions, key=lambda protected: protected.name)
    )
    reasons: list[str] = []
    if margin_summary.lower_confidence_bound <= 0:
        reasons.append("effect-not-beyond-maximum-control")
    floors = {item.name: item.floor for item in protected_dimensions}
    if any(
        summary.lower_confidence_bound < floors[summary.name]
        for summary in protected_summaries
    ):
        reasons.append("protected-dimension-regression")
    return ImprovementDecision(
        status=DecisionStatus.REJECTED if reasons else DecisionStatus.PROVISIONAL,
        seed=seed,
        alpha=alpha,
        delta=delta,
        control_contract_id=control_contract.content_id,
        protected_contract_id=protected_contract.content_id,
        candidate_samples_id=candidate_samples.content_id,
        comparison_ids=comparison_ids,
        proposed_summary=proposed_summary,
        control_summaries=control_summaries,
        protected_summaries=protected_summaries,
        margin_summary=margin_summary,
        reasons=tuple(reasons),
    )
