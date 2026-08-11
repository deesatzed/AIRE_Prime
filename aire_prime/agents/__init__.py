"""Isolated AIRE agent roles and typed exchange protocol."""

from aire_prime.agents.ingress import (
    IngressRejection,
    IngressResult,
    ingest_envelope_jsonl,
    record_ingress_rejection,
)
from aire_prime.agents.protocol import AgentRequest, AgentResponse, MessageKind
from aire_prime.agents.roles import AgentIdentity, ClaimRoleAssignments, Role
from aire_prime.agents.subprocess_adapter import (
    FailureDiagnostic,
    ResourceObservation,
    SubprocessAdapter,
    TrustedCommand,
)

__all__ = [
    "AgentIdentity",
    "AgentRequest",
    "AgentResponse",
    "ClaimRoleAssignments",
    "FailureDiagnostic",
    "ResourceObservation",
    "IngressRejection",
    "IngressResult",
    "MessageKind",
    "Role",
    "SubprocessAdapter",
    "TrustedCommand",
    "ingest_envelope_jsonl",
    "record_ingress_rejection",
]
