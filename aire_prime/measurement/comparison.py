import math
from enum import StrEnum
from typing import Self

from pydantic import field_validator, model_validator

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.measurement.resources import (
    RESOURCE_DIMENSIONS,
    MeasurementState,
    ResourceVector,
)
from aire_prime.objects import ContentID

COMPARISON_DIMENSIONS = RESOURCE_DIMENSIONS + ("observation_access", "receiver_prior_id")


class ComparisonStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    UNDETERMINED = "undetermined"


class ComparisonArm(FrozenModel):
    arm_id: str
    resources: ResourceVector
    observation_access: tuple[str, ...]
    receiver_prior_id: str

    @field_validator("arm_id", "receiver_prior_id")
    @classmethod
    def require_nonblank_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("comparison identifiers must be nonblank")
        return value

    @field_validator("observation_access")
    @classmethod
    def normalize_observation_access(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value) or len(value) != len(set(value)):
            raise ValueError("observation access must contain unique nonblank identifiers")
        return tuple(sorted(value))

    @property
    def content_id(self) -> str:
        return content_id(self)


class DeclaredAdjustment(FrozenModel):
    dimension: str
    method: str
    rationale: str
    maximum_absolute_difference: float

    @field_validator("dimension")
    @classmethod
    def require_resource_dimension(cls, value: str) -> str:
        if value not in RESOURCE_DIMENSIONS:
            raise ValueError("adjustments are limited to known resource dimensions")
        return value

    @field_validator("method", "rationale")
    @classmethod
    def require_narrative(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("adjustment method and rationale must be trimmed and nonblank")
        return value

    @field_validator("maximum_absolute_difference")
    @classmethod
    def require_finite_bound(cls, value: float) -> float:
        if not math.isfinite(value) or value < 0:
            raise ValueError("adjustment bound must be finite and nonnegative")
        return value

    @property
    def content_id(self) -> str:
        return content_id(self)


class ResourceComparison(FrozenModel):
    candidate_id: ContentID
    control_id: ContentID
    status: ComparisonStatus
    matched_dimensions: tuple[str, ...] = ()
    adjusted_dimensions: tuple[str, ...] = ()
    mismatched_dimensions: tuple[str, ...] = ()
    undetermined_dimensions: tuple[str, ...] = ()
    adjustment_ids: tuple[ContentID, ...] = ()

    @model_validator(mode="after")
    def require_consistent_partition_and_status(self) -> Self:
        buckets = (
            self.matched_dimensions,
            self.adjusted_dimensions,
            self.mismatched_dimensions,
            self.undetermined_dimensions,
        )
        flattened = tuple(dimension for bucket in buckets for dimension in bucket)
        if any(tuple(sorted(bucket)) != bucket for bucket in buckets):
            raise ValueError("comparison dimension buckets must be sorted")
        if len(flattened) != len(set(flattened)) or set(flattened) != set(
            COMPARISON_DIMENSIONS
        ):
            raise ValueError("comparison dimensions must form a disjoint exhaustive partition")
        expected = (
            ComparisonStatus.INVALID
            if self.mismatched_dimensions
            else ComparisonStatus.UNDETERMINED
            if self.undetermined_dimensions
            else ComparisonStatus.VALID
        )
        if self.status is not expected:
            raise ValueError("comparison status does not match its dimension evidence")
        if len(self.adjustment_ids) != len(self.adjusted_dimensions):
            raise ValueError("every adjusted dimension requires one adjustment commitment")
        return self

    @property
    def content_id(self) -> str:
        return content_id(self)


def compare_arms(
    candidate: ComparisonArm,
    control: ComparisonArm,
    *,
    declared_adjustments: tuple[DeclaredAdjustment, ...] = (),
) -> ResourceComparison:
    adjustment_dimensions = [adjustment.dimension for adjustment in declared_adjustments]
    if len(adjustment_dimensions) != len(set(adjustment_dimensions)):
        raise ValueError("declared adjustments must have unique dimensions")
    adjustments = {adjustment.dimension: adjustment for adjustment in declared_adjustments}
    matched: list[str] = []
    adjusted: list[str] = []
    mismatched: list[str] = []
    undetermined: list[str] = []

    control_resources = dict(control.resources.measurements())
    for name, candidate_measurement in candidate.resources.measurements():
        control_measurement = control_resources[name]
        if (
            candidate_measurement.state is MeasurementState.UNDETERMINED
            or control_measurement.state is MeasurementState.UNDETERMINED
        ):
            undetermined.append(name)
        elif candidate_measurement.value == control_measurement.value:
            matched.append(name)
        elif (
            name in adjustments
            and candidate_measurement.value is not None
            and control_measurement.value is not None
        ):
            difference = abs(candidate_measurement.value - control_measurement.value)
            if difference <= adjustments[name].maximum_absolute_difference:
                adjusted.append(name)
            else:
                mismatched.append(name)
        else:
            mismatched.append(name)

    for name, candidate_value, control_value in (
        ("observation_access", candidate.observation_access, control.observation_access),
        ("receiver_prior_id", candidate.receiver_prior_id, control.receiver_prior_id),
    ):
        if candidate_value == control_value:
            matched.append(name)
        else:
            mismatched.append(name)

    status = (
        ComparisonStatus.INVALID
        if mismatched
        else ComparisonStatus.UNDETERMINED
        if undetermined
        else ComparisonStatus.VALID
    )
    return ResourceComparison(
        candidate_id=candidate.content_id,
        control_id=control.content_id,
        status=status,
        matched_dimensions=tuple(sorted(matched)),
        adjusted_dimensions=tuple(sorted(adjusted)),
        mismatched_dimensions=tuple(sorted(mismatched)),
        undetermined_dimensions=tuple(sorted(undetermined)),
        adjustment_ids=tuple(
            adjustments[name].content_id for name in sorted(adjusted)
        ),
    )
