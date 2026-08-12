import pytest

from aire_prime.experiments.e3.contracts import (
    BASELINE_ARM_IDS,
    E3_HARD_CONTRACT,
    BaselineCompatibility,
    BaselinePacket,
)


def test_hard_contract_matches_preregistered_episode_schedule() -> None:
    assert E3_HARD_CONTRACT.packet_bytes == 2_048
    assert E3_HARD_CONTRACT.target_calibration_episodes == 32
    assert E3_HARD_CONTRACT.evaluation_episodes == 256
    assert E3_HARD_CONTRACT.external_calls == 0


def test_packet_wire_is_exactly_canonical_byte_ceiling() -> None:
    packet = BaselinePacket(arm_id="B0", algorithm="none", payload=())

    assert packet.packet_bytes == 2_048
    assert len(packet.wire_bytes) == 2_048
    assert packet.wire_bytes.startswith(b"{")


def test_oversized_packet_is_rejected() -> None:
    packet = BaselinePacket(arm_id="B0", algorithm="none", payload=tuple(range(2_000)))

    with pytest.raises(ValueError, match="packet exceeds"):
        _ = packet.wire_bytes


def test_baseline_registry_and_incompatibility_record_are_explicit() -> None:
    assert BASELINE_ARM_IDS == ("B0", "B1", "B2", "B3", "B4", "B5", "B6", "B9")
    record = BaselineCompatibility(
        arm_id="B7", status="incompatible", rationale="requires continuous latent state"
    )
    assert record.arm_id == "B7"
