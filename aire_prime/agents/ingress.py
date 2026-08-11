import hashlib
import json
from typing import Any, Self

from pydantic import computed_field, model_validator

from aire_prime.agents.protocol import (
    AgentRequest,
    AgentResponse,
    ProtocolFailure,
    ProtocolFailureCode,
    parse_envelope_jsonl,
)
from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.objects import ContentID
from aire_prime.registry.events import RegistryEvent
from aire_prime.registry.lifecycle import LifecycleState
from aire_prime.registry.store import RegistryStore


class IngressRejection(FrozenModel):
    wire_content_id: ContentID
    failure: ProtocolFailure

    @computed_field(return_type=str)  # type: ignore[prop-decorator]
    @property
    def content_id(self) -> str:
        return content_id(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return self.model_dump(
            mode="json",
            exclude={"content_id"},
            exclude_computed_fields=True,
        )


class IngressResult(FrozenModel):
    envelope: AgentRequest | AgentResponse | None = None
    rejection: IngressRejection | None = None
    registry_event_id: ContentID | None = None

    @model_validator(mode="after")
    def require_exact_outcome(self) -> Self:
        if (self.envelope is None) == (self.rejection is None):
            raise ValueError("ingress result requires exactly one envelope or rejection")
        if (self.rejection is None) != (self.registry_event_id is None):
            raise ValueError("only ingress rejection carries registry evidence")
        return self


def _wire_content_id(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def record_ingress_rejection(
    data: bytes,
    failure_code: ProtocolFailureCode,
    *,
    registry: RegistryStore,
    actor_role: str,
    actor_id: str,
) -> IngressResult:
    """Durably record a typed rejection without retaining adversary-controlled bytes."""
    wire_id = _wire_content_id(data)
    rejection = IngressRejection(
        wire_content_id=wire_id,
        failure=ProtocolFailure(
            code=failure_code,
            detail_content_id=content_id({"failure_code": failure_code.value}),
        ),
    )
    event: RegistryEvent = registry.append(
        actor_role=actor_role,
        actor_id=actor_id,
        object_payload=rejection.identity_payload(),
        event_type=LifecycleState.DRAFT,
        event_payload={
            "failure_code": failure_code.value,
            "wire_content_id": wire_id,
        },
    )
    return IngressResult(rejection=rejection, registry_event_id=event.event_content_id)


def ingest_envelope_jsonl(
    data: bytes,
    *,
    registry: RegistryStore,
    actor_role: str,
    actor_id: str,
    max_input_bytes: int = 65_536,
) -> IngressResult:
    """Parse untrusted JSONL or durably record a typed, content-addressed rejection."""
    failure_code: ProtocolFailureCode | None = None
    if len(data) > max_input_bytes:
        failure_code = ProtocolFailureCode.EXCESS_INPUT
    else:
        try:
            envelope = parse_envelope_jsonl(data)
        except (UnicodeDecodeError, ValueError, RecursionError):
            try:
                json.loads(data)
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                failure_code = ProtocolFailureCode.MALFORMED_JSON
            else:
                failure_code = ProtocolFailureCode.PROTOCOL_VIOLATION
        else:
            return IngressResult(envelope=envelope)

    if failure_code is None:
        raise AssertionError("ingress rejection requires a failure code")
    return record_ingress_rejection(
        data,
        failure_code,
        registry=registry,
        actor_role=actor_role,
        actor_id=actor_id,
    )
