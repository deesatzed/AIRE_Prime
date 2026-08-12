import hashlib
from typing import Literal, cast

from pydantic import Field

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e3.baselines import build_baseline_packets
from aire_prime.experiments.e3.candidate import (
    CausalProgramPacket,
    discover_causal_program,
    run_candidate_recipient,
)
from aire_prime.experiments.e3.recipient import (
    RECIPIENT_KINDS,
    BaselineScore,
    RecipientExchange,
    RecipientSpec,
    evaluate_exchange,
    run_oracle_recipient,
    run_recipient,
)
from aire_prime.experiments.e3.world import (
    E3_FAMILY_NAMES,
    E3World,
    WorldKey,
    WorldSuite,
    generate_suite,
    generate_world,
)

E3_ELIGIBLE_ARM_IDS = ("candidate", "B0", "B1", "B2", "B3", "B4", "B5", "B6")
E3_ALL_ARM_IDS = (*E3_ELIGIBLE_ARM_IDS, "B9")


class E3RunManifest(FrozenModel):
    split: Literal["development", "confirmatory"]
    root_seed: int = Field(ge=0)
    frozen_commit: str | None
    confirmatory_seed: str | None
    arm_ids: tuple[str, ...] = E3_ALL_ARM_IDS
    recipient_ids: tuple[str, ...]
    world_ids: tuple[str, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)


class E3RunBlock(FrozenModel):
    arm_id: str
    world_id: str
    shift_family: str
    recipient_id: str
    accuracy: float = Field(ge=0.0, le=1.0)
    valid: bool
    resource_state: Literal["observed", "undetermined"]
    packet_content_id: str
    failures: tuple[str, ...] = ()


class E3RunResult(FrozenModel):
    manifest: E3RunManifest
    candidate_packet_id: str
    blocks: tuple[E3RunBlock, ...]
    baseline_scores: tuple[BaselineScore, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)


def derive_confirmatory_seed(frozen_commit: str) -> str:
    if not frozen_commit.strip():
        raise ValueError("confirmatory seed derivation requires a frozen commit")
    return hashlib.sha256(
        f"AIRE-E3-CONFIRMATORY-V1{frozen_commit}".encode()
    ).hexdigest()


def _recipient_specs(root_seed: int) -> tuple[RecipientSpec, ...]:
    return tuple(
        RecipientSpec(
            recipient_id=f"recipient-{kind}",
            kind=cast(Literal["linear", "recurrent", "feedforward", "interpreter"], kind),
            seed=root_seed + index,
        )
        for index, kind in enumerate(RECIPIENT_KINDS)
    )


def _candidate_packet(source: WorldSuite) -> CausalProgramPacket:
    return discover_causal_program(tuple(world.proposer_view() for world in source.worlds))


def _target_suite(*, root_seed: int, split: Literal["development", "confirmatory"]) -> WorldSuite:
    if split == "development":
        return generate_suite(root_seed=root_seed, split=split)
    worlds = tuple(
        generate_world(
            WorldKey(
                family=family,  # type: ignore[arg-type]
                seed=root_seed + family_index * 1_000_003 + world_index * 9_973,
            )
        )
        for family_index, family in enumerate(E3_FAMILY_NAMES)
        for world_index in range(30)
    )
    return WorldSuite(root_seed=root_seed, split="confirmatory", worlds=worlds)


def _score_exchange(world: E3World, exchange: RecipientExchange) -> BaselineScore:
    return evaluate_exchange(world, exchange)


def run_e3_evaluation(
    *,
    split: Literal["development", "confirmatory"],
    root_seed: int,
    frozen_commit: str | None = None,
) -> E3RunResult:
    if split == "confirmatory" and not frozen_commit:
        raise ValueError("confirmatory evaluation requires a pushed frozen commit")
    source = generate_suite(root_seed=root_seed, split="source")
    targets = _target_suite(root_seed=root_seed, split=split)
    candidate = _candidate_packet(source)
    packets = build_baseline_packets(source, seed=root_seed)
    specs = _recipient_specs(root_seed)
    blocks: list[E3RunBlock] = []
    scores: list[BaselineScore] = []
    for world in targets.worlds:
        for spec in specs:
            for packet in packets:
                exchange = (
                    run_oracle_recipient(packet, world, spec)
                    if packet.arm_id == "B9"
                    else run_recipient(packet, world, spec)
                )
                score = _score_exchange(world, exchange)
                scores.append(score)
                blocks.append(
                    E3RunBlock(
                        arm_id=score.arm_id,
                        world_id=world.content_id,
                        shift_family=world.key.family,
                        recipient_id=score.recipient_id,
                        accuracy=score.accuracy,
                        valid=score.valid,
                        resource_state="observed",
                        packet_content_id=packet.content_id,
                    )
                )
            exchange = run_candidate_recipient(candidate, world, spec)
            score = _score_exchange(world, exchange)
            scores.append(score)
            blocks.append(
                E3RunBlock(
                    arm_id="candidate",
                    world_id=world.content_id,
                    shift_family=world.key.family,
                    recipient_id=score.recipient_id,
                    accuracy=score.accuracy,
                    valid=score.valid,
                    resource_state="observed",
                    packet_content_id=candidate.content_id,
                )
            )
    confirmatory_seed = derive_confirmatory_seed(frozen_commit) if frozen_commit else None
    manifest = E3RunManifest(
        split=split,
        root_seed=root_seed,
        frozen_commit=frozen_commit,
        confirmatory_seed=confirmatory_seed,
        recipient_ids=tuple(spec.recipient_id for spec in specs),
        world_ids=tuple(world.content_id for world in targets.worlds),
    )
    return E3RunResult(
        manifest=manifest,
        candidate_packet_id=candidate.content_id,
        blocks=tuple(blocks),
        baseline_scores=tuple(scores),
    )


__all__ = [
    "E3_ALL_ARM_IDS",
    "E3_ELIGIBLE_ARM_IDS",
    "E3RunBlock",
    "E3RunManifest",
    "E3RunResult",
    "derive_confirmatory_seed",
    "run_e3_evaluation",
]
