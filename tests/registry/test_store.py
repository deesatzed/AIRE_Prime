import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.registry.events import GENESIS_EVENT_HASH, RegistryEvent
from aire_prime.registry.lifecycle import InvalidLifecycleTransition, LifecycleState
from aire_prime.registry.store import RegistryStore, RegistryVerificationError


def fixed_clock() -> Any:
    current = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)

    def tick() -> datetime:
        nonlocal current
        value = current
        current += timedelta(seconds=1)
        return value

    return tick


def append_path(store: RegistryStore, object_payload: dict[str, Any]) -> list[RegistryEvent]:
    events = []
    for state in (
        LifecycleState.DRAFT,
        LifecycleState.SUBMITTED,
        LifecycleState.CONTRACT_BOUND,
        LifecycleState.VALIDATION_PENDING,
        LifecycleState.PROVISIONAL,
    ):
        events.append(
            store.append(
                actor_role="validator" if state is not LifecycleState.DRAFT else "proposer",
                actor_id="agent:1",
                object_payload=object_payload,
                event_type=state,
                event_payload={"note": state.value},
            )
        )
    return events


def test_append_emits_required_hash_chained_fields_and_verifies(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    events = append_path(store, {"kind": "sense", "version": 1})

    verified = store.verify()

    assert verified == tuple(events)
    assert events[0].sequence == 0
    assert events[0].previous_event_hash == GENESIS_EVENT_HASH
    assert events[1].previous_event_hash == events[0].event_content_id
    line = json.loads(store.path.read_text().splitlines()[0])
    assert {
        "sequence",
        "timestamp",
        "actor_role",
        "actor_id",
        "object_id",
        "event_type",
        "previous_event_hash",
        "payload_content_id",
        "event_content_id",
    } <= set(line)
    assert store.path.read_bytes().endswith(b"\n")


def test_invalid_transition_is_rejected_without_changing_file(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    payload = {"kind": "sense", "version": 1}
    store.append(
        actor_role="proposer",
        actor_id="agent:1",
        object_payload=payload,
        event_type=LifecycleState.DRAFT,
        event_payload={},
    )
    before = store.path.read_bytes()

    with pytest.raises(InvalidLifecycleTransition):
        store.append(
            actor_role="validator",
            actor_id="agent:2",
            object_payload=payload,
            event_type=LifecycleState.REPLICATED,
            event_payload={},
        )

    assert store.path.read_bytes() == before


def test_supersession_uses_new_identity_and_retains_old_failure_evidence(
    tmp_path: Path,
) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    old_payload = {"kind": "sense", "version": 1}
    new_payload = {"kind": "sense", "version": 2}
    old_events = append_path(store, old_payload)[:-1]
    restricted = store.append(
        actor_role="validator",
        actor_id="agent:2",
        object_payload=old_payload,
        event_type=LifecycleState.RESTRICTED,
        event_payload={"failures": ["counterexample: hidden transform"]},
    )
    successor = store.append(
        actor_role="proposer",
        actor_id="agent:3",
        object_payload=new_payload,
        event_type=LifecycleState.DRAFT,
        event_payload={"supersedes": restricted.object_id},
    )
    superseded = store.append(
        actor_role="authorizer",
        actor_id="agent:4",
        object_payload=old_payload,
        event_type=LifecycleState.SUPERSEDED,
        event_payload={"successor_object_id": successor.object_id},
    )

    verified = store.verify()

    assert successor.object_id != restricted.object_id
    assert old_events[0] in verified
    assert restricted in verified
    assert "counterexample: hidden transform" in restricted.payload_json
    assert superseded.object_id == restricted.object_id


def test_corrupting_prior_line_fails_verification(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    append_path(store, {"kind": "sense", "version": 1})
    text = store.path.read_text()
    store.path.write_text(text.replace("Draft", "Draxx", 1))

    with pytest.raises(RegistryVerificationError):
        store.verify()


def test_reordering_events_fails_verification(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    append_path(store, {"kind": "sense", "version": 1})
    lines = store.path.read_text().splitlines()
    lines[1], lines[2] = lines[2], lines[1]
    store.path.write_text("\n".join(lines) + "\n")

    with pytest.raises(RegistryVerificationError, match="sequence|hash"):
        store.verify()


def test_breaking_hash_link_fails_even_with_recomputed_event_id(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    append_path(store, {"kind": "sense", "version": 1})
    lines = store.path.read_text().splitlines()
    second = json.loads(lines[1])
    second["previous_event_hash"] = GENESIS_EVENT_HASH
    identity = {key: value for key, value in second.items() if key != "event_content_id"}
    second["event_content_id"] = content_id(identity)
    lines[1] = canonical_bytes(second).decode()
    store.path.write_text("\n".join(lines) + "\n")

    with pytest.raises(RegistryVerificationError, match="hash"):
        store.verify()


def test_reusing_object_id_for_different_bytes_fails_verification(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    store.append(
        actor_role="proposer",
        actor_id="agent:1",
        object_payload={"kind": "sense", "version": 1},
        event_type=LifecycleState.DRAFT,
        event_payload={},
    )
    line = json.loads(store.path.read_text())
    line["object_payload_json"] = canonical_bytes(
        {"kind": "sense", "version": 2}
    ).decode()
    store.path.write_bytes(canonical_bytes(line) + b"\n")

    with pytest.raises(RegistryVerificationError, match="object ID"):
        store.verify()


def test_store_surface_has_no_update_or_delete_path(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    assert callable(store.append)
    assert callable(store.verify)
    assert not hasattr(store, "update")
    assert not hasattr(store, "delete")


@pytest.mark.parametrize("hostile_field", ("object_payload", "event_payload"))
def test_append_rejects_mapping_subclasses_without_invoking_them(
    tmp_path: Path, hostile_field: str
) -> None:
    class HostileDict(dict[str, Any]):
        calls = 0

        def __iter__(self) -> Any:
            self.calls += 1
            raise RuntimeError("must not execute")

    hostile = HostileDict(kind="sense")
    arguments: dict[str, Any] = {
        "actor_role": "proposer",
        "actor_id": "agent:1",
        "object_payload": {"kind": "sense"},
        "event_type": LifecycleState.DRAFT,
        "event_payload": {},
    }
    arguments[hostile_field] = hostile
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())

    with pytest.raises(TypeError, match="plain JSON"):
        store.append(**arguments)

    assert hostile.calls == 0
    assert not store.path.exists()


def test_writer_lock_serializes_independent_store_instances(tmp_path: Path) -> None:
    path = tmp_path / "registry.jsonl"
    first = RegistryStore(path, clock=fixed_clock())
    second = RegistryStore(path, clock=fixed_clock())

    with ThreadPoolExecutor(max_workers=1) as executor:
        with first._registry_lock(exclusive=True):
            future = executor.submit(
                second.append,
                actor_role="proposer",
                actor_id="agent:2",
                object_payload={"kind": "sense", "version": 2},
                event_type=LifecycleState.DRAFT,
                event_payload={},
            )
            time.sleep(0.05)
            assert not future.done()

        assert future.result().sequence == 0
    assert len(first.verify()) == 1


def test_serialized_store_instances_accept_anchored_heads_as_ancestors(
    tmp_path: Path,
) -> None:
    path = tmp_path / "registry.jsonl"
    first = RegistryStore(path, clock=fixed_clock())
    second = RegistryStore(path, clock=fixed_clock())
    first.append(
        actor_role="proposer",
        actor_id="agent:1",
        object_payload={"kind": "sense", "version": 1},
        event_type=LifecycleState.DRAFT,
        event_payload={},
    )
    second.append(
        actor_role="proposer",
        actor_id="agent:2",
        object_payload={"kind": "sense", "version": 2},
        event_type=LifecycleState.DRAFT,
        event_payload={},
    )

    assert len(first.verify()) == 2
    third = first.append(
        actor_role="proposer",
        actor_id="agent:3",
        object_payload={"kind": "sense", "version": 3},
        event_type=LifecycleState.DRAFT,
        event_payload={},
    )
    assert third.sequence == 2


def test_suffix_rollback_is_detected_by_head_checkpoint(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    append_path(store, {"kind": "sense", "version": 1})
    lines = store.path.read_text().splitlines()
    store.path.write_text("\n".join(lines[:-1]) + "\n")

    with pytest.raises(RegistryVerificationError, match="head checkpoint"):
        store.verify()


def test_external_expected_head_detects_registry_and_checkpoint_rollback(
    tmp_path: Path,
) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    events = append_path(store, {"kind": "sense", "version": 1})
    trusted_head = events[-1].event_content_id
    lines = store.path.read_text().splitlines()
    first = events[0]
    store.path.write_text(lines[0] + "\n")
    store.checkpoint_path.write_bytes(
        canonical_bytes(
            {"sequence": first.sequence, "event_content_id": first.event_content_id}
        )
    )

    externally_anchored = RegistryStore(store.path, expected_head=trusted_head)
    with pytest.raises(RegistryVerificationError, match="trusted expected head"):
        externally_anchored.verify()


def test_external_expected_head_rejects_complete_history_deletion(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    event = store.append(
        actor_role="proposer",
        actor_id="agent:1",
        object_payload={"kind": "sense"},
        event_type=LifecycleState.DRAFT,
        event_payload={},
    )
    store.path.unlink()
    store.checkpoint_path.unlink()

    anchored = RegistryStore(store.path, expected_head=event.event_content_id)
    with pytest.raises(RegistryVerificationError, match="trusted expected head"):
        anchored.verify()


def test_interrupted_checkpoint_commit_recovers_from_valid_registry_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    replace = store._replace_atomically

    def fail_checkpoint(target: Path, data: bytes) -> None:
        if target == store.checkpoint_path:
            raise OSError("simulated checkpoint failure")
        replace(target, data)

    monkeypatch.setattr(store, "_replace_atomically", fail_checkpoint)
    with pytest.raises(OSError, match="simulated checkpoint failure"):
        store.append(
            actor_role="proposer",
            actor_id="agent:1",
            object_payload={"kind": "sense"},
            event_type=LifecycleState.DRAFT,
            event_payload={},
        )
    monkeypatch.setattr(store, "_replace_atomically", replace)

    assert len(store.verify()) == 1
    assert store.checkpoint_path.exists()


def test_supersession_requires_reciprocal_lineage(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    old_payload = {"kind": "sense", "version": 1}
    new_payload = {"kind": "unrelated", "version": 1}
    append_path(store, old_payload)
    successor = store.append(
        actor_role="proposer",
        actor_id="agent:3",
        object_payload=new_payload,
        event_type=LifecycleState.DRAFT,
        event_payload={},
    )

    with pytest.raises(RegistryVerificationError, match="reciprocal"):
        store.append(
            actor_role="authorizer",
            actor_id="agent:4",
            object_payload=old_payload,
            event_type=LifecycleState.SUPERSEDED,
            event_payload={"successor_object_id": successor.object_id},
        )


def test_withdrawn_object_cannot_become_official_successor(
    tmp_path: Path,
) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    old_payload = {"kind": "sense", "version": 1}
    new_payload = {"kind": "sense", "version": 2}
    append_path(store, old_payload)
    successor = store.append(
        actor_role="proposer",
        actor_id="agent:2",
        object_payload=new_payload,
        event_type=LifecycleState.DRAFT,
        event_payload={"supersedes": content_id(old_payload)},
    )
    store.append(
        actor_role="proposer",
        actor_id="agent:2",
        object_payload=new_payload,
        event_type=LifecycleState.WITHDRAWN,
        event_payload={},
    )

    with pytest.raises(RegistryVerificationError, match="eligible"):
        store.append(
            actor_role="authorizer",
            actor_id="agent:3",
            object_payload=old_payload,
            event_type=LifecycleState.SUPERSEDED,
            event_payload={"successor_object_id": successor.object_id},
        )


def test_official_successor_can_later_record_failure_terminal(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    old_payload = {"kind": "sense", "version": 1}
    new_payload = {"kind": "sense", "version": 2}
    append_path(store, old_payload)
    successor = store.append(
        actor_role="proposer",
        actor_id="agent:2",
        object_payload=new_payload,
        event_type=LifecycleState.DRAFT,
        event_payload={"supersedes": content_id(old_payload)},
    )
    store.append(
        actor_role="authorizer",
        actor_id="agent:3",
        object_payload=old_payload,
        event_type=LifecycleState.SUPERSEDED,
        event_payload={"successor_object_id": successor.object_id},
    )

    for state in (
        LifecycleState.SUBMITTED,
        LifecycleState.CONTRACT_BOUND,
        LifecycleState.VALIDATION_PENDING,
    ):
        store.append(
            actor_role="validator",
            actor_id="agent:2",
            object_payload=new_payload,
            event_type=state,
            event_payload={},
        )
    failure = store.append(
        actor_role="validator",
        actor_id="agent:2",
        object_payload=new_payload,
        event_type=LifecycleState.GROUNDING_CONFLICT,
        event_payload={"failures": ["instrument did not replicate"]},
    )

    assert store.verify()[-1] == failure
    assert "instrument did not replicate" in failure.payload_json


def test_multi_generation_supersession_lineage_is_valid(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    first_payload = {"kind": "sense", "version": 1}
    second_payload = {"kind": "sense", "version": 2}
    third_payload = {"kind": "sense", "version": 3}
    append_path(store, first_payload)
    second = store.append(
        actor_role="proposer",
        actor_id="agent:2",
        object_payload=second_payload,
        event_type=LifecycleState.DRAFT,
        event_payload={"supersedes": content_id(first_payload)},
    )
    store.append(
        actor_role="authorizer",
        actor_id="agent:3",
        object_payload=first_payload,
        event_type=LifecycleState.SUPERSEDED,
        event_payload={"successor_object_id": second.object_id},
    )
    for state in (
        LifecycleState.SUBMITTED,
        LifecycleState.CONTRACT_BOUND,
        LifecycleState.VALIDATION_PENDING,
        LifecycleState.PROVISIONAL,
    ):
        store.append(
            actor_role="validator",
            actor_id="agent:4",
            object_payload=second_payload,
            event_type=state,
            event_payload={},
        )
    third = store.append(
        actor_role="proposer",
        actor_id="agent:5",
        object_payload=third_payload,
        event_type=LifecycleState.DRAFT,
        event_payload={"supersedes": second.object_id},
    )

    store.append(
        actor_role="authorizer",
        actor_id="agent:6",
        object_payload=second_payload,
        event_type=LifecycleState.SUPERSEDED,
        event_payload={"successor_object_id": third.object_id},
    )

    assert len(store.verify()) == 13


def test_official_successor_may_eventually_expire(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    first_payload = {"kind": "sense", "version": 1}
    second_payload = {"kind": "sense", "version": 2}
    append_path(store, first_payload)
    second = store.append(
        actor_role="proposer",
        actor_id="agent:2",
        object_payload=second_payload,
        event_type=LifecycleState.DRAFT,
        event_payload={"supersedes": content_id(first_payload)},
    )
    store.append(
        actor_role="authorizer",
        actor_id="agent:3",
        object_payload=first_payload,
        event_type=LifecycleState.SUPERSEDED,
        event_payload={"successor_object_id": second.object_id},
    )
    for state in (
        LifecycleState.SUBMITTED,
        LifecycleState.CONTRACT_BOUND,
        LifecycleState.VALIDATION_PENDING,
        LifecycleState.PROVISIONAL,
        LifecycleState.EXPIRED,
    ):
        store.append(
            actor_role="validator",
            actor_id="agent:4",
            object_payload=second_payload,
            event_type=state,
            event_payload={},
        )

    assert store.verify()[-1].event_type is LifecycleState.EXPIRED


def test_revision_cannot_declare_unknown_or_cyclic_predecessor(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    unknown_id = "sha256:" + "f" * 64

    with pytest.raises(RegistryVerificationError, match="predecessor"):
        store.append(
            actor_role="proposer",
            actor_id="agent:1",
            object_payload={"kind": "sense", "version": 2},
            event_type=LifecycleState.DRAFT,
            event_payload={"supersedes": unknown_id},
        )


def test_deep_hostile_json_returns_registry_verification_error(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.jsonl", clock=fixed_clock())
    event = store.append(
        actor_role="proposer",
        actor_id="agent:1",
        object_payload={"kind": "sense"},
        event_type=LifecycleState.DRAFT,
        event_payload={},
    )
    line = json.loads(store.path.read_text())
    line["payload_json"] = "[" * 2_000 + "0" + "]" * 2_000
    identity = {key: value for key, value in line.items() if key != "event_content_id"}
    line["event_content_id"] = content_id(identity)
    store.path.write_bytes(canonical_bytes(line) + b"\n")
    assert event.event_content_id

    with pytest.raises(RegistryVerificationError):
        store.verify()
