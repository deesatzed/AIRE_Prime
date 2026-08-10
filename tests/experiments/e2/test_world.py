from aire_prime.experiments.e2.world import generate_causal_world


def test_seeded_world_freezes_distinct_split_commitments() -> None:
    first = generate_causal_world(seed=202)
    second = generate_causal_world(seed=202)
    different = generate_causal_world(seed=203)

    assert first == second
    assert first.content_id == second.content_id
    assert first.content_id != different.content_id
    assert len(set(first.split_commitments)) == 4
    assert {split.name for split in first.splits} == {
        "train",
        "validation",
        "hidden-test",
        "transformed-test",
    }


def test_conventional_schema_conflates_a_consequential_state_pair() -> None:
    world = generate_causal_world(seed=202)
    zero = next(episode for episode in world.train.episodes if episode.latent_class == 0)
    one = next(episode for episode in world.train.episodes if episode.latent_class == 1)

    assert zero.raw_observation == one.raw_observation
    assert zero.optimal_physical_action != one.optimal_physical_action
    assert world.baseline_feature_schema == ("raw_observation",)


def test_hidden_and_transformed_details_are_not_in_discovery_packet() -> None:
    world = generate_causal_world(seed=202)
    packet = world.discovery_packet()
    packet_text = str(packet)

    assert "hidden-test" not in packet_text
    assert "transformed-test" not in packet_text
    assert all(commitment not in packet_text for commitment in world.split_commitments[2:])
    assert all(
        "optimal_physical_action" not in episode and "latent_class" not in episode
        for episode in packet["training_episodes"]
    )
