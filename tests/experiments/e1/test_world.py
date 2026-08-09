from aire_prime.experiments.e1.world import (
    ResourceKind,
    generate_world,
    realize_capability,
)


def test_two_constructions_satisfy_the_same_capability_contract() -> None:
    world = generate_world(seed=101)

    battery = realize_capability(world, resource=ResourceKind.BATTERY)
    solar = realize_capability(world, resource=ResourceKind.SOLAR)

    assert battery.success
    assert solar.success
    assert battery.contract_id == solar.contract_id == world.contract.content_id
    assert battery.component_ids != solar.component_ids
    assert all(component.content_id for component in world.components)
    assert world.content_id


def test_hidden_resource_substitution_breaks_fixed_instance_not_constructor() -> None:
    world = generate_world(seed=101)
    fixed = realize_capability(world, resource=ResourceKind.BATTERY)

    fixed_under_transfer = realize_capability(
        world,
        resource=ResourceKind.SOLAR,
        fixed_component_ids=fixed.component_ids,
    )
    generated_under_transfer = realize_capability(world, resource=ResourceKind.SOLAR)

    assert not fixed_under_transfer.success
    assert "resource-substitution" in fixed_under_transfer.failed_tests
    assert generated_under_transfer.success
    assert world.hidden_test_ids


def test_world_seed_is_canonical_and_repeatable() -> None:
    first = generate_world(seed=101)
    second = generate_world(seed=101)
    different = generate_world(seed=102)

    assert first == second
    assert first.content_id == second.content_id
    assert first.content_id != different.content_id


def test_hidden_validator_rejects_unknown_duplicate_and_reordered_components() -> None:
    world = generate_world(seed=101)
    valid = realize_capability(world, resource=ResourceKind.SOLAR)

    unknown = realize_capability(
        world,
        resource=ResourceKind.SOLAR,
        fixed_component_ids=(*valid.component_ids[:-1], "sha256:" + "0" * 64),
    )
    duplicate = realize_capability(
        world,
        resource=ResourceKind.SOLAR,
        fixed_component_ids=(*valid.component_ids, valid.component_ids[-1]),
    )
    reordered = realize_capability(
        world,
        resource=ResourceKind.SOLAR,
        fixed_component_ids=tuple(reversed(valid.component_ids)),
    )

    assert unknown.failed_tests == ("unknown-component",)
    assert duplicate.failed_tests == ("duplicate-component",)
    assert not reordered.success
    assert "single-component-repair" in reordered.failed_tests
    assert valid.artifact_content_id != valid.content_id
