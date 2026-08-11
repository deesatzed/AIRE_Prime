from aire_prime.experiments.e3.leakage import (
    E3_PACKET_BYTES,
    audit_proposer_view,
    minimum_exact_policy_bytes,
)
from aire_prime.experiments.e3.world import WorldKey, generate_suite, generate_world


def test_proposer_wire_excludes_validator_fields() -> None:
    world = generate_world(WorldKey(family="surface", seed=401))
    audit = audit_proposer_view(world)

    assert audit.forbidden_tokens == ()
    assert audit.packet_bytes > 0


def test_policy_table_lower_bound_exceeds_packet_budget() -> None:
    suite = generate_suite(root_seed=401, split="source")

    assert minimum_exact_policy_bytes(suite) > E3_PACKET_BYTES


def test_leakage_audit_requires_capacity_gap() -> None:
    world = generate_world(WorldKey(family="composition", seed=402))
    audit = audit_proposer_view(world)

    assert audit.packet_bytes <= minimum_exact_policy_bytes(
        generate_suite(root_seed=402, split="source")
    )
    assert audit.capacity_gap
