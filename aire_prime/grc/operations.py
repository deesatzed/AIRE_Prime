from enum import StrEnum

import numpy as np
from numpy.typing import NDArray


class Primitive(StrEnum):
    IDENTITY = "identity"
    CONSTANT = "constant"
    SELECT = "select"
    AFFINE = "affine"
    CONCAT = "concat"
    NORMALIZE = "normalize"
    THRESHOLD = "threshold"
    LOOKUP = "lookup"


def execute_primitive(
    primitive: Primitive,
    inputs: tuple[NDArray[np.float64], ...],
    *,
    constant: tuple[float, ...],
    indices: tuple[int, ...],
    matrix: tuple[tuple[float, ...], ...],
    bias: tuple[float, ...],
    threshold: float,
    lookup_table: tuple[tuple[float, ...], ...],
) -> NDArray[np.float64]:
    if primitive is Primitive.CONSTANT:
        return np.asarray(constant, dtype=np.float64)
    if not inputs:
        raise ValueError(f"{primitive.value} requires at least one input")

    if primitive is Primitive.IDENTITY:
        return np.array(inputs[0], dtype=np.float64, copy=True)
    if primitive is Primitive.SELECT:
        return np.asarray(inputs[0], dtype=np.float64).reshape(-1)[list(indices)]
    if primitive is Primitive.AFFINE:
        weights = np.asarray(matrix, dtype=np.float64)
        offset = np.zeros(len(matrix), dtype=np.float64) if not bias else np.asarray(bias)
        return np.asarray(weights @ inputs[0].reshape(-1) + offset, dtype=np.float64)
    if primitive is Primitive.CONCAT:
        return np.concatenate(tuple(value.reshape(-1) for value in inputs)).astype(
            np.float64, copy=False
        )
    if primitive is Primitive.NORMALIZE:
        value = inputs[0].astype(np.float64, copy=False)
        scale = float(np.max(np.abs(value), initial=0.0))
        if scale == 0.0:
            return np.zeros_like(value)
        scaled = value / scale
        norm = float(np.sqrt(np.sum(scaled * scaled)))
        return scaled / norm
    if primitive is Primitive.THRESHOLD:
        return (inputs[0] >= threshold).astype(np.float64)
    if primitive is Primitive.LOOKUP:
        index = int(inputs[0].reshape(-1)[0])
        return np.asarray(lookup_table[index], dtype=np.float64)
    raise AssertionError(f"unhandled primitive: {primitive}")
