import random

from aire_prime.experiments.e3.contracts import (
    BaselineCompatibility,
    BaselinePacket,
)
from aire_prime.experiments.e3.recipient import evaluate_exchange
from aire_prime.experiments.e3.world import WorldSuite

BASELINE_IDS = ("B0", "B1", "B2", "B3", "B4", "B5", "B6")


def _pack_observation(observation: tuple[int, ...]) -> int:
    return sum(bit << index for index, bit in enumerate(observation))


def _source_pairs(source: WorldSuite, limit: int = 40) -> tuple[int, ...]:
    pairs: list[int] = []
    for world in source.worlds:
        for episode in world.episodes:
            pairs.extend((_pack_observation(episode.observation), episode.action))
            if len(pairs) // 2 >= limit:
                return tuple(pairs)
    return tuple(pairs)


def build_baseline_packets(source: WorldSuite, *, seed: int) -> tuple[BaselinePacket, ...]:
    generator = random.Random(seed)
    pairs = _source_pairs(source)
    random_payload = tuple(generator.randrange(2**31) for _ in range(180))
    compressed = tuple(value % 251 for value in pairs[:80])
    packets = (
        BaselinePacket(arm_id="B0", algorithm="none"),
        BaselinePacket(arm_id="B1", algorithm="random", payload=random_payload),
        BaselinePacket(arm_id="B2", algorithm="trajectory", payload=compressed),
        BaselinePacket(arm_id="B3", algorithm="nearest", payload=pairs),
        BaselinePacket(arm_id="B4", algorithm="distill", payload=(generator.randrange(97),)),
        BaselinePacket(arm_id="B5", algorithm="feature", payload=(generator.randrange(97),)),
        BaselinePacket(arm_id="B6", algorithm="world-model", payload=(generator.randrange(97),)),
        BaselinePacket(arm_id="B9", algorithm="oracle", payload=()),
    )
    for packet in packets:
        _ = packet.wire_bytes
    return packets


def baseline_compatibility() -> tuple[BaselineCompatibility, ...]:
    return (
        BaselineCompatibility(
            arm_id="B7",
            status="incompatible",
            rationale=(
                "available causal representation methods require continuous latent observations"
            ),
        ),
        BaselineCompatibility(
            arm_id="B8",
            status="incompatible",
            rationale=(
                "available symmetry alignment methods require a declared group action "
                "not present in E3 v1"
            ),
        ),
    )


__all__ = [
    "BASELINE_IDS",
    "baseline_compatibility",
    "build_baseline_packets",
    "evaluate_exchange",
]
