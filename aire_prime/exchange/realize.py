import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import monotonic

import numpy as np
from numpy.typing import NDArray

from aire_prime.exchange.receipt import (
    FailureCode,
    RealizationFailure,
    RealizationReceipt,
    ResourceUse,
)
from aire_prime.grc.constructor import ConstructorPlan, OperationSpec, ResourceBudget
from aire_prime.grc.operations import Primitive, execute_primitive
from aire_prime.grc.types import SpaceKind, StructuralType


@dataclass(frozen=True)
class RealizationContext:
    receiver_id: str
    local_realization_id: str
    inputs: Mapping[str, object]
    budget: ResourceBudget
    contract_tests: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.receiver_id.strip() or not self.local_realization_id.strip():
            raise ValueError("realization context attribution IDs must be nonblank")


@dataclass(frozen=True)
class RealizationOutcome:
    output: NDArray[np.float64] | None
    receipt: RealizationReceipt


class Realizer:
    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock

    def realize(self, plan: ConstructorPlan, context: RealizationContext) -> RealizationOutcome:
        start = self._clock()
        outputs: dict[str, NDArray[np.float64]] = {}
        operation_count = 0
        max_elements = 0
        max_tensor_bytes = 0

        def finish(
            output: NDArray[np.float64] | None,
            failure: RealizationFailure | None = None,
        ) -> RealizationOutcome:
            elapsed = max(0.0, self._clock() - start)
            output_bytes = 0 if output is None else int(output.nbytes)
            if failure is None and self._elapsed_exceeded(
                elapsed, context.budget.max_elapsed_seconds
            ):
                failure = RealizationFailure(
                    code=FailureCode.RESOURCE_INFEASIBLE,
                    message="elapsed-time budget exceeded before receipt creation",
                )
            receipt = RealizationReceipt(
                object_id=plan.object_id,
                receiver_id=context.receiver_id,
                local_realization_id=context.local_realization_id,
                contract_tests=context.contract_tests,
                resources=ResourceUse(
                    operation_count=operation_count,
                    max_elements=max_elements,
                    max_tensor_bytes=max_tensor_bytes,
                    output_bytes=output_bytes,
                    elapsed_seconds=elapsed,
                ),
                failures=() if failure is None else (failure,),
            )
            return RealizationOutcome(output=output if failure is None else None, receipt=receipt)

        def fail(
            code: FailureCode,
            message: str,
            counterexample: str | None = None,
        ) -> RealizationOutcome:
            return finish(
                None,
                RealizationFailure(code=code, message=message, counterexample=counterexample),
            )

        if len(plan.operations) > context.budget.max_operations:
            return fail(FailureCode.RESOURCE_INFEASIBLE, "operation budget exceeded")

        primitives: dict[str, Primitive] = {}
        for operation in plan.operations:
            try:
                primitives[operation.id] = Primitive(operation.primitive)
            except ValueError:
                return fail(
                    FailureCode.UNSUPPORTED_PRIMITIVE,
                    "operation is not in the allow-list",
                    operation.primitive,
                )

        operation_ids = [operation.id for operation in plan.operations]
        if len(operation_ids) != len(set(operation_ids)):
            return fail(FailureCode.CONSTRUCTOR_FAILURE, "operation IDs must be unique")
        if len(plan.dependencies) != len(set(plan.dependencies)):
            return fail(FailureCode.CONSTRUCTOR_FAILURE, "dependency IDs must be unique")
        if set(plan.dependencies) & set(operation_ids):
            return fail(
                FailureCode.CONSTRUCTOR_FAILURE,
                "dependency and operation ID namespaces must be disjoint",
            )

        available = set(plan.dependencies)
        future = set(operation_ids)
        for operation in plan.operations:
            future.remove(operation.id)
            for input_ref in operation.inputs:
                if input_ref == operation.id or input_ref in future:
                    return fail(
                        FailureCode.CONSTRUCTOR_FAILURE,
                        "recursive or forward operation reference",
                        input_ref,
                    )
                if input_ref not in available:
                    return fail(
                        FailureCode.MISSING_DEPENDENCY,
                        "operation uses an undeclared dependency",
                        input_ref,
                    )
            available.add(operation.id)

        if plan.output_ref not in set(operation_ids):
            return fail(FailureCode.CONSTRUCTOR_FAILURE, "output_ref is not an operation ID")

        if type(context.inputs) is not dict:
            return fail(
                FailureCode.PERMISSION_DENIED,
                "dependency inputs must use an exact built-in dictionary",
            )

        missing = set(plan.dependencies) - set(context.inputs)
        if missing:
            return fail(
                FailureCode.MISSING_DEPENDENCY,
                "declared dependency is unavailable",
                ",".join(sorted(missing)),
            )

        for dependency in plan.dependencies:
            raw_value = context.inputs[dependency]
            dependency_elements = int(raw_value.size) if type(raw_value) is np.ndarray else 1
            dependency_bytes = dependency_elements * np.dtype(np.float64).itemsize
            max_elements = max(max_elements, dependency_elements)
            max_tensor_bytes = max(max_tensor_bytes, dependency_bytes)
            if dependency_elements > context.budget.max_elements:
                return fail(
                    FailureCode.RESOURCE_INFEASIBLE,
                    "dependency exceeds the tensor element budget",
                    dependency,
                )
            if dependency_bytes > context.budget.max_output_bytes:
                return fail(
                    FailureCode.RESOURCE_INFEASIBLE,
                    "dependency exceeds the tensor byte budget",
                    dependency,
                )
            try:
                value = self._safe_dependency(raw_value)
            except (OverflowError, TypeError, ValueError):
                return fail(
                    FailureCode.TYPE_MISMATCH,
                    "dependency is not a numeric scalar or array",
                    dependency,
                )
            if not np.all(np.isfinite(value)):
                return fail(
                    FailureCode.INVARIANT_VIOLATION,
                    "dependency contains non-finite values",
                    dependency,
                )
            outputs[dependency] = value

        for operation in plan.operations:
            elapsed = self._clock() - start
            if self._elapsed_exceeded(elapsed, context.budget.max_elapsed_seconds):
                return fail(FailureCode.RESOURCE_INFEASIBLE, "elapsed-time budget exceeded")

            input_values = tuple(outputs[input_ref] for input_ref in operation.inputs)
            try:
                estimate = self._estimate_elements(operation, input_values)
            except ValueError as error:
                return fail(FailureCode.CONSTRUCTOR_FAILURE, str(error), operation.id)

            parameter_elements = self._parameter_elements(operation)
            parameter_bytes = parameter_elements * np.dtype(np.float64).itemsize
            max_elements = max(max_elements, parameter_elements)
            max_tensor_bytes = max(max_tensor_bytes, parameter_bytes)
            if parameter_elements > context.budget.max_elements:
                return fail(
                    FailureCode.RESOURCE_INFEASIBLE,
                    "operation parameter tensor exceeds the element budget",
                    operation.id,
                )
            if parameter_bytes > context.budget.max_output_bytes:
                return fail(
                    FailureCode.RESOURCE_INFEASIBLE,
                    "operation parameter tensor exceeds the byte budget",
                    operation.id,
                )
            if estimate > context.budget.max_elements:
                return fail(
                    FailureCode.RESOURCE_INFEASIBLE,
                    "tensor element budget exceeded",
                    operation.id,
                )
            if estimate * np.dtype(np.float64).itemsize > context.budget.max_output_bytes:
                return fail(
                    FailureCode.RESOURCE_INFEASIBLE,
                    "output-byte budget exceeded",
                    operation.id,
                )

            try:
                result = execute_primitive(
                    primitives[operation.id],
                    input_values,
                    constant=operation.constant,
                    indices=operation.indices,
                    matrix=operation.matrix,
                    bias=operation.bias,
                    threshold=operation.threshold,
                    lookup_table=operation.lookup_table,
                )
            except (IndexError, TypeError, ValueError) as error:
                return fail(FailureCode.CONSTRUCTOR_FAILURE, str(error), operation.id)

            operation_count += 1
            elapsed = self._clock() - start
            if self._elapsed_exceeded(elapsed, context.budget.max_elapsed_seconds):
                return fail(FailureCode.RESOURCE_INFEASIBLE, "elapsed-time budget exceeded")
            if result.size > context.budget.max_elements:
                return fail(
                    FailureCode.RESOURCE_INFEASIBLE,
                    "operation exceeded its preflight element estimate",
                    operation.id,
                )
            if result.nbytes > context.budget.max_output_bytes:
                return fail(
                    FailureCode.RESOURCE_INFEASIBLE,
                    "operation exceeded its preflight byte estimate",
                    operation.id,
                )
            if not np.all(np.isfinite(result)):
                return fail(
                    FailureCode.INVARIANT_VIOLATION,
                    "operation produced non-finite values",
                    operation.id,
                )
            max_elements = max(max_elements, int(result.size))
            max_tensor_bytes = max(max_tensor_bytes, int(result.nbytes))
            outputs[operation.id] = result

        output = outputs[plan.output_ref]
        if not self._matches_structural_type(output, plan.output_type):
            return fail(
                FailureCode.TYPE_MISMATCH,
                "output is outside the declared structural type",
                str(output.shape),
            )
        return finish(output)

    @staticmethod
    def _estimate_elements(
        operation: OperationSpec, inputs: tuple[NDArray[np.float64], ...]
    ) -> int:
        if operation.primitive == Primitive.CONSTANT.value:
            if inputs:
                raise ValueError("constant does not accept inputs")
            return len(operation.constant)
        if operation.primitive == Primitive.CONCAT.value:
            if not inputs:
                raise ValueError("concat requires at least one input")
            return sum(int(value.size) for value in inputs)
        if len(inputs) != 1:
            raise ValueError(f"{operation.primitive} requires exactly one input")
        if operation.primitive == Primitive.SELECT.value:
            return len(operation.indices)
        if operation.primitive == Primitive.AFFINE.value:
            rows = len(operation.matrix)
            if rows == 0:
                raise ValueError("affine requires a nonempty matrix")
            input_elements = int(inputs[0].size)
            if any(len(row) != input_elements for row in operation.matrix):
                raise ValueError("affine matrix width must match the input size")
            if operation.bias and len(operation.bias) != rows:
                raise ValueError("affine bias length must match the matrix row count")
            return rows
        if operation.primitive == Primitive.LOOKUP.value:
            if inputs[0].size != 1:
                raise ValueError("lookup requires a scalar index")
            if not operation.lookup_table:
                raise ValueError("lookup requires a nonempty table")
            widths = {len(row) for row in operation.lookup_table}
            if len(widths) != 1:
                raise ValueError("lookup rows must have equal widths")
            index_value = float(inputs[0].reshape(-1)[0])
            if not math.isfinite(index_value) or not index_value.is_integer():
                raise ValueError("lookup index must be a finite exact integer")
            index = int(index_value)
            if index < 0 or index >= len(operation.lookup_table):
                raise ValueError("lookup index is outside the table")
            return sum(len(row) for row in operation.lookup_table)
        return 0 if not inputs else int(inputs[0].size)

    @staticmethod
    def _parameter_elements(operation: OperationSpec) -> int:
        if operation.primitive == Primitive.CONSTANT.value:
            return len(operation.constant)
        if operation.primitive == Primitive.SELECT.value:
            return len(operation.indices)
        if operation.primitive == Primitive.AFFINE.value:
            matrix_elements = sum(len(row) for row in operation.matrix)
            return max(matrix_elements, len(operation.bias))
        if operation.primitive == Primitive.LOOKUP.value:
            return sum(len(row) for row in operation.lookup_table)
        if operation.primitive == Primitive.THRESHOLD.value:
            return 1
        return 0

    @staticmethod
    def _safe_dependency(value: object) -> NDArray[np.float64]:
        if type(value) is np.ndarray:
            array = value
            if array.dtype.kind not in "biuf":
                raise TypeError("dependency arrays must have a real numeric dtype")
            return array.astype(np.float64, copy=True)
        if type(value) in {bool, int, float}:
            return np.array(value, dtype=np.float64)
        raise TypeError("dependency must be an exact ndarray or JSON numeric scalar")

    @staticmethod
    def _elapsed_exceeded(elapsed: float, budget: float) -> bool:
        return budget == 0.0 or elapsed > budget

    @staticmethod
    def _matches_structural_type(value: NDArray[np.float64], expected: StructuralType) -> bool:
        if expected.precision is not None and expected.precision != str(value.dtype):
            return False
        if expected.field not in {None, "real"}:
            return False
        if expected.domain is not None or expected.unit is not None:
            return False
        if expected.kind is SpaceKind.SCALAR:
            return value.ndim == 0 and expected.dimensions == ()
        if expected.kind in {SpaceKind.VECTOR, SpaceKind.TENSOR}:
            return tuple(value.shape) == expected.dimensions
        return False
