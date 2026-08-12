import random
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel

E3_FAMILY_NAMES = (
    "surface",
    "nuisance",
    "parameter",
    "composition",
    "topology",
    "sensor-loss",
)
_SPLIT_NAMES = ("source", "development", "confirmatory")
_FAMILY_OFFSETS = {name: index * 100_003 for index, name in enumerate(E3_FAMILY_NAMES)}
_SPLIT_OFFSETS = {name: index * 10_000_019 for index, name in enumerate(_SPLIT_NAMES)}
_MECHANISM_KINDS = (
    "modular-step",
    "parent-gate",
    "equality-gate",
    "parity-gate",
    "saturating-step",
    "delayed-step",
)


class WorldFamily(StrEnum):
    SURFACE = "surface"
    NUISANCE = "nuisance"
    PARAMETER = "parameter"
    COMPOSITION = "composition"
    TOPOLOGY = "topology"
    SENSOR_LOSS = "sensor-loss"


class WorldKey(FrozenModel):
    family: Literal[
        "surface", "nuisance", "parameter", "composition", "topology", "sensor-loss"
    ]
    seed: int = Field(ge=0)


class MechanismSpec(FrozenModel):
    mechanism_id: str
    kind: str
    parents: tuple[int, ...]
    parameter: int = Field(ge=0, le=8)


class PublicWorldSpec(FrozenModel):
    mechanism_count: int = Field(default=6, ge=1)
    action_count: int = Field(default=5, ge=2)
    observation_bits: int = Field(default=48, ge=1)
    episode_horizon: int = Field(default=8, ge=1)
    episode_count: int = Field(default=288, ge=2)


class ValidatorWorldSpec(FrozenModel):
    latent_state: tuple[int, ...]
    graph: tuple[tuple[int, ...], ...]
    nuisance_state: tuple[int, ...]
    mechanisms: tuple[MechanismSpec, ...]
    optimal_actions: tuple[int, ...]
    action_permutation: tuple[int, ...]

    @field_validator("latent_state")
    @classmethod
    def require_ternary_state(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if len(value) != 6 or any(item not in (0, 1, 2) for item in value):
            raise ValueError("E3 latent state must contain six ternary values")
        return value

    @field_validator("nuisance_state")
    @classmethod
    def require_binary_nuisance(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if len(value) != 6 or any(item not in (0, 1) for item in value):
            raise ValueError("E3 nuisance state must contain six binary values")
        return value


class E3Episode(FrozenModel):
    episode_id: str
    observation: tuple[int, ...]
    action: int
    reward: int
    intervention_outcomes: tuple[int, ...]


class ProposerEpisode(FrozenModel):
    episode_id: str
    observation: tuple[int, ...]
    action: int
    reward: int
    intervention_outcomes: tuple[int, ...]


class ProposerWorld(FrozenModel):
    public_spec: PublicWorldSpec
    episodes: tuple[ProposerEpisode, ...]


class E3World(FrozenModel):
    key: WorldKey
    public_spec: PublicWorldSpec
    validator_spec: ValidatorWorldSpec
    episodes: tuple[E3Episode, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)

    def proposer_view(self) -> ProposerWorld:
        return ProposerWorld(
            public_spec=self.public_spec,
            episodes=tuple(
                ProposerEpisode(
                    episode_id=episode.episode_id,
                    observation=episode.observation,
                    action=episode.action,
                    reward=episode.reward,
                    intervention_outcomes=episode.intervention_outcomes,
                )
                for episode in self.episodes
            ),
        )


class WorldSuite(FrozenModel):
    root_seed: int = Field(ge=0)
    split: Literal["source", "development", "confirmatory"]
    worlds: tuple[E3World, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)


def _family_seed(key: WorldKey) -> int:
    return key.seed + _FAMILY_OFFSETS[key.family]


def _build_graph(generator: random.Random) -> tuple[tuple[int, ...], ...]:
    graph: list[tuple[int, ...]] = []
    for index in range(6):
        candidates = list(range(index))
        generator.shuffle(candidates)
        graph.append(tuple(sorted(candidates[: min(2, len(candidates))])))
    return tuple(graph)


def _observation(
    *, latent: tuple[int, ...], nuisance: tuple[int, ...], episode_index: int, family: str
) -> tuple[int, ...]:
    values: list[int] = []
    for bit in range(48):
        value = latent[bit % 6] + nuisance[(bit // 6) % 6] + episode_index + bit
        if family == "nuisance":
            value += nuisance[(bit + 2) % 6] * (1 if bit % 3 else -1)
        if family == "surface":
            value += (bit * 5) % 7
        if family == "sensor-loss" and bit % 7 == 0:
            values.append(0)
            continue
        values.append(value % 2)
    return tuple(values)


def generate_world(key: WorldKey) -> E3World:
    generator = random.Random(_family_seed(key))
    public_spec = PublicWorldSpec()
    graph = _build_graph(generator)
    mechanisms = tuple(
        MechanismSpec(
            mechanism_id=f"mechanism-{index}",
            kind=_MECHANISM_KINDS[index],
            parents=graph[index],
            parameter=generator.randrange(9),
        )
        for index in range(6)
    )
    latent_state = tuple(generator.randrange(3) for _ in range(6))
    nuisance_state = tuple(generator.randrange(2) for _ in range(6))
    permutation = list(range(public_spec.action_count))
    generator.shuffle(permutation)

    episodes: list[E3Episode] = []
    optimal_actions: list[int] = []
    for episode_index in range(public_spec.episode_count):
        latent = tuple(
            (value + episode_index + index) % 3 for index, value in enumerate(latent_state)
        )
        observation = _observation(
            latent=latent,
            nuisance=nuisance_state,
            episode_index=episode_index,
            family=key.family,
        )
        intervention_outcomes = tuple(
            (
                sum(latent)
                + action
                + sum(mechanism.parameter for mechanism in mechanisms if mechanism.parents)
                + episode_index
            )
            % 3
            for action in range(public_spec.action_count)
        )
        optimal = permutation[sum(latent) % public_spec.action_count]
        optimal_actions.append(optimal)
        chosen_action = episode_index % public_spec.action_count
        episodes.append(
            E3Episode(
                episode_id=content_id(
                    {"family": key.family, "seed": key.seed, "episode": episode_index}
                ),
                observation=observation,
                action=chosen_action,
                reward=int(chosen_action == optimal),
                intervention_outcomes=intervention_outcomes,
            )
        )

    validator_spec = ValidatorWorldSpec(
        latent_state=latent_state,
        graph=graph,
        nuisance_state=nuisance_state,
        mechanisms=mechanisms,
        optimal_actions=tuple(optimal_actions),
        action_permutation=tuple(permutation),
    )
    return E3World(
        key=key,
        public_spec=public_spec,
        validator_spec=validator_spec,
        episodes=tuple(episodes),
    )


def generate_suite(*, root_seed: int, split: str) -> WorldSuite:
    if split not in _SPLIT_NAMES:
        raise ValueError(f"unknown E3 split: {split}")
    split_seed = root_seed + _SPLIT_OFFSETS[split]
    worlds = tuple(
        generate_world(
            WorldKey(
                family=family,  # type: ignore[arg-type]
                seed=split_seed + index * 997,
            )
        )
        for index, family in enumerate(E3_FAMILY_NAMES)
    )
    return WorldSuite(root_seed=root_seed, split=split, worlds=worlds)  # type: ignore[arg-type]


def episode_ids(suite: WorldSuite) -> set[str]:
    return {episode.episode_id for world in suite.worlds for episode in world.episodes}
