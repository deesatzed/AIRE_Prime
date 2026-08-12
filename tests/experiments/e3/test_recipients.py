import pytest

from aire_prime.experiments.e3.baselines import build_baseline_packets
from aire_prime.experiments.e3.recipient import (
    RECIPIENT_KINDS,
    RecipientSpec,
    build_recipient_state,
    run_recipient,
)
from aire_prime.experiments.e3.world import generate_suite


def test_recipient_families_have_distinct_seeded_identities_and_state() -> None:
    specs = tuple(
        RecipientSpec(recipient_id=f"recipient-{kind}", kind=kind, seed=41)
        for kind in RECIPIENT_KINDS
    )
    assert len({spec.identity for spec in specs}) == len(specs)
    states = tuple(build_recipient_state(spec) for spec in specs)
    assert len({state.content_id for state in states}) == len(states)
    assert all(spec.adapter_version == "e3-reviewed-contained-v1" for spec in specs)
    assert all(spec.external_calls == 0 for spec in specs)
    assert all(spec.calibration_schedule_id == "e3-calibration-v1" for spec in specs)


def test_recipient_uses_typed_packet_and_same_calibration_schedule() -> None:
    suite = generate_suite(root_seed=9, split="source")
    target = generate_suite(root_seed=11, split="development").worlds[0]
    packet = build_baseline_packets(suite, seed=7)[0]
    spec = RecipientSpec(recipient_id="recipient-linear", kind="linear", seed=7)

    exchange = run_recipient(packet, target, spec)

    assert exchange.contained is True
    assert exchange.calibration_episode_count == 32
    assert len(exchange.predicted_actions) == 256
    assert exchange.observation_access == "proposer-visible-v1"
    assert exchange.resources.packet_bytes.value == 2_048


def test_malformed_packet_and_invalid_recipient_fail_closed() -> None:
    suite = generate_suite(root_seed=9, split="source")
    target = generate_suite(root_seed=11, split="development").worlds[0]
    packet = build_baseline_packets(suite, seed=7)[0]
    with pytest.raises(ValueError, match="recipient kind"):
        RecipientSpec(recipient_id="bad", kind="unknown", seed=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="packet arm"):
        run_recipient(packet.model_copy(update={"arm_id": "not-registered"}), target, RecipientSpec(
            recipient_id="recipient-linear", kind="linear", seed=7
        ))
