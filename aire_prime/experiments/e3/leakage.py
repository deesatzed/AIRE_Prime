from aire_prime.core.canonical import canonical_bytes
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e3.world import E3World, WorldSuite

E3_PACKET_BYTES = 2_048
_FORBIDDEN_TOKENS = (
    "latent_state",
    "optimal_actions",
    "validator_spec",
    "nuisance_state",
    "action_permutation",
    "mechanisms",
    "split",
    "root_seed",
)


class LeakageAudit(FrozenModel):
    packet_bytes: int
    exact_policy_bytes: int
    forbidden_tokens: tuple[str, ...]
    capacity_gap: bool


def _exact_policy_bytes(worlds: tuple[E3World, ...]) -> int:
    exact_rows = tuple(
        {
            "episode_id": episode.episode_id,
            "observation": episode.observation,
            "action": episode.action,
        }
        for world in worlds
        for episode in world.episodes
    )
    return len(canonical_bytes(exact_rows))


def minimum_exact_policy_bytes(suite: WorldSuite) -> int:
    return _exact_policy_bytes(suite.worlds)


def audit_proposer_view(world: E3World) -> LeakageAudit:
    payload = canonical_bytes(world.proposer_view())
    exact_policy_bytes = _exact_policy_bytes((world,))
    forbidden_tokens = tuple(
        token for token in _FORBIDDEN_TOKENS if token.encode("utf-8") in payload
    )
    return LeakageAudit(
        packet_bytes=len(payload),
        exact_policy_bytes=exact_policy_bytes,
        forbidden_tokens=forbidden_tokens,
        capacity_gap=exact_policy_bytes > E3_PACKET_BYTES,
    )
