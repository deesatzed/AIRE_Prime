import math
import random
from enum import StrEnum
from statistics import fmean
from typing import Self

from pydantic import field_validator, model_validator

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.objects import ContentID


class AblationKind(StrEnum):
    TARGETED = "targeted"
    RANDOM_SUBSPACE = "random-subspace"
    ACTIVATION_PERMUTATION = "activation-permutation"
    REPRESENTATION_REPLACEMENT = "representation-replacement"


class AblationResult(FrozenModel):
    kind: AblationKind
    selected_dimensions: tuple[int, ...]
    mean_absolute_effect: float

    @field_validator("selected_dimensions")
    @classmethod
    def normalize_dimensions(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(index < 0 for index in value) or len(value) != len(set(value)):
            raise ValueError("ablation dimensions must be unique nonnegative indexes")
        return tuple(sorted(value))

    @field_validator("mean_absolute_effect")
    @classmethod
    def require_finite_effect(cls, value: float) -> float:
        if not math.isfinite(value) or value < 0:
            raise ValueError("ablation effect must be finite and nonnegative")
        return value

    @property
    def content_id(self) -> str:
        return content_id(self)


class AblationReport(FrozenModel):
    seed: int
    activation_content_id: ContentID
    target_content_id: ContentID
    evaluator_id: str
    metric_id: str
    replacement_strategy: str
    results: tuple[AblationResult, ...]

    @field_validator("evaluator_id", "metric_id", "replacement_strategy")
    @classmethod
    def require_procedure_commitment(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("ablation procedure identifiers must be trimmed and nonblank")
        return value

    @model_validator(mode="after")
    def require_every_frozen_control(self) -> Self:
        kinds = tuple(result.kind for result in self.results)
        if len(kinds) != len(set(kinds)) or set(kinds) != set(AblationKind):
            raise ValueError("ablation report must retain every standard control exactly once")
        return self

    @property
    def targeted(self) -> AblationResult:
        return next(result for result in self.results if result.kind is AblationKind.TARGETED)

    @property
    def sham_controls(self) -> tuple[AblationResult, ...]:
        return tuple(
            result for result in self.results if result.kind is not AblationKind.TARGETED
        )

    @property
    def content_id(self) -> str:
        return content_id(self)


def _validate_activations(
    activations: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], ...]:
    if not activations or not activations[0]:
        raise ValueError("ablations require a nonempty activation matrix")
    width = len(activations[0])
    if any(
        len(row) != width or any(not math.isfinite(value) for value in row)
        for row in activations
    ):
        raise ValueError("activation matrix must be rectangular and finite")
    return activations


def _effect(
    original: tuple[tuple[float, ...], ...],
    changed: tuple[tuple[float, ...], ...],
) -> float:
    return fmean(
        abs(before - after)
        for original_row, changed_row in zip(original, changed, strict=True)
        for before, after in zip(original_row, changed_row, strict=True)
    )


def _zero_dimensions(
    activations: tuple[tuple[float, ...], ...], dimensions: tuple[int, ...]
) -> tuple[tuple[float, ...], ...]:
    selected = set(dimensions)
    return tuple(
        tuple(0.0 if index in selected else value for index, value in enumerate(row))
        for row in activations
    )


def run_standard_ablations(
    *,
    activations: tuple[tuple[float, ...], ...],
    targeted_dimensions: tuple[int, ...],
    seed: int,
) -> AblationReport:
    matrix = _validate_activations(activations)
    width = len(matrix[0])
    targeted = tuple(sorted(targeted_dimensions))
    if (
        not targeted
        or len(targeted) != len(set(targeted))
        or any(index < 0 or index >= width for index in targeted)
    ):
        raise ValueError("targeted dimensions must be unique valid indexes")

    generator = random.Random(seed)
    alternatives = [index for index in range(width) if index not in targeted]
    if len(alternatives) < len(targeted):
        raise ValueError("equal-size random sham requires enough non-target dimensions")
    random_dimensions = tuple(sorted(generator.sample(alternatives, len(targeted))))

    permuted_rows = [list(row) for row in matrix]
    for dimension in targeted:
        values = [row[dimension] for row in permuted_rows]
        generator.shuffle(values)
        for row, value in zip(permuted_rows, values, strict=True):
            row[dimension] = value
    permuted = tuple(tuple(row) for row in permuted_rows)

    column_means = tuple(fmean(row[index] for row in matrix) for index in range(width))
    replaced = tuple(
        tuple(
            column_means[index] if index in targeted else value
            for index, value in enumerate(row)
        )
        for row in matrix
    )
    results = (
        AblationResult(
            kind=AblationKind.TARGETED,
            selected_dimensions=targeted,
            mean_absolute_effect=_effect(matrix, _zero_dimensions(matrix, targeted)),
        ),
        AblationResult(
            kind=AblationKind.RANDOM_SUBSPACE,
            selected_dimensions=random_dimensions,
            mean_absolute_effect=_effect(
                matrix, _zero_dimensions(matrix, random_dimensions)
            ),
        ),
        AblationResult(
            kind=AblationKind.ACTIVATION_PERMUTATION,
            selected_dimensions=targeted,
            mean_absolute_effect=_effect(matrix, permuted),
        ),
        AblationResult(
            kind=AblationKind.REPRESENTATION_REPLACEMENT,
            selected_dimensions=targeted,
            mean_absolute_effect=_effect(matrix, replaced),
        ),
    )
    return AblationReport(
        seed=seed,
        activation_content_id=content_id(matrix),
        target_content_id=content_id(targeted),
        evaluator_id="aire:mean-absolute-effect:v1",
        metric_id="metric:activation-absolute-difference:v1",
        replacement_strategy="per-dimension-observed-mean:v1",
        results=results,
    )
