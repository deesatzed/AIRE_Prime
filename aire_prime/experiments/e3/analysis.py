import math
from typing import Literal

import numpy as np
from pydantic import Field

from aire_prime.core.model import FrozenModel


class E3Block(FrozenModel):
    arm_id: str
    world_id: str
    shift_family: str
    recipient_id: str
    auc: float = Field(ge=0.0, le=1.0)
    valid: bool
    resource_state: Literal["observed", "undetermined"]


class E3AnalysisResult(FrozenModel):
    status: Literal["provisional", "rejected", "undetermined"]
    resampling_unit: Literal["world"]
    candidate_arm: str
    maximum_baseline: str | None
    point_effect: float | None
    bootstrap_distribution: tuple[float, ...]


def adaptation_auc(values: tuple[float, ...]) -> float:
    if len(values) < 2 or any(not math.isfinite(value) for value in values):
        raise ValueError("adaptation AUC requires at least two finite observations")
    return sum((left + right) / 2 for left, right in zip(values, values[1:], strict=False)) / (
        len(values) - 1
    )


def _world_values(blocks: tuple[E3Block, ...]) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    for block in blocks:
        arm_values = grouped.setdefault(block.world_id, {})
        if block.arm_id in arm_values:
            raise ValueError("E3 analysis requires one block per arm and world")
        arm_values[block.arm_id] = block.auc
    return grouped


def analyze_confirmatory(
    blocks: tuple[E3Block, ...], *, seed: int, bootstrap_replicates: int = 100_000
) -> E3AnalysisResult:
    if bootstrap_replicates <= 0:
        raise ValueError("bootstrap_replicates must be positive")
    if not blocks:
        raise ValueError("E3 analysis requires blocks")
    candidate_ids = {block.arm_id for block in blocks if block.arm_id == "candidate"}
    baseline_ids = sorted({block.arm_id for block in blocks if block.arm_id != "candidate"})
    grouped = _world_values(blocks)
    worlds = tuple(sorted(grouped))
    complete = bool(candidate_ids and baseline_ids) and all(
        set(grouped[world]) == {"candidate", *baseline_ids} for world in worlds
    )
    valid = complete and all(block.valid and block.resource_state == "observed" for block in blocks)
    if not valid:
        return E3AnalysisResult(
            status="undetermined",
            resampling_unit="world",
            candidate_arm="candidate",
            maximum_baseline=None,
            point_effect=None,
            bootstrap_distribution=(),
        )

    candidate_means = [grouped[world]["candidate"] for world in worlds]
    baseline_means = {
        arm_id: [grouped[world][arm_id] for world in worlds] for arm_id in baseline_ids
    }
    maximum_baseline = max(
        baseline_ids, key=lambda arm_id: float(np.mean(baseline_means[arm_id]))
    )
    point_effect = float(
        np.mean(candidate_means) - max(np.mean(values) for values in baseline_means.values())
    )
    rng = np.random.default_rng(seed)
    distribution: list[float] = []
    for _ in range(bootstrap_replicates):
        indices = rng.integers(0, len(worlds), size=len(worlds))
        candidate_mean = float(np.mean([candidate_means[index] for index in indices]))
        baseline_effects = [
            float(np.mean([values[index] for index in indices]))
            for values in baseline_means.values()
        ]
        distribution.append(candidate_mean - max(baseline_effects))
    return E3AnalysisResult(
        status="provisional" if point_effect > 0 else "rejected",
        resampling_unit="world",
        candidate_arm="candidate",
        maximum_baseline=maximum_baseline,
        point_effect=point_effect,
        bootstrap_distribution=tuple(distribution),
    )


def holm_adjust(p_values: tuple[float, ...]) -> tuple[float, ...]:
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in p_values):
        raise ValueError("p-values must be finite values in [0, 1]")
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted_sorted: list[float] = []
    running = 0.0
    count = len(p_values)
    for rank, (_, p_value) in enumerate(indexed):
        running = max(running, min(1.0, (count - rank) * p_value))
        adjusted_sorted.append(running)
    adjusted = [0.0] * count
    for (index, _), value in zip(indexed, adjusted_sorted, strict=True):
        adjusted[index] = value
    return tuple(adjusted)
