import json

import pytest
from pydantic import ValidationError

from aire_prime.agents.protocol import (
    AgentRequest,
    AgentResponse,
    DeclaredInput,
    MessageKind,
    parse_envelope_jsonl,
)
from aire_prime.agents.roles import AgentIdentity, ClaimRoleAssignments, Role

CLAIM_ID = "sha256:" + "1" * 64
OBJECT_ID = "sha256:" + "2" * 64
INPUT_ID = "sha256:" + "3" * 64


def identity(role: Role, suffix: str) -> AgentIdentity:
    return AgentIdentity(agent_id=f"agent:{suffix}", role=role)


def request() -> AgentRequest:
    return AgentRequest(
        message_kind=MessageKind.VALIDATE_REQUEST,
        sender=identity(Role.PROPOSER, "proposer"),
        receiver=identity(Role.VALIDATOR, "validator"),
        claim_id=CLAIM_ID,
        object_ids=(OBJECT_ID,),
        content_ids=(INPUT_ID,),
        declared_inputs=(DeclaredInput(name="observations", content_id=INPUT_ID),),
    )


def test_governance_roles_require_independent_identities() -> None:
    proposer = identity(Role.PROPOSER, "same")
    payload = {
        "claim_id": CLAIM_ID,
        "proposer": proposer,
        "receiver": identity(Role.RECEIVER, "receiver"),
        "validator": AgentIdentity(agent_id="agent:same", role=Role.VALIDATOR),
        "adversary": identity(Role.ADVERSARY, "adversary"),
        "authorizer": AgentIdentity(agent_id="agent:same", role=Role.AUTHORIZER),
    }

    with pytest.raises(ValidationError, match="independent"):
        ClaimRoleAssignments.model_validate(payload)


def test_complete_role_assignment_is_valid_and_immutable() -> None:
    assignments = ClaimRoleAssignments(
        claim_id=CLAIM_ID,
        proposer=identity(Role.PROPOSER, "proposer"),
        receiver=identity(Role.RECEIVER, "receiver"),
        validator=identity(Role.VALIDATOR, "validator"),
        adversary=identity(Role.ADVERSARY, "adversary"),
        authorizer=identity(Role.AUTHORIZER, "authorizer"),
    )
    assert len({agent.agent_id for agent in assignments.agents}) == 5
    with pytest.raises(ValidationError):
        assignments.validator = identity(Role.VALIDATOR, "replacement")


@pytest.mark.parametrize("hidden_field", ("hidden_context", "proposer_notes", "prompt"))
def test_validator_request_rejects_hidden_or_proposer_only_fields(hidden_field: str) -> None:
    payload = request().identity_payload()
    payload[hidden_field] = "not permitted"

    with pytest.raises(ValidationError, match="Extra inputs"):
        AgentRequest.model_validate(payload)


def test_request_jsonl_round_trip_is_canonical_and_deterministic() -> None:
    original = request()

    wire = original.to_jsonl()
    restored = AgentRequest.from_jsonl(wire)

    assert wire.endswith(b"\n")
    assert restored == original
    assert restored.to_jsonl() == wire
    assert parse_envelope_jsonl(wire) == original


def test_protocol_rejects_unknown_message_kind() -> None:
    payload = request().model_dump(mode="json")
    payload["message_kind"] = "secret_request"
    wire = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode() + b"\n"

    with pytest.raises(ValueError, match="message kind"):
        parse_envelope_jsonl(wire)


def test_tampered_message_content_id_is_rejected() -> None:
    payload = json.loads(request().to_jsonl())
    payload["claim_id"] = "sha256:" + "4" * 64
    wire = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode() + b"\n"

    with pytest.raises(ValueError, match="content ID"):
        AgentRequest.from_jsonl(wire)


def test_message_kind_must_match_receiver_role() -> None:
    payload = request().identity_payload()
    payload["receiver"] = identity(Role.ADVERSARY, "adversary")

    with pytest.raises(ValidationError, match="receiver role"):
        AgentRequest.model_validate(payload)


def test_response_requires_request_reference_and_matching_kind() -> None:
    response = AgentResponse(
        message_kind=MessageKind.RESPONSE,
        request_content_id=request().content_id,
        sender=identity(Role.VALIDATOR, "validator"),
        receiver=identity(Role.PROPOSER, "proposer"),
        object_ids=(OBJECT_ID,),
        content_ids=(INPUT_ID,),
    )
    assert AgentResponse.from_jsonl(response.to_jsonl()) == response

    with pytest.raises(ValidationError, match="failures"):
        AgentResponse(
            message_kind=MessageKind.FAILURE,
            request_content_id=request().content_id,
            sender=identity(Role.VALIDATOR, "validator"),
            receiver=identity(Role.PROPOSER, "proposer"),
        )
