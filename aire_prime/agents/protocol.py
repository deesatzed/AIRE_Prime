import json
import re
from enum import StrEnum
from typing import Any, Self

from pydantic import computed_field, field_validator, model_validator

from aire_prime.agents.roles import AgentIdentity, Role
from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.core.model import FrozenModel
from aire_prime.objects import ContentID


class MessageKind(StrEnum):
    REALIZE_REQUEST = "realize_request"
    VALIDATE_REQUEST = "validate_request"
    ADVERSARY_REQUEST = "adversary_request"
    AUTHORIZE_REQUEST = "authorize_request"
    RESPONSE = "response"
    FAILURE = "failure"


class ProtocolFailureCode(StrEnum):
    TIMEOUT = "Timeout"
    MALFORMED_JSON = "MalformedJSON"
    EXCESS_INPUT = "ExcessInput"
    EXCESS_OUTPUT = "ExcessOutput"
    NONZERO_EXIT = "NonzeroExit"
    ROLE_CONFLICT = "RoleConflict"
    UNDECLARED_FILE_ACCESS = "UndeclaredFileAccess"
    PROTOCOL_VIOLATION = "ProtocolViolation"
    EXECUTION_ERROR = "ExecutionError"


class ProtocolFailure(FrozenModel):
    code: ProtocolFailureCode
    detail_content_id: ContentID | None = None


class DeclaredInput(FrozenModel):
    name: str
    content_id: ContentID

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        if re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", value) is None:
            raise ValueError("declared input name must be a bounded machine identifier")
        return value


class ProtocolEnvelope(FrozenModel):
    schema_version: str = "0.1.0"
    message_kind: MessageKind

    @field_validator("schema_version")
    @classmethod
    def require_schema_version(cls, value: str) -> str:
        if value != "0.1.0":
            raise ValueError("unsupported protocol schema version")
        return value

    def identity_payload(self) -> dict[str, Any]:
        return self.model_dump(
            mode="python",
            exclude={"content_id"},
            exclude_computed_fields=True,
        )

    @computed_field(return_type=str)  # type: ignore[prop-decorator]
    @property
    def content_id(self) -> str:
        return content_id(self.identity_payload())

    def to_jsonl(self) -> bytes:
        payload = self.identity_payload()
        payload["content_id"] = self.content_id
        return canonical_bytes(payload) + b"\n"

    @classmethod
    def from_jsonl(cls, data: bytes) -> Self:
        if not data.endswith(b"\n") or data.count(b"\n") != 1:
            raise ValueError("protocol envelope must be exactly one JSONL line")
        try:
            payload = json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as error:
            raise ValueError("protocol envelope contains malformed JSON") from error
        if type(payload) is not dict:
            raise ValueError("protocol envelope must contain a JSON object")
        transmitted_id = payload.pop("content_id", None)
        instance = cls.model_validate(payload)
        if transmitted_id != instance.content_id:
            raise ValueError("protocol envelope content ID does not match bytes")
        if instance.to_jsonl() != data:
            raise ValueError("protocol envelope is not canonical JSONL")
        return instance


def _normalize_content_ids(value: tuple[str, ...], *, name: str) -> tuple[str, ...]:
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must not contain duplicates")
    return tuple(sorted(value))


class AgentRequest(ProtocolEnvelope):
    sender: AgentIdentity
    receiver: AgentIdentity
    claim_id: ContentID
    object_ids: tuple[ContentID, ...] = ()
    content_ids: tuple[ContentID, ...] = ()
    declared_inputs: tuple[DeclaredInput, ...] = ()
    receipt_content_ids: tuple[ContentID, ...] = ()

    @field_validator("object_ids")
    @classmethod
    def normalize_object_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_content_ids(value, name="object_ids")

    @field_validator("content_ids", "receipt_content_ids")
    @classmethod
    def normalize_content_references(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_content_ids(value, name="content_ids")

    @field_validator("declared_inputs")
    @classmethod
    def normalize_declared_inputs(
        cls, value: tuple[DeclaredInput, ...]
    ) -> tuple[DeclaredInput, ...]:
        names = [item.name for item in value]
        if len(names) != len(set(names)):
            raise ValueError("declared input names must be unique")
        return tuple(sorted(value, key=lambda item: item.name))

    @model_validator(mode="after")
    def require_request_roles(self) -> Self:
        allowed = {
            MessageKind.REALIZE_REQUEST: Role.RECEIVER,
            MessageKind.VALIDATE_REQUEST: Role.VALIDATOR,
            MessageKind.ADVERSARY_REQUEST: Role.ADVERSARY,
            MessageKind.AUTHORIZE_REQUEST: Role.AUTHORIZER,
        }
        expected_receiver = allowed.get(self.message_kind)
        if expected_receiver is None:
            raise ValueError("request uses a non-request message kind")
        if self.receiver.role is not expected_receiver:
            raise ValueError("request message kind does not match receiver role")
        if self.sender.agent_id == self.receiver.agent_id:
            raise ValueError("request sender and receiver identities must be independent")
        return self


class AgentResponse(ProtocolEnvelope):
    request_content_id: ContentID
    sender: AgentIdentity
    receiver: AgentIdentity
    object_ids: tuple[ContentID, ...] = ()
    content_ids: tuple[ContentID, ...] = ()
    receipt_content_ids: tuple[ContentID, ...] = ()
    failures: tuple[ProtocolFailure, ...] = ()

    @field_validator("object_ids")
    @classmethod
    def normalize_object_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_content_ids(value, name="object_ids")

    @field_validator("content_ids", "receipt_content_ids")
    @classmethod
    def normalize_content_references(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_content_ids(value, name="content_ids")

    @model_validator(mode="after")
    def require_response_kind(self) -> Self:
        if self.message_kind is MessageKind.RESPONSE and self.failures:
            raise ValueError("successful response cannot contain failures")
        if self.message_kind is MessageKind.FAILURE and not self.failures:
            raise ValueError("failure response requires failures")
        if self.message_kind not in {MessageKind.RESPONSE, MessageKind.FAILURE}:
            raise ValueError("response uses a non-response message kind")
        if self.sender.agent_id == self.receiver.agent_id:
            raise ValueError("response sender and receiver identities must be independent")
        return self


def parse_envelope_jsonl(data: bytes) -> AgentRequest | AgentResponse:
    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as error:
        raise ValueError("protocol envelope contains malformed JSON") from error
    if type(payload) is not dict:
        raise ValueError("protocol envelope must contain a JSON object")
    kind = payload.get("message_kind")
    request_kinds = {
        item.value
        for item in (
            MessageKind.REALIZE_REQUEST,
            MessageKind.VALIDATE_REQUEST,
            MessageKind.ADVERSARY_REQUEST,
            MessageKind.AUTHORIZE_REQUEST,
        )
    }
    if kind in request_kinds:
        return AgentRequest.from_jsonl(data)
    if kind in {MessageKind.RESPONSE.value, MessageKind.FAILURE.value}:
        return AgentResponse.from_jsonl(data)
    raise ValueError("protocol envelope has an unknown message kind")
