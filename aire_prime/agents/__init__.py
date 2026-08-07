"""Isolated AIRE agent roles and typed exchange protocol."""

from aire_prime.agents.protocol import AgentRequest, AgentResponse, MessageKind
from aire_prime.agents.roles import AgentIdentity, ClaimRoleAssignments, Role
from aire_prime.agents.subprocess_adapter import (
    FailureDiagnostic,
    SubprocessAdapter,
    TrustedCommand,
)

__all__ = [
    "AgentIdentity",
    "AgentRequest",
    "AgentResponse",
    "ClaimRoleAssignments",
    "FailureDiagnostic",
    "MessageKind",
    "Role",
    "SubprocessAdapter",
    "TrustedCommand",
]
