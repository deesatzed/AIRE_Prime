from aire_prime.experiments.e3.ablations import (
    ABLATION_KINDS,
    build_ablation_packets,
)
from aire_prime.experiments.e3.candidate import discover_causal_program
from aire_prime.experiments.e3.world import generate_suite


def test_targeted_sham_and_wrong_object_transformations_are_equal_size_and_distinct() -> None:
    source = generate_suite(root_seed=301, split="source")
    packet = discover_causal_program(tuple(world.proposer_view() for world in source.worlds))
    other = generate_suite(root_seed=302, split="source")
    other_packet = discover_causal_program(tuple(world.proposer_view() for world in other.worlds))

    transformed = build_ablation_packets(packet, wrong_object=other_packet)

    assert tuple(item.kind for item in transformed) == ABLATION_KINDS
    assert len({item.packet.content_id for item in transformed}) == len(ABLATION_KINDS)
    assert {len(item.packet.wire_bytes) for item in transformed} == {2_048}
    assert all(item.packet.operator_count == packet.operator_count for item in transformed)
    assert tuple(item.kind for item in transformed[:3]) == (
        "remove-causal-operator",
        "permute-dependency-edges",
        "replace-mechanism-parameters",
    )
    assert all(item.targeted for item in transformed[:3])
    assert all(not item.targeted for item in transformed[3:])


def test_ablation_records_changed_fields_and_no_confirmatory_inputs() -> None:
    source = generate_suite(root_seed=301, split="source")
    packet = discover_causal_program(tuple(world.proposer_view() for world in source.worlds))
    transformed = build_ablation_packets(packet, wrong_object=packet)

    assert all(item.changed_fields for item in transformed)
    assert all(item.source_packet_id == packet.content_id for item in transformed)
