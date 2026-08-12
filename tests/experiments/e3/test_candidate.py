import pytest

from aire_prime.experiments.e3.candidate import (
    ALLOWED_OPERATORS,
    discover_causal_program,
    run_candidate_recipient,
)
from aire_prime.experiments.e3.recipient import RecipientSpec
from aire_prime.experiments.e3.world import generate_suite


def _source_views():
    suite = generate_suite(root_seed=301, split="source")
    return tuple(world.proposer_view() for world in suite.worlds)


def test_candidate_is_deterministic_typed_and_byte_bounded() -> None:
    first = discover_causal_program(_source_views())
    second = discover_causal_program(_source_views())

    assert first.wire_bytes == second.wire_bytes
    assert len(first.wire_bytes) == 2_048
    assert first.packet_bytes == 2_048
    assert all(mechanism.operator in ALLOWED_OPERATORS for mechanism in first.mechanisms)
    assert first.operator_count == len(first.mechanisms)
    assert b"validator_spec" not in first.wire_bytes
    assert b"latent_state" not in first.wire_bytes
    assert b"target_world" not in first.wire_bytes


def test_candidate_requires_source_interaction_evidence() -> None:
    with pytest.raises(ValueError, match="source interaction evidence"):
        discover_causal_program(())


def test_candidate_recipient_uses_same_frozen_schedule_and_typed_boundary() -> None:
    packet = discover_causal_program(_source_views())
    target = generate_suite(root_seed=301, split="development").worlds[0]
    exchange = run_candidate_recipient(
        packet,
        target,
        RecipientSpec(recipient_id="recipient-interpreter", kind="interpreter", seed=7),
    )

    assert exchange.packet_arm_id == "candidate"
    assert exchange.calibration_episode_count == 32
    assert len(exchange.predicted_actions) == 256
    assert exchange.contained is True
    assert exchange.observation_access == "proposer-visible-v1"
    assert exchange.resources.external_calls.value == 0
