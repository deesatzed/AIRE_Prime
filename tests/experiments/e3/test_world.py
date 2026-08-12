from aire_prime.core.canonical import canonical_bytes
from aire_prime.experiments.e3.world import (
    E3_FAMILY_NAMES,
    WorldKey,
    episode_ids,
    generate_suite,
    generate_world,
)


def test_same_world_spec_is_byte_identical() -> None:
    first = generate_world(WorldKey(family="surface", seed=301))
    second = generate_world(WorldKey(family="surface", seed=301))

    assert first == second
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first.content_id == second.content_id


def test_distinct_split_domains_have_disjoint_episode_ids() -> None:
    source = generate_suite(root_seed=301, split="source")
    confirmatory = generate_suite(root_seed=301, split="confirmatory")

    assert episode_ids(source).isdisjoint(episode_ids(confirmatory))
    assert source.split == "source"
    assert confirmatory.split == "confirmatory"


def test_world_has_declared_causal_shape_and_interventions() -> None:
    world = generate_world(WorldKey(family="topology", seed=302))

    assert len(world.validator_spec.latent_state) == 6
    assert len(world.validator_spec.graph) == 6
    assert all(len(parents) <= 2 for parents in world.validator_spec.graph)
    assert all(
        parent < index
        for index, parents in enumerate(world.validator_spec.graph)
        for parent in parents
    )
    assert world.public_spec.action_count == 5
    assert world.public_spec.observation_bits == 48
    assert len(world.episodes) == 288
    assert all(len(episode.intervention_outcomes) == 5 for episode in world.episodes)


def test_all_shift_families_are_explicit() -> None:
    assert E3_FAMILY_NAMES == (
        "surface",
        "nuisance",
        "parameter",
        "composition",
        "topology",
        "sensor-loss",
    )


def test_proposer_view_excludes_validator_only_fields() -> None:
    world = generate_world(WorldKey(family="nuisance", seed=303))
    proposer = world.proposer_view()
    wire = canonical_bytes(proposer)

    assert b"latent_state" not in wire
    assert b"optimal_actions" not in wire
    assert b"validator_spec" not in wire
    assert b"split" not in wire
    assert all("latent_class" not in type(episode).model_fields for episode in proposer.episodes)
