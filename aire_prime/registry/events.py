import json
import math
from datetime import datetime
from typing import Any, Self, cast

from pydantic import Field, field_validator, model_validator

from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel
from aire_prime.objects import ContentID
from aire_prime.registry.lifecycle import LifecycleState

GENESIS_EVENT_HASH = "sha256:" + "0" * 64


def _require_plain_json(value: object) -> None:
    stack: list[tuple[object, int]] = [(value, 0)]
    visited = 0
    while stack:
        current, depth = stack.pop()
        visited += 1
        if visited > 100_000:
            raise ValueError("registry payload exceeds the node limit")
        if depth > 100:
            raise ValueError("registry payload exceeds the nesting limit")
        if type(current) is dict:
            mapping = cast(dict[object, object], current)
            if any(type(key) is not str for key in mapping):
                raise TypeError("registry payload keys must be exact strings")
            stack.extend((item, depth + 1) for item in mapping.values())
            continue
        if type(current) in {list, tuple}:
            sequence = cast(list[object] | tuple[object, ...], current)
            stack.extend((item, depth + 1) for item in sequence)
            continue
        if type(current) is float and not math.isfinite(current):
            raise ValueError("registry payload numbers must be finite")
        if current is None or type(current) in {str, int, float, bool}:
            continue
        raise TypeError("registry payloads must contain only plain JSON values")


def canonical_json_text(value: object) -> str:
    _require_plain_json(value)
    return canonical_bytes(value).decode("utf-8")


class RegistryEvent(FrozenModel):
    sequence: int = Field(ge=0)
    timestamp: datetime
    actor_role: str
    actor_id: str
    object_id: ContentID
    event_type: LifecycleState
    previous_event_hash: ContentID
    object_payload_json: str
    payload_json: str
    payload_content_id: ContentID
    event_content_id: ContentID

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("registry event timestamp must include a timezone")
        return value

    @field_validator("actor_role", "actor_id")
    @classmethod
    def require_attribution(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("registry actor attribution must be nonblank")
        return value

    @model_validator(mode="after")
    def verify_content_ids(self) -> Self:
        try:
            object_payload = json.loads(self.object_payload_json)
            payload = json.loads(self.payload_json)
        except (json.JSONDecodeError, TypeError) as error:
            raise ValueError("registry event contains malformed payload JSON") from error
        if canonical_json_text(object_payload) != self.object_payload_json:
            raise ValueError("registry object payload JSON is not canonical")
        if canonical_json_text(payload) != self.payload_json:
            raise ValueError("registry event payload JSON is not canonical")
        if content_id(object_payload) != self.object_id:
            raise ValueError("registry object ID does not match object bytes")
        if content_id(payload) != self.payload_content_id:
            raise ValueError("registry payload content ID does not match payload bytes")
        if content_id(self.identity_payload()) != self.event_content_id:
            raise ValueError("registry event content ID does not match event bytes")
        return self

    def identity_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="python", exclude={"event_content_id"})

    def decoded_payload(self) -> Any:
        return json.loads(self.payload_json)

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        timestamp: datetime,
        actor_role: str,
        actor_id: str,
        object_payload: dict[str, Any],
        event_type: LifecycleState,
        previous_event_hash: str,
        event_payload: dict[str, Any],
    ) -> Self:
        object_payload_json = canonical_json_text(object_payload)
        payload_json = canonical_json_text(event_payload)
        identity: dict[str, Any] = {
            "sequence": sequence,
            "timestamp": timestamp,
            "actor_role": actor_role,
            "actor_id": actor_id,
            "object_id": content_id(object_payload),
            "event_type": event_type,
            "previous_event_hash": previous_event_hash,
            "object_payload_json": object_payload_json,
            "payload_json": payload_json,
            "payload_content_id": content_id(event_payload),
        }
        return cls(**identity, event_content_id=content_id(identity))
