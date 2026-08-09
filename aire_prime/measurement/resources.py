import math
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from aire_prime.core.model import FrozenModel


class MeasurementState(StrEnum):
    OBSERVED = "observed"
    UNDETERMINED = "undetermined"


class ResourceMeasurement(FrozenModel):
    state: MeasurementState
    value: float | None = None

    @model_validator(mode="after")
    def require_consistent_state(self) -> Self:
        if self.state is MeasurementState.UNDETERMINED:
            if self.value is not None:
                raise ValueError("undetermined measurement cannot contain a value")
            return self
        if self.value is None:
            raise ValueError("observed measurement requires a value")
        if not math.isfinite(self.value) or self.value < 0:
            raise ValueError("observed resource measurement must be finite and nonnegative")
        return self

    @classmethod
    def observed(cls, value: float) -> "ResourceMeasurement":
        return cls(state=MeasurementState.OBSERVED, value=value)

    @classmethod
    def undetermined(cls) -> "ResourceMeasurement":
        return cls(state=MeasurementState.UNDETERMINED)


RESOURCE_DIMENSIONS = (
    "packet_bytes",
    "peak_resident_bytes",
    "operation_count",
    "interaction_count",
    "elapsed_time",
    "external_calls",
    "declared_energy_proxy",
    "declared_bandwidth",
)


class ResourceVector(FrozenModel):
    packet_bytes: ResourceMeasurement = Field(default_factory=ResourceMeasurement.undetermined)
    peak_resident_bytes: ResourceMeasurement = Field(
        default_factory=ResourceMeasurement.undetermined
    )
    operation_count: ResourceMeasurement = Field(
        default_factory=ResourceMeasurement.undetermined
    )
    interaction_count: ResourceMeasurement = Field(
        default_factory=ResourceMeasurement.undetermined
    )
    elapsed_time: ResourceMeasurement = Field(default_factory=ResourceMeasurement.undetermined)
    external_calls: ResourceMeasurement = Field(default_factory=ResourceMeasurement.undetermined)
    declared_energy_proxy: ResourceMeasurement = Field(
        default_factory=ResourceMeasurement.undetermined
    )
    declared_bandwidth: ResourceMeasurement = Field(
        default_factory=ResourceMeasurement.undetermined
    )

    @model_validator(mode="after")
    def require_integral_discrete_resources(self) -> Self:
        for name in (
            "packet_bytes",
            "peak_resident_bytes",
            "operation_count",
            "interaction_count",
            "external_calls",
        ):
            measurement = getattr(self, name)
            if measurement.value is not None and not measurement.value.is_integer():
                raise ValueError(f"{name} must be an integral count")
        return self

    def measurements(self) -> tuple[tuple[str, ResourceMeasurement], ...]:
        return tuple((name, getattr(self, name)) for name in RESOURCE_DIMENSIONS)
