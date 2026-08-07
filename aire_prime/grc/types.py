from enum import StrEnum

from pydantic import Field, field_validator

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel


class SpaceKind(StrEnum):
    SCALAR = "scalar"
    VECTOR = "vector"
    TENSOR = "tensor"
    DISTRIBUTION = "distribution"
    GRAPH = "graph"
    MANIFOLD = "manifold"
    OPERATOR = "operator"
    PROCESS = "process"


class StructuralType(FrozenModel):
    kind: SpaceKind
    dimensions: tuple[int, ...] = ()
    field: str | None = None
    unit: str | None = None
    domain: str | None = None
    precision: str | None = None
    label: str | None = Field(default=None, exclude=True)

    @field_validator("dimensions")
    @classmethod
    def require_positive_dimensions(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(dimension <= 0 for dimension in value):
            raise ValueError("dimensions must be positive")
        return value

    def structural_signature(self) -> str:
        return content_id(self)
