import re
from enum import StrEnum
from typing import Self

from pydantic import field_validator, model_validator

from aire_prime.core.model import FrozenModel
from aire_prime.objects import ContentID


class Role(StrEnum):
    PROPOSER = "proposer"
    RECEIVER = "receiver"
    VALIDATOR = "validator"
    ADVERSARY = "adversary"
    AUTHORIZER = "authorizer"


class AgentIdentity(FrozenModel):
    agent_id: str
    role: Role

    @field_validator("agent_id")
    @classmethod
    def require_canonical_id(cls, value: str) -> str:
        if re.fullmatch(r"[a-z][a-z0-9._:-]{0,63}", value) is None:
            raise ValueError(
                "agent identity must be a canonical lower-case machine identifier"
            )
        return value


class ClaimRoleAssignments(FrozenModel):
    claim_id: ContentID
    proposer: AgentIdentity
    receiver: AgentIdentity
    validator: AgentIdentity
    adversary: AgentIdentity
    authorizer: AgentIdentity

    @property
    def agents(self) -> tuple[AgentIdentity, ...]:
        return (
            self.proposer,
            self.receiver,
            self.validator,
            self.adversary,
            self.authorizer,
        )

    @model_validator(mode="after")
    def require_role_and_identity_separation(self) -> Self:
        expected = (
            Role.PROPOSER,
            Role.RECEIVER,
            Role.VALIDATOR,
            Role.ADVERSARY,
            Role.AUTHORIZER,
        )
        if tuple(agent.role for agent in self.agents) != expected:
            raise ValueError("claim role assignment has a mismatched role")
        if len({agent.agent_id for agent in self.agents}) != len(self.agents):
            raise ValueError("claim roles require independent agent identities")
        return self
