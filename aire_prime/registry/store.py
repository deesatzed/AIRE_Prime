import fcntl
import json
import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.registry.events import GENESIS_EVENT_HASH, RegistryEvent, canonical_json_text
from aire_prime.registry.lifecycle import (
    InvalidLifecycleTransition,
    LifecycleState,
    require_transition,
)


class RegistryVerificationError(ValueError):
    pass


ELIGIBLE_SUCCESSOR_STATES = frozenset(
    {
        LifecycleState.DRAFT,
        LifecycleState.SUBMITTED,
        LifecycleState.CONTRACT_BOUND,
        LifecycleState.VALIDATION_PENDING,
        LifecycleState.PROVISIONAL,
        LifecycleState.RESTRICTED,
        LifecycleState.REPLICATED,
    }
)
class RegistryStore:
    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        expected_head: str | None = None,
    ) -> None:
        self.path = path
        self.checkpoint_path = path.with_name(f"{path.name}.head")
        self.lock_path = path.with_name(f"{path.name}.lock")
        self._clock = clock or (lambda: datetime.now(UTC))
        self._expected_head = expected_head

    def append(
        self,
        *,
        actor_role: str,
        actor_id: str,
        object_payload: dict[str, Any],
        event_type: LifecycleState,
        event_payload: dict[str, Any],
    ) -> RegistryEvent:
        object_payload_json = canonical_json_text(object_payload)
        canonical_json_text(event_payload)
        with self._registry_lock(exclusive=True):
            events = self._verify_unlocked()
            object_id = content_id(object_payload)
            object_events = tuple(event for event in events if event.object_id == object_id)
            if not object_events:
                if event_type is not LifecycleState.DRAFT:
                    raise InvalidLifecycleTransition(
                        f"new registry object must begin at {LifecycleState.DRAFT.value}"
                    )
                self._require_known_predecessor(object_id, event_payload, events)
            else:
                require_transition(object_events[-1].event_type, event_type)
                if object_events[-1].object_payload_json != object_payload_json:
                    raise RegistryVerificationError(
                        "object ID reused for different object bytes"
                    )
            if event_type is LifecycleState.SUPERSEDED:
                self._require_reciprocal_successor(object_id, event_payload, events)

            previous_hash = events[-1].event_content_id if events else GENESIS_EVENT_HASH
            event = RegistryEvent.create(
                sequence=len(events),
                timestamp=self._clock(),
                actor_role=actor_role,
                actor_id=actor_id,
                object_payload=object_payload,
                event_type=event_type,
                previous_event_hash=previous_hash,
                event_payload=event_payload,
            )
            old_bytes = self.path.read_bytes() if self.path.exists() else b""
            new_line = canonical_bytes(event.model_dump(mode="python")) + b"\n"
            self._replace_atomically(self.path, old_bytes + new_line)
            self._write_checkpoint(event)
            if self._expected_head is None:
                self._expected_head = event.event_content_id
            return event

    def verify(self) -> tuple[RegistryEvent, ...]:
        # Verification may repair a stale/missing checkpoint left by a crash
        # after the registry event was durably replaced.
        with self._registry_lock(exclusive=True):
            return self._verify_unlocked()

    def _verify_unlocked(self) -> tuple[RegistryEvent, ...]:
        if not self.path.exists():
            if self._expected_head is not None:
                raise RegistryVerificationError(
                    "registry does not contain the trusted expected head"
                )
            if self.checkpoint_path.exists():
                raise RegistryVerificationError("registry head checkpoint has no registry")
            return ()
        if self.path.is_symlink():
            raise RegistryVerificationError("registry path must not be a symbolic link")
        raw = self.path.read_bytes()
        if not raw:
            if self._expected_head is not None:
                raise RegistryVerificationError(
                    "registry does not contain the trusted expected head"
                )
            if self.checkpoint_path.exists():
                raise RegistryVerificationError("registry head checkpoint has no events")
            return ()
        if not raw.endswith(b"\n"):
            raise RegistryVerificationError("registry JSONL must end with a newline")

        events: list[RegistryEvent] = []
        previous_hash = GENESIS_EVENT_HASH
        histories: dict[str, list[RegistryEvent]] = {}
        try:
            for sequence, raw_line in enumerate(raw.splitlines()):
                event = RegistryEvent.model_validate_json(raw_line)
                canonical_line = canonical_bytes(event.model_dump(mode="python"))
                if raw_line != canonical_line:
                    raise RegistryVerificationError("registry line is not canonical JSON")
                if event.sequence != sequence:
                    raise RegistryVerificationError("registry event sequence is invalid")
                if event.previous_event_hash != previous_hash:
                    raise RegistryVerificationError("registry event hash chain is broken")
                object_history = histories.setdefault(event.object_id, [])
                if not object_history:
                    if event.event_type is not LifecycleState.DRAFT:
                        raise RegistryVerificationError(
                            "registered object does not begin at Draft"
                        )
                    payload = event.decoded_payload()
                    if type(payload) is not dict:
                        raise RegistryVerificationError(
                            "Draft event payload must be an object"
                        )
                    self._require_known_predecessor(event.object_id, payload, events)
                else:
                    if event.object_payload_json != object_history[0].object_payload_json:
                        raise RegistryVerificationError(
                            "object ID reused for different object bytes"
                        )
                    require_transition(object_history[-1].event_type, event.event_type)
                object_history.append(event)
                events.append(event)
                previous_hash = event.event_content_id
        except RegistryVerificationError:
            raise
        except (
            InvalidLifecycleTransition,
            UnicodeDecodeError,
            ValidationError,
            ValueError,
            RecursionError,
        ) as error:
            raise RegistryVerificationError(f"registry verification failed: {error}") from error

        known_ids = set(histories)
        for event in events:
            if event.event_type is LifecycleState.SUPERSEDED:
                payload = event.decoded_payload()
                if type(payload) is not dict:
                    raise RegistryVerificationError(
                        "Superseded event payload must be an object"
                    )
                successor_id = payload.get("successor_object_id")
                if successor_id == event.object_id or successor_id not in known_ids:
                    raise RegistryVerificationError("registry supersession link is invalid")
                successor_events = histories[successor_id]
                successor_payload = successor_events[0].decoded_payload()
                if (
                    type(successor_payload) is not dict
                    or successor_payload.get("supersedes") != event.object_id
                ):
                    raise RegistryVerificationError(
                        "registry supersession lacks reciprocal lineage"
                    )
                successor_events_at_link = tuple(
                    successor
                    for successor in successor_events
                    if successor.sequence < event.sequence
                )
                if (
                    not successor_events_at_link
                    or successor_events_at_link[-1].event_type
                    not in ELIGIBLE_SUCCESSOR_STATES
                ):
                    raise RegistryVerificationError(
                        "registry supersession successor was not eligible at authorization"
                    )
        self._verify_checkpoint(events)
        return tuple(events)

    @staticmethod
    def _require_known_predecessor(
        object_id: str,
        event_payload: dict[str, Any],
        events: tuple[RegistryEvent, ...] | list[RegistryEvent],
    ) -> None:
        predecessor_id = event_payload.get("supersedes")
        if predecessor_id is None:
            return
        known_ids = {event.object_id for event in events}
        if (
            type(predecessor_id) is not str
            or predecessor_id == object_id
            or predecessor_id not in known_ids
        ):
            raise RegistryVerificationError(
                "revision supersedes an unknown or cyclic predecessor"
            )

    @staticmethod
    def _require_reciprocal_successor(
        object_id: str,
        event_payload: dict[str, Any],
        events: tuple[RegistryEvent, ...],
    ) -> None:
        successor_id = event_payload.get("successor_object_id")
        if type(successor_id) is not str or successor_id == object_id:
            raise RegistryVerificationError(
                "supersession requires a distinct successor_object_id"
            )
        successor_events = tuple(event for event in events if event.object_id == successor_id)
        if not successor_events:
            raise RegistryVerificationError(
                "supersession successor must already exist in the registry"
            )
        successor_payload = successor_events[0].decoded_payload()
        if (
            type(successor_payload) is not dict
            or successor_payload.get("supersedes") != object_id
        ):
            raise RegistryVerificationError("supersession lacks reciprocal lineage")
        if successor_events[-1].event_type not in ELIGIBLE_SUCCESSOR_STATES:
            raise RegistryVerificationError("supersession successor is not eligible")

    def _verify_checkpoint(self, events: list[RegistryEvent]) -> None:
        if not events:
            if self.checkpoint_path.exists():
                raise RegistryVerificationError("registry head checkpoint has no events")
            return
        event_ids = {event.event_content_id for event in events}
        if self._expected_head is not None and self._expected_head not in event_ids:
            raise RegistryVerificationError(
                "registry does not contain the trusted expected head"
            )
        if not self.checkpoint_path.exists():
            self._write_checkpoint(events[-1])
            return
        try:
            raw = self.checkpoint_path.read_bytes()
            payload = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RegistryVerificationError("registry head checkpoint is malformed") from error
        expected = {
            "sequence": events[-1].sequence,
            "event_content_id": events[-1].event_content_id,
        }
        if type(payload) is not dict or raw != canonical_bytes(payload):
            raise RegistryVerificationError("registry head checkpoint does not match history")
        if payload == expected:
            return
        checkpoint_id = payload.get("event_content_id")
        checkpoint_sequence = payload.get("sequence")
        if (
            type(checkpoint_sequence) is int
            and 0 <= checkpoint_sequence < len(events)
            and events[checkpoint_sequence].event_content_id == checkpoint_id
        ):
            self._write_checkpoint(events[-1])
            return
        raise RegistryVerificationError("registry head checkpoint does not match history")

    def _write_checkpoint(self, event: RegistryEvent) -> None:
        payload = {
            "sequence": event.sequence,
            "event_content_id": event.event_content_id,
        }
        self._replace_atomically(self.checkpoint_path, canonical_bytes(payload))

    @contextmanager
    def _registry_lock(self, *, exclusive: bool) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+b") as lock_file:
            operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(lock_file.fileno(), operation)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _replace_atomically(self, target: Path, data: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, prefix=f".{target.name}.", delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(data)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, target)
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
