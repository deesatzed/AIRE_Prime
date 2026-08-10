import random

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel


class CausalEpisode(FrozenModel):
    episode_id: str
    raw_observation: tuple[int, ...]
    probe_success: int
    latent_class: int
    optimal_physical_action: int

    @property
    def content_id(self) -> str:
        return content_id(self)


class CausalSplit(FrozenModel):
    name: str
    seed_commitment: str
    action_label_map: tuple[tuple[int, int], ...]
    episodes: tuple[CausalEpisode, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)


class SyntheticCausalWorld(FrozenModel):
    seed: int
    starting_distribution_commitment: str
    baseline_feature_schema: tuple[str, ...]
    splits: tuple[CausalSplit, ...]

    @property
    def content_id(self) -> str:
        return content_id(self)

    @property
    def train(self) -> CausalSplit:
        return self._split("train")

    @property
    def validation(self) -> CausalSplit:
        return self._split("validation")

    @property
    def hidden_test(self) -> CausalSplit:
        return self._split("hidden-test")

    @property
    def transformed_test(self) -> CausalSplit:
        return self._split("transformed-test")

    @property
    def split_commitments(self) -> tuple[str, ...]:
        return tuple(split.content_id for split in self.splits)

    def _split(self, name: str) -> CausalSplit:
        return next(split for split in self.splits if split.name == name)

    def discovery_packet(self) -> dict[str, object]:
        return {
            "baseline_feature_schema": self.baseline_feature_schema,
            "training_episodes": tuple(
                {
                    "episode_id": episode.episode_id,
                    "raw_observation": episode.raw_observation,
                    "probe_success": episode.probe_success,
                    "action_outcomes": tuple(
                        (
                            action,
                            1 if action == episode.optimal_physical_action else 0,
                        )
                        for action in (0, 1)
                    ),
                }
                for episode in self.train.episodes
            ),
            "training_commitment": self.train.content_id,
        }


def _generate_split(*, name: str, seed: int, transformed: bool) -> CausalSplit:
    generator = random.Random(seed)
    classes = [0, 1] * 20
    generator.shuffle(classes)
    episodes = tuple(
        CausalEpisode(
            episode_id=content_id({"split_seed": seed, "index": index}),
            raw_observation=(0,),
            probe_success=1 if latent_class == 0 else 0,
            latent_class=latent_class,
            optimal_physical_action=latent_class,
        )
        for index, latent_class in enumerate(classes)
    )
    return CausalSplit(
        name=name,
        seed_commitment=content_id({"split": name, "seed": seed}),
        action_label_map=((0, 1), (1, 0)) if transformed else ((0, 0), (1, 1)),
        episodes=episodes,
    )


def generate_causal_world(seed: int) -> SyntheticCausalWorld:
    split_specs = (
        ("train", seed * 100 + 11, False),
        ("validation", seed * 100 + 23, False),
        ("hidden-test", seed * 100 + 37, False),
        ("transformed-test", seed * 100 + 53, True),
    )
    return SyntheticCausalWorld(
        seed=seed,
        starting_distribution_commitment=content_id(
            {"seed": seed, "distribution": "validator-hidden-balanced-binary"}
        ),
        baseline_feature_schema=("raw_observation",),
        splits=tuple(
            _generate_split(name=name, seed=split_seed, transformed=transformed)
            for name, split_seed, transformed in split_specs
        ),
    )
