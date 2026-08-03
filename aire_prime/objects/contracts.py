from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Self

from pydantic import field_validator, model_validator

from aire_prime.objects import CanonicalObject, normalize_measurements
from aire_prime.objects.evidence import GroundingClass


class RealityTier(StrEnum):
    PHYSICAL = "physical"
    DIGITAL_TWIN = "digital-twin"
    SIMULATED = "simulated"
    FORMAL = "formal"
    HYPOTHETICAL = "hypothetical"


ALLOWED_GROUNDING: Mapping[RealityTier, frozenset[GroundingClass]] = MappingProxyType({
    RealityTier.PHYSICAL: frozenset(GroundingClass),
    RealityTier.DIGITAL_TWIN: frozenset(
        {
            GroundingClass.UNGROUNDED,
            GroundingClass.SIMULATED,
            GroundingClass.OBSERVED,
            GroundingClass.COUNTERFACTUAL,
        }
    ),
    RealityTier.SIMULATED: frozenset(
        {
            GroundingClass.UNGROUNDED,
            GroundingClass.SIMULATED,
            GroundingClass.COUNTERFACTUAL,
        }
    ),
    RealityTier.FORMAL: frozenset({GroundingClass.UNGROUNDED}),
    RealityTier.HYPOTHETICAL: frozenset({GroundingClass.UNGROUNDED}),
})


class EvaluationContract(CanonicalObject):
    claim: str
    baseline_ids: tuple[str, ...]
    hidden_test_ids: tuple[str, ...]
    controls: tuple[str, ...] = ()
    ablations: tuple[str, ...] = ()
    resource_budget: tuple[tuple[str, float], ...] = ()
    decision_rule: str
    replication_requirements: tuple[str, ...] = ()

    @field_validator("baseline_ids", "hidden_test_ids")
    @classmethod
    def require_evaluation_sets(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError(
                "evaluation contracts require at least one baseline and hidden test ID"
            )
        return value

    @field_validator("resource_budget")
    @classmethod
    def normalize_resource_budget(
        cls, value: tuple[tuple[str, float], ...]
    ) -> tuple[tuple[str, float], ...]:
        normalized = normalize_measurements(value, field_name="resource_budget")
        if any(measurement < 0 for _, measurement in normalized):
            raise ValueError("resource_budget values must be nonnegative")
        return normalized


class BridgeContract(CanonicalObject):
    reality_tier: RealityTier
    authority_id: str
    authorization_boundary: str
    observable_consequences: tuple[str, ...] = ()
    approved_instruments: tuple[str, ...] = ()
    resource_envelope: tuple[tuple[str, float], ...] = ()
    protected_boundaries: tuple[str, ...] = ()
    permitted_status_claims: tuple[GroundingClass, ...] = ()

    @field_validator("authority_id", "authorization_boundary")
    @classmethod
    def require_bridge_boundaries(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("bridge contracts require a reality tier and authorization boundary")
        return value

    @field_validator("resource_envelope")
    @classmethod
    def normalize_resource_envelope(
        cls, value: tuple[tuple[str, float], ...]
    ) -> tuple[tuple[str, float], ...]:
        normalized = normalize_measurements(value, field_name="resource_envelope")
        if any(measurement < 0 for _, measurement in normalized):
            raise ValueError("resource_envelope values must be nonnegative")
        return normalized

    @model_validator(mode="after")
    def enforce_reality_tier(self) -> Self:
        disallowed = set(self.permitted_status_claims) - ALLOWED_GROUNDING[self.reality_tier]
        if disallowed:
            claims = ", ".join(sorted(claim.value for claim in disallowed))
            raise ValueError(f"reality tier cannot authorize grounding claims: {claims}")
        return self
