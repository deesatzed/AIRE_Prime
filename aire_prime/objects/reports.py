from collections.abc import Mapping
from typing import Self

from pydantic import ValidationInfo, field_validator, model_validator

from aire_prime.objects import CanonicalObject, ContentID, normalize_measurements
from aire_prime.objects.evidence import EvidenceState, GroundingClass, OccurrenceMaturity


class OccurrenceReport(CanonicalObject):
    proposal_id: ContentID
    contract_id: ContentID
    validator_id: str
    evidence_state: EvidenceState
    independence_evidence: tuple[str, ...] = ()
    causal_evidence: tuple[str, ...] = ()
    generalization_evidence: tuple[str, ...] = ()
    transfer_evidence: tuple[str, ...] = ()
    replication_evidence: tuple[str, ...] = ()
    known_failures: tuple[str, ...] = ()
    evidence_attachments: tuple[str, ...] = ()
    expiration_conditions: tuple[str, ...] = ()
    resource_measurements: tuple[tuple[str, float], ...]

    @field_validator(
        "independence_evidence",
        "causal_evidence",
        "generalization_evidence",
        "transfer_evidence",
        "replication_evidence",
        "evidence_attachments",
    )
    @classmethod
    def require_nonblank_evidence(
        cls, value: tuple[str, ...], info: ValidationInfo
    ) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError(f"{info.field_name} entries must be nonblank")
        return value

    @field_validator("validator_id")
    @classmethod
    def require_validator(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("validator_id cannot be empty")
        return value

    @field_validator("resource_measurements")
    @classmethod
    def normalize_resources(
        cls, value: tuple[tuple[str, float], ...]
    ) -> tuple[tuple[str, float], ...]:
        if not value:
            raise ValueError("occurrence reports require resource measurements")
        normalized = normalize_measurements(value, field_name="resource_measurements")
        if any(measurement < 0 for _, measurement in normalized):
            raise ValueError("resource_measurements values must be nonnegative")
        return normalized

    @model_validator(mode="after")
    def require_claim_evidence(self) -> Self:
        required_by_maturity = {
            OccurrenceMaturity.ASSOCIATED: ("independence_evidence",),
            OccurrenceMaturity.CAUSALLY_USED: ("independence_evidence", "causal_evidence"),
            OccurrenceMaturity.GENERALIZED: (
                "independence_evidence",
                "causal_evidence",
                "generalization_evidence",
            ),
            OccurrenceMaturity.TRANSFERRED: (
                "independence_evidence",
                "causal_evidence",
                "generalization_evidence",
                "transfer_evidence",
            ),
        }
        for field_name in required_by_maturity.get(self.evidence_state.occurrence, ()):
            if not getattr(self, field_name):
                raise ValueError(f"{self.evidence_state.occurrence.value} requires {field_name}")
        physical = {
            GroundingClass.PHYSICAL,
            GroundingClass.PHYSICALLY_REPLICATED,
        }
        if self.evidence_state.grounding in physical and not self.evidence_attachments:
            raise ValueError("physical grounding requires evidence attachments")
        if (
            self.evidence_state.grounding is GroundingClass.PHYSICALLY_REPLICATED
            and not self.replication_evidence
        ):
            raise ValueError("G-PR grounding requires independent replication evidence")
        return self


class ImprovementReport(CanonicalObject):
    metric_proposal_id: ContentID
    evaluation_contract_id: ContentID
    occurrence_report_id: ContentID
    validator_id: str
    claimed_grounding: GroundingClass
    improvement_vector: tuple[tuple[str, float], ...]
    baseline_results: tuple[tuple[str, float], ...]
    resource_measurements: tuple[tuple[str, float], ...]
    protected_effects: tuple[tuple[str, float], ...] = ()
    adversarial_results: tuple[str, ...] = ()
    replications: tuple[str, ...] = ()
    known_failures: tuple[str, ...] = ()
    evidence_attachments: tuple[str, ...] = ()
    expiration_conditions: tuple[str, ...] = ()

    @field_validator(
        "improvement_vector",
        "baseline_results",
        "resource_measurements",
        "protected_effects",
    )
    @classmethod
    def normalize_result_pairs(
        cls, value: tuple[tuple[str, float], ...], info: ValidationInfo
    ) -> tuple[tuple[str, float], ...]:
        field_name = info.field_name or "measurements"
        required = {"improvement_vector", "baseline_results", "resource_measurements"}
        if field_name in required and not value:
            raise ValueError(f"{field_name} must not be empty")
        normalized = normalize_measurements(value, field_name=field_name)
        if field_name == "resource_measurements" and any(
            measurement < 0 for _, measurement in normalized
        ):
            raise ValueError("resource_measurements values must be nonnegative")
        return normalized

    @field_validator("validator_id")
    @classmethod
    def require_validator(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("validator_id cannot be empty")
        return value

    @model_validator(mode="after")
    def grounding_must_match_occurrence(self, info: ValidationInfo) -> Self:
        context = info.context
        if not isinstance(context, Mapping):
            raise ValueError("trusted occurrence report resolver is required")
        reports = context.get("occurrence_reports")
        if not isinstance(reports, Mapping):
            raise ValueError("trusted occurrence report resolver is required")
        occurrence = reports.get(self.occurrence_report_id)
        if not isinstance(occurrence, OccurrenceReport):
            raise ValueError("referenced occurrence report was not resolved")
        if occurrence.content_id != self.occurrence_report_id:
            raise ValueError("resolved occurrence report content ID does not match")
        if self.claimed_grounding != occurrence.evidence_state.grounding:
            raise ValueError("improvement grounding must match its occurrence report")
        return self
