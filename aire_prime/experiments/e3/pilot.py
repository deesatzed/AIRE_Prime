import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Literal, cast

from pydantic import Field

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e3.baselines import build_baseline_packets
from aire_prime.experiments.e3.contracts import BASELINE_ARM_IDS
from aire_prime.experiments.e3.leakage import audit_proposer_view, minimum_exact_policy_bytes
from aire_prime.experiments.e3.recipient import (
    RECIPIENT_KINDS,
    RecipientSpec,
    evaluate_exchange,
    run_oracle_recipient,
    run_recipient,
)
from aire_prime.experiments.e3.world import generate_suite


class PilotManifest(FrozenModel):
    root_seed: int = Field(ge=0)
    split: Literal["development"] = "development"
    arm_ids: tuple[str, ...] = BASELINE_ARM_IDS
    recipient_kinds: tuple[str, ...] = RECIPIENT_KINDS
    candidate_access: bool = False
    confirmatory_seed_domain: str | None = None

    @property
    def content_id(self) -> str:
        return content_id(self)


class PilotBlock(FrozenModel):
    arm_id: str
    world_id: str
    shift_family: str
    recipient_id: str
    auc: float = Field(ge=0.0, le=1.0)
    valid: bool
    resource_state: Literal["observed", "undetermined"]


class PilotResult(FrozenModel):
    manifest: PilotManifest
    blocks: tuple[PilotBlock, ...]
    world_variance: float = Field(ge=0.0)
    oracle_headroom: float
    capacity_gap: bool
    leakage_clean: bool

    @property
    def content_id(self) -> str:
        return content_id(self)


def build_pilot_manifest(*, root_seed: int) -> PilotManifest:
    return PilotManifest(root_seed=root_seed)


def run_pilot(*, root_seed: int) -> PilotResult:
    manifest = build_pilot_manifest(root_seed=root_seed)
    source = generate_suite(root_seed=root_seed, split="source")
    development = generate_suite(root_seed=root_seed, split="development")
    packets = build_baseline_packets(source, seed=root_seed)
    specs = tuple(
        RecipientSpec(
            recipient_id=f"recipient-{kind}",
            kind=cast(Literal["linear", "recurrent", "feedforward", "interpreter"], kind),
            seed=root_seed + index,
        )
        for index, kind in enumerate(RECIPIENT_KINDS)
    )
    blocks: list[PilotBlock] = []
    by_world: dict[str, list[float]] = defaultdict(list)
    oracle_scores: list[float] = []
    leakage_clean = True
    for world in development.worlds:
        leakage_clean = leakage_clean and not audit_proposer_view(world).forbidden_tokens
        expected = world.validator_spec.optimal_actions[32:]
        oracle = sum(
            action == expected_action
            for action, expected_action in zip(expected, expected, strict=True)
        ) / len(expected)
        oracle_scores.append(oracle)
        for packet in packets:
            for spec in specs:
                exchange = (
                    run_oracle_recipient(packet, world, spec)
                    if packet.arm_id == "B9"
                    else run_recipient(packet, world, spec)
                )
                score = evaluate_exchange(world, exchange)
                block = PilotBlock(
                    arm_id=score.arm_id,
                    world_id=world.content_id,
                    shift_family=world.key.family,
                    recipient_id=score.recipient_id,
                    auc=score.accuracy,
                    valid=score.valid,
                    resource_state="observed",
                )
                blocks.append(block)
                if packet.arm_id != "B9":
                    by_world[world.content_id].append(score.accuracy)
    world_means = tuple(sum(values) / len(values) for values in by_world.values())
    mean = sum(world_means) / len(world_means)
    world_variance = sum((value - mean) ** 2 for value in world_means) / len(world_means)
    maximum_baseline = max(block.auc for block in blocks if block.arm_id != "B9")
    return PilotResult(
        manifest=manifest,
        blocks=tuple(blocks),
        world_variance=world_variance,
        oracle_headroom=sum(oracle_scores) / len(oracle_scores) - maximum_baseline,
        capacity_gap=minimum_exact_policy_bytes(source) > 2_048,
        leakage_clean=leakage_clean,
    )


__all__ = ["PilotBlock", "PilotManifest", "PilotResult", "build_pilot_manifest", "run_pilot"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the E3 baseline/oracle-only development pilot"
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_pilot(root_seed=args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "pilot_manifest.json").write_text(
        json.dumps(result.manifest.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output / "pilot_result.json").write_text(
        json.dumps(result.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(result.content_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
