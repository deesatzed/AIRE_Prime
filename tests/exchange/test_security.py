import pickle
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from aire_prime.exchange.realize import RealizationContext, Realizer
from aire_prime.exchange.receipt import (
    FailureCode,
    RealizationReceipt,
    ResourceUse,
)
from aire_prime.grc.constructor import ConstructorPlan, OperationSpec, ResourceBudget
from aire_prime.grc.types import SpaceKind, StructuralType

OBJECT_ID = "sha256:" + "b" * 64
DEFAULT_BUDGET = ResourceBudget(
    max_operations=10,
    max_elements=16,
    max_output_bytes=128,
    max_elapsed_seconds=1.0,
)


def plan(
    operation: OperationSpec,
    *,
    dependencies: tuple[str, ...] = ("x",),
    output_type: StructuralType | None = None,
) -> ConstructorPlan:
    return ConstructorPlan(
        object_id=OBJECT_ID,
        dependencies=dependencies,
        operations=(operation,),
        output_ref=operation.id,
        output_type=output_type or StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,)),
    )


def context(inputs: dict[str, Any], budget: ResourceBudget = DEFAULT_BUDGET) -> RealizationContext:
    return RealizationContext(
        receiver_id="receiver:security",
        local_realization_id="local:security",
        inputs=inputs,
        budget=budget,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source", "__import__('os')"),
        ("path", "../../etc/passwd"),
        ("url", "https://example.invalid/payload"),
        ("command", "touch /tmp/owned"),
        ("callable", lambda: None),
        ("pickle", pickle.dumps({"hostile": True})),
    ),
)
def test_operation_schema_rejects_executable_or_external_channels(
    field: str, value: str | bytes | Callable[[], None]
) -> None:
    payload: dict[str, Any] = {"id": "bad", "primitive": "identity", field: value}
    with pytest.raises(ValidationError, match="Extra inputs"):
        OperationSpec.model_validate(payload)


def test_non_finite_input_returns_invariant_failure() -> None:
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    outcome = Realizer().realize(plan(operation), context({"x": np.array([1.0, np.nan])}))
    assert outcome.receipt.failures[0].code is FailureCode.INVARIANT_VIOLATION


def test_oversized_lookup_stops_before_execution() -> None:
    operation = OperationSpec(
        id="output",
        primitive="lookup",
        inputs=("x",),
        lookup_table=tuple((float(index), float(index + 1)) for index in range(20)),
    )
    outcome = Realizer().realize(plan(operation), context({"x": 0}))
    assert outcome.receipt.failures[0].code is FailureCode.RESOURCE_INFEASIBLE
    assert outcome.receipt.resources.operation_count == 0


def test_recursive_operation_reference_returns_constructor_failure() -> None:
    operation = OperationSpec(id="loop", primitive="identity", inputs=("loop",))
    outcome = Realizer().realize(plan(operation), context({"x": np.array([1.0, 2.0])}))
    assert outcome.receipt.failures[0].code is FailureCode.CONSTRUCTOR_FAILURE


def test_undeclared_dependency_returns_missing_dependency() -> None:
    operation = OperationSpec(id="output", primitive="identity", inputs=("secret",))
    outcome = Realizer().realize(plan(operation), context({"secret": np.array([1.0, 2.0])}))
    assert outcome.receipt.failures[0].code is FailureCode.MISSING_DEPENDENCY


def test_output_outside_declared_structural_type_returns_type_mismatch() -> None:
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    output_type = StructuralType(kind=SpaceKind.VECTOR, dimensions=(3,))
    outcome = Realizer().realize(
        plan(operation, output_type=output_type),
        context({"x": np.array([1.0, 2.0])}),
    )
    assert outcome.receipt.failures[0].code is FailureCode.TYPE_MISMATCH


def test_affine_bias_cannot_broadcast_beyond_preflight_estimate() -> None:
    operation = OperationSpec(
        id="output",
        primitive="affine",
        inputs=("x",),
        matrix=((1.0, 1.0),),
        bias=tuple(float(value) for value in range(100)),
    )
    tiny_budget = ResourceBudget(
        max_operations=1,
        max_elements=2,
        max_output_bytes=16,
        max_elapsed_seconds=1.0,
    )
    outcome = Realizer().realize(
        plan(
            operation,
            output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(1,)),
        ),
        context({"x": np.array([1.0, 2.0])}, budget=tiny_budget),
    )
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.CONSTRUCTOR_FAILURE
    assert outcome.receipt.resources.operation_count == 0


def test_elapsed_budget_is_checked_after_operation() -> None:
    ticks = iter((0.0, 0.0, 2.0, 2.0))
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    outcome = Realizer(clock=lambda: next(ticks)).realize(
        plan(operation),
        context({"x": np.array([1.0, 2.0])}),
    )
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.RESOURCE_INFEASIBLE


def test_dependency_conversion_does_not_invoke_array_protocols() -> None:
    class HostileArray:
        calls = 0

        def __array__(self, dtype: object = None, copy: object = None) -> np.ndarray:
            self.calls += 1
            return np.array([1.0, 2.0])

    hostile = HostileArray()
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    outcome = Realizer().realize(plan(operation), context({"x": hostile}))
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.TYPE_MISMATCH
    assert hostile.calls == 0


def test_elapsed_budget_is_enforced_when_success_receipt_is_created() -> None:
    ticks = iter((0.0, 0.0, 0.5, 2.0, 2.0))
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    outcome = Realizer(clock=lambda: next(ticks)).realize(
        plan(operation),
        context({"x": np.array([1.0, 2.0])}),
    )
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.RESOURCE_INFEASIBLE
    assert outcome.receipt.resources.elapsed_seconds == 2.0


def test_huge_integer_returns_typed_failure_instead_of_raising() -> None:
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    outcome = Realizer().realize(plan(operation), context({"x": 10**10_000}))
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.TYPE_MISMATCH
    assert outcome.receipt.model_dump_json()


def test_oversized_dependency_is_rejected_before_copy_and_counted() -> None:
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    tiny_budget = ResourceBudget(
        max_operations=1,
        max_elements=2,
        max_output_bytes=128,
        max_elapsed_seconds=1.0,
    )
    source = np.arange(100, dtype=np.float64)
    outcome = Realizer().realize(plan(operation), context({"x": source}, budget=tiny_budget))
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.RESOURCE_INFEASIBLE
    assert outcome.receipt.resources.max_elements == 100
    assert outcome.receipt.resources.operation_count == 0


def test_affine_parameter_tensor_is_budgeted_and_counted() -> None:
    operation = OperationSpec(
        id="output",
        primitive="affine",
        inputs=("x",),
        matrix=tuple(tuple(1.0 for _ in range(4)) for _ in range(4)),
        bias=(0.0, 0.0, 0.0, 0.0),
    )
    budget = ResourceBudget(
        max_operations=1,
        max_elements=4,
        max_output_bytes=32,
        max_elapsed_seconds=1.0,
    )
    outcome = Realizer().realize(
        plan(
            operation,
            output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(4,)),
        ),
        context({"x": np.ones(4)}, budget=budget),
    )
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.RESOURCE_INFEASIBLE
    assert outcome.receipt.resources.max_elements == 16
    assert outcome.receipt.resources.operation_count == 0


def test_irrelevant_parameter_tensor_is_rejected_by_operation_schema() -> None:
    with pytest.raises(ValidationError, match="not valid for identity"):
        OperationSpec(
            id="output",
            primitive="identity",
            inputs=("x",),
            lookup_table=tuple((float(value),) for value in range(100)),
        )


@pytest.mark.parametrize("index", (-1, 1.9, 2))
def test_lookup_requires_in_range_exact_integer_index(index: float) -> None:
    operation = OperationSpec(
        id="output",
        primitive="lookup",
        inputs=("x",),
        lookup_table=((10.0,), (20.0,)),
    )
    output_type = StructuralType(kind=SpaceKind.VECTOR, dimensions=(1,))
    outcome = Realizer().realize(
        plan(operation, output_type=output_type),
        context({"x": index}),
    )
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.CONSTRUCTOR_FAILURE
    assert outcome.receipt.resources.operation_count == 0


def test_dependency_and_operation_namespaces_are_disjoint() -> None:
    operation = OperationSpec(id="x", primitive="constant", constant=(1.0, 2.0))
    outcome = Realizer().realize(plan(operation), context({"x": np.array([3.0, 4.0])}))
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.CONSTRUCTOR_FAILURE


def test_custom_mapping_is_rejected_without_invoking_it() -> None:
    class HostileMapping(dict[str, object]):
        calls = 0

        def __getitem__(self, key: str) -> object:
            self.calls += 1
            raise RuntimeError("must not execute")

    hostile = HostileMapping(x=np.array([1.0, 2.0]))
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    outcome = Realizer().realize(plan(operation), context(hostile))
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.PERMISSION_DENIED
    assert hostile.calls == 0


@pytest.mark.parametrize(
    "output_type",
    (
        StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,), precision="float32"),
        StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,), field="complex"),
        StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,), domain="human-label"),
        StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,), unit="volts"),
    ),
)
def test_output_must_satisfy_all_declared_structural_metadata(
    output_type: StructuralType,
) -> None:
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    outcome = Realizer().realize(
        plan(operation, output_type=output_type),
        context({"x": np.array([1.0, 2.0])}),
    )
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.TYPE_MISMATCH


def test_scalar_output_rejects_declared_dimensions() -> None:
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    output_type = StructuralType(kind=SpaceKind.SCALAR, dimensions=(2,))
    outcome = Realizer().realize(
        plan(operation, output_type=output_type),
        context({"x": 1.0}),
    )
    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.TYPE_MISMATCH


def test_resource_receipt_tracks_max_tensor_bytes() -> None:
    resource = ResourceUse(
        operation_count=0,
        max_elements=2,
        max_tensor_bytes=16,
        output_bytes=0,
        elapsed_seconds=0.0,
    )
    assert resource.max_tensor_bytes == 16


@pytest.mark.parametrize(
    "payload",
    (
        {
            "operation_count": -1,
            "max_elements": 0,
            "output_bytes": 0,
            "elapsed_seconds": 0.0,
        },
        {
            "operation_count": 0,
            "max_elements": -1,
            "output_bytes": 0,
            "elapsed_seconds": 0.0,
        },
        {
            "operation_count": 0,
            "max_elements": 0,
            "max_tensor_bytes": -1,
            "output_bytes": 0,
            "elapsed_seconds": 0.0,
        },
        {
            "operation_count": 0,
            "max_elements": 0,
            "output_bytes": -1,
            "elapsed_seconds": 0.0,
        },
        {
            "operation_count": 0,
            "max_elements": 0,
            "output_bytes": 0,
            "elapsed_seconds": float("nan"),
        },
    ),
)
def test_resource_receipt_rejects_impossible_measurements(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ResourceUse.model_validate(payload)


@pytest.mark.parametrize("field", ("receiver_id", "local_realization_id"))
def test_receipt_rejects_blank_attribution_ids(field: str) -> None:
    payload = {
        "object_id": OBJECT_ID,
        "receiver_id": "receiver:security",
        "local_realization_id": "local:security",
        "resources": {
            "operation_count": 0,
            "max_elements": 0,
            "output_bytes": 0,
            "elapsed_seconds": 0.0,
        },
    }
    payload[field] = "  "
    with pytest.raises(ValidationError, match="nonblank"):
        RealizationReceipt.model_validate(payload)


@pytest.mark.parametrize("field", ("receiver_id", "local_realization_id"))
def test_context_rejects_blank_attribution_ids(field: str) -> None:
    payload: dict[str, object] = {
        "receiver_id": "receiver:security",
        "local_realization_id": "local:security",
        "inputs": {},
        "budget": DEFAULT_BUDGET,
    }
    payload[field] = ""
    with pytest.raises(ValueError, match="nonblank"):
        RealizationContext(**payload)  # type: ignore[arg-type]


def test_dependency_references_must_be_nonblank() -> None:
    with pytest.raises(ValidationError, match="nonblank"):
        OperationSpec(id="output", primitive="identity", inputs=("",))


def test_explicit_default_valued_irrelevant_parameter_is_rejected() -> None:
    with pytest.raises(ValidationError, match="not valid for identity"):
        OperationSpec(
            id="output",
            primitive="identity",
            inputs=("x",),
            threshold=0.0,
        )
