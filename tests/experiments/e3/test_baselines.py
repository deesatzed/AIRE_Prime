from aire_prime.experiments.e3.baselines import (
    BASELINE_IDS,
    baseline_compatibility,
    build_baseline_packets,
    evaluate_exchange,
)
from aire_prime.experiments.e3.contracts import BASELINE_ARM_IDS
from aire_prime.experiments.e3.recipient import RecipientSpec, run_recipient
from aire_prime.experiments.e3.world import generate_suite


def test_mandatory_baseline_packets_are_exactly_byte_matched_and_deterministic() -> None:
    source = generate_suite(root_seed=9, split="source")
    packets_a = build_baseline_packets(source, seed=31)
    packets_b = build_baseline_packets(source, seed=31)

    assert tuple(packet.arm_id for packet in packets_a) == BASELINE_ARM_IDS
    assert [packet.wire_bytes for packet in packets_a] == [
        packet.wire_bytes for packet in packets_b
    ]
    assert all(packet.packet_bytes == 2_048 for packet in packets_a)


def test_baselines_execute_against_identical_target_interactions() -> None:
    source = generate_suite(root_seed=9, split="source")
    target = generate_suite(root_seed=11, split="development").worlds[0]
    recipient = RecipientSpec(recipient_id="recipient-interpreter", kind="interpreter", seed=3)

    exchanges = tuple(
        run_recipient(packet, target, recipient)
        for packet in build_baseline_packets(source, seed=31)
        if packet.arm_id != "B9"
    )
    assert {len(exchange.predicted_actions) for exchange in exchanges} == {256}
    assert {exchange.calibration_episode_count for exchange in exchanges} == {32}
    scores = tuple(evaluate_exchange(target, exchange) for exchange in exchanges)
    assert all(score.valid for score in scores)
    assert all(score.evaluation_count == 256 for score in scores)


def test_oracle_is_headroom_only_and_b7_b8_are_not_silent_substitutions() -> None:
    records = baseline_compatibility()
    assert {record.arm_id for record in records} == {"B7", "B8"}
    assert all(record.status == "incompatible" for record in records)
    assert "B9" not in BASELINE_IDS
