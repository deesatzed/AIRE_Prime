from pathlib import Path

import numpy as np
import pytest

from aire_prime.exchange.realize import RealizationContext, Realizer
from aire_prime.exchange.receipt import FailureCode
from aire_prime.grc.constructor import ConstructorPlan, OperationSpec, ResourceBudget
from aire_prime.grc.types import SpaceKind, StructuralType

OBJECT_ID = "sha256:" + "a" * 64


def capability_plan(*, primitive: str = "concat") -> ConstructorPlan:
    return ConstructorPlan(
        object_id=OBJECT_ID,
        dependencies=("x",),
        operations=(
            OperationSpec(id="selected", primitive="select", inputs=("x",), indices=(0, 2)),
            OperationSpec(
                id="affine",
                primitive="affine",
                inputs=("selected",),
                matrix=((2.0, 0.0), (0.0, 2.0)),
                bias=(1.0, 1.0),
            ),
            OperationSpec(
                id="output",
                primitive=primitive,
                inputs=("affine", "selected"),
            ),
        ),
        output_ref="output",
        output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(4,)),
    )


def context(*, budget: ResourceBudget | None = None) -> RealizationContext:
    return RealizationContext(
        receiver_id="receiver:1",
        local_realization_id="local:1",
        inputs={"x": np.array([1.0, 2.0, 3.0])},
        budget=budget or ResourceBudget(
            max_operations=10,
            max_elements=100,
            max_output_bytes=1_000,
            max_elapsed_seconds=1.0,
        ),
        contract_tests=("shape", "finite"),
    )


def test_select_affine_concat_realizes_expected_array_and_receipt() -> None:
    outcome = Realizer().realize(capability_plan(), context())

    assert outcome.output is not None
    np.testing.assert_allclose(outcome.output, np.array([3.0, 7.0, 1.0, 3.0]))
    assert outcome.receipt.success
    assert outcome.receipt.resources.operation_count == 3
    assert outcome.receipt.resources.max_elements == 4
    assert outcome.receipt.resources.output_bytes == 32
    assert outcome.receipt.contract_tests == ("shape", "finite")
    assert outcome.receipt.failures == ()


def test_unknown_operation_returns_typed_failure_without_execution(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    hostile = f"__import__('pathlib').Path('{marker}').touch()"

    outcome = Realizer().realize(capability_plan(primitive=hostile), context())

    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.UNSUPPORTED_PRIMITIVE
    assert not marker.exists()
    assert outcome.receipt.model_dump_json()


@pytest.mark.parametrize(
    "budget",
    (
        ResourceBudget(
            max_operations=2,
            max_elements=100,
            max_output_bytes=1_000,
            max_elapsed_seconds=1.0,
        ),
        ResourceBudget(
            max_operations=10,
            max_elements=3,
            max_output_bytes=1_000,
            max_elapsed_seconds=1.0,
        ),
        ResourceBudget(
            max_operations=10,
            max_elements=100,
            max_output_bytes=31,
            max_elapsed_seconds=1.0,
        ),
        ResourceBudget(
            max_operations=10,
            max_elements=100,
            max_output_bytes=1_000,
            max_elapsed_seconds=0.0,
        ),
    ),
)
def test_resource_limit_stops_with_typed_failure(budget: ResourceBudget) -> None:
    outcome = Realizer().realize(capability_plan(), context(budget=budget))

    assert outcome.output is None
    assert outcome.receipt.failures[0].code is FailureCode.RESOURCE_INFEASIBLE
    assert outcome.receipt.model_dump_json()


@pytest.mark.parametrize(
    ("operation", "inputs", "expected"),
    (
        (
            OperationSpec(id="output", primitive="identity", inputs=("x",)),
            {"x": np.array([2.0, 4.0])},
            np.array([2.0, 4.0]),
        ),
        (
            OperationSpec(id="output", primitive="constant", constant=(2.0, 4.0)),
            {},
            np.array([2.0, 4.0]),
        ),
        (
            OperationSpec(id="output", primitive="normalize", inputs=("x",)),
            {"x": np.array([3.0, 4.0])},
            np.array([0.6, 0.8]),
        ),
        (
            OperationSpec(id="output", primitive="threshold", inputs=("x",), threshold=2.0),
            {"x": np.array([1.0, 3.0])},
            np.array([0.0, 1.0]),
        ),
        (
            OperationSpec(
                id="output",
                primitive="lookup",
                inputs=("x",),
                lookup_table=((2.0, 4.0), (6.0, 8.0)),
            ),
            {"x": 1},
            np.array([6.0, 8.0]),
        ),
    ),
)
def test_allow_list_primitive_semantics(
    operation: OperationSpec, inputs: dict[str, object], expected: np.ndarray
) -> None:
    dependencies = tuple(inputs)
    operation_plan = ConstructorPlan(
        object_id=OBJECT_ID,
        dependencies=dependencies,
        operations=(operation,),
        output_ref="output",
        output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,)),
    )
    outcome = Realizer().realize(operation_plan, context_for_inputs(inputs))
    assert outcome.receipt.success
    assert outcome.output is not None
    np.testing.assert_allclose(outcome.output, expected)


def context_for_inputs(inputs: dict[str, object]) -> RealizationContext:
    return RealizationContext(
        receiver_id="receiver:primitives",
        local_realization_id="local:primitives",
        inputs=inputs,
        budget=ResourceBudget(
            max_operations=5,
            max_elements=100,
            max_output_bytes=1_000,
            max_elapsed_seconds=1.0,
        ),
    )


def test_normalize_is_stable_for_large_finite_values() -> None:
    operation = OperationSpec(id="output", primitive="normalize", inputs=("x",))
    operation_plan = ConstructorPlan(
        object_id=OBJECT_ID,
        dependencies=("x",),
        operations=(operation,),
        output_ref="output",
        output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,)),
    )
    outcome = Realizer().realize(
        operation_plan,
        context_for_inputs({"x": np.array([1e308, 1e308])}),
    )
    assert outcome.receipt.success
    assert outcome.output is not None
    np.testing.assert_allclose(outcome.output, np.array([2**-0.5, 2**-0.5]))


def test_identity_output_does_not_alias_dependency_input() -> None:
    source = np.array([2.0, 4.0])
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))
    operation_plan = ConstructorPlan(
        object_id=OBJECT_ID,
        dependencies=("x",),
        operations=(operation,),
        output_ref="output",
        output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,)),
    )
    outcome = Realizer().realize(operation_plan, context_for_inputs({"x": source}))
    assert outcome.output is not None
    outcome.output[0] = 99.0
    np.testing.assert_allclose(source, np.array([2.0, 4.0]))


def test_operation_wire_round_trip_preserves_supplied_fields_only() -> None:
    operation = OperationSpec(id="output", primitive="identity", inputs=("x",))

    wire = operation.to_wire()

    assert set(wire) == {"id", "primitive", "inputs"}
    assert OperationSpec.from_wire(wire) == operation


def test_complete_constructor_plan_has_canonical_json_round_trip() -> None:
    plan = ConstructorPlan(
        object_id=OBJECT_ID,
        dependencies=("x",),
        operations=(OperationSpec(id="output", primitive="identity", inputs=("x",)),),
        output_ref="output",
        output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(2,)),
    )

    wire_json = plan.to_wire_json()
    restored = ConstructorPlan.from_wire_json(wire_json)

    assert restored == plan
    assert restored.to_wire_json() == wire_json
