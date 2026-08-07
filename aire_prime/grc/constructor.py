import json
import math
from collections.abc import Mapping
from typing import Any, Self

from pydantic import Field, field_validator, model_validator

from aire_prime.core.canonical import canonical_bytes
from aire_prime.core.model import FrozenModel
from aire_prime.grc.operations import Primitive
from aire_prime.grc.types import StructuralType
from aire_prime.objects import ContentID


class ResourceBudget(FrozenModel):
    max_operations: int = Field(ge=0)
    max_elements: int = Field(ge=0)
    max_output_bytes: int = Field(
        ge=0,
        description="Maximum bytes for any dependency, parameter, or output tensor.",
    )
    max_elapsed_seconds: float = Field(ge=0, allow_inf_nan=False)


class ConstructorWireModel(FrozenModel):
    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_unset=True)

    def to_wire_json(self) -> str:
        return canonical_bytes(self.to_wire()).decode("utf-8")

    @classmethod
    def from_wire(cls, data: Mapping[str, Any]) -> Self:
        if type(data) is not dict:
            raise TypeError("constructor wire payload must be an exact dictionary")
        return cls.model_validate(data)

    @classmethod
    def from_wire_json(cls, data: str) -> Self:
        payload = json.loads(data)
        if type(payload) is not dict:
            raise ValueError("constructor wire JSON must contain an object")
        return cls.from_wire(payload)


class OperationSpec(ConstructorWireModel):
    id: str
    primitive: str
    inputs: tuple[str, ...] = ()
    constant: tuple[float, ...] = ()
    indices: tuple[int, ...] = ()
    matrix: tuple[tuple[float, ...], ...] = ()
    bias: tuple[float, ...] = ()
    threshold: float = 0.0
    lookup_table: tuple[tuple[float, ...], ...] = ()

    @field_validator("id", "primitive")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("operation identifiers and primitive names must be nonblank")
        return value

    @field_validator("inputs")
    @classmethod
    def require_nonblank_input_references(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not reference.strip() for reference in value):
            raise ValueError("operation input references must be nonblank")
        return value

    @model_validator(mode="after")
    def require_finite_parameters(self) -> "OperationSpec":
        values = self.constant + self.bias + tuple(value for row in self.matrix for value in row)
        values += tuple(value for row in self.lookup_table for value in row)
        values += (self.threshold,)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("operation parameters must be finite")
        try:
            primitive = Primitive(self.primitive)
        except ValueError:
            # Unknown names remain representable so the realization boundary can
            # return a typed UnsupportedPrimitive receipt.
            return self

        parameter_fields = {
            "constant",
            "indices",
            "matrix",
            "bias",
            "threshold",
            "lookup_table",
        }
        allowed: dict[Primitive, frozenset[str]] = {
            Primitive.IDENTITY: frozenset(),
            Primitive.CONSTANT: frozenset({"constant"}),
            Primitive.SELECT: frozenset({"indices"}),
            Primitive.AFFINE: frozenset({"matrix", "bias"}),
            Primitive.CONCAT: frozenset(),
            Primitive.NORMALIZE: frozenset(),
            Primitive.THRESHOLD: frozenset({"threshold"}),
            Primitive.LOOKUP: frozenset({"lookup_table"}),
        }
        invalid = sorted(
            name
            for name in self.model_fields_set & parameter_fields
            if name not in allowed[primitive]
        )
        if invalid:
            raise ValueError(
                f"parameters {', '.join(invalid)} are not valid for {primitive.value}"
            )

        input_count = len(self.inputs)
        if primitive is Primitive.CONSTANT:
            if input_count:
                raise ValueError("constant does not accept inputs")
            if not self.constant:
                raise ValueError("constant requires nonempty values")
        elif primitive is Primitive.CONCAT:
            if input_count == 0:
                raise ValueError("concat requires at least one input")
        elif input_count != 1:
            raise ValueError(f"{primitive.value} requires exactly one input")

        required_parameter = {
            Primitive.SELECT: (self.indices, "select requires nonempty indices"),
            Primitive.AFFINE: (self.matrix, "affine requires a nonempty matrix"),
            Primitive.LOOKUP: (self.lookup_table, "lookup requires a nonempty table"),
        }.get(primitive)
        if required_parameter is not None and not required_parameter[0]:
            raise ValueError(required_parameter[1])
        return self


class ConstructorPlan(ConstructorWireModel):
    object_id: ContentID
    dependencies: tuple[str, ...] = ()
    operations: tuple[OperationSpec, ...]
    output_ref: str
    output_type: StructuralType

    @field_validator("dependencies")
    @classmethod
    def require_nonblank_dependencies(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not dependency.strip() for dependency in value):
            raise ValueError("constructor dependency IDs must be nonblank")
        return value

    @field_validator("output_ref")
    @classmethod
    def require_nonblank_output_ref(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("constructor output_ref must be nonblank")
        return value
