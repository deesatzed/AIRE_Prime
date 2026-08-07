from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from aire_prime.grc.types import SpaceKind, StructuralType
from aire_prime.objects.contracts import BridgeContract, EvaluationContract, RealityTier
from aire_prime.objects.evidence import EvidenceState, GroundingClass, OccurrenceMaturity
from aire_prime.objects.proposals import MetricProposal, RealityObject, SenseProposal
from aire_prime.objects.reports import ImprovementReport, OccurrenceReport

NOW = datetime(2026, 8, 3, tzinfo=UTC)
CID_A = "sha256:" + "a" * 64
CID_B = "sha256:" + "b" * 64

OCCURRENCE = OccurrenceReport(
    created_at=NOW,
    proposal_id=CID_A,
    contract_id=CID_B,
    validator_id="validator:1",
    evidence_state=EvidenceState(
        occurrence=OccurrenceMaturity.CLAIMED,
        grounding=GroundingClass.SIMULATED,
    ),
    resource_measurements=(("seconds", 1.0),),
)


def canonical_object_cases() -> tuple[
    tuple[type[BaseModel], dict[str, object], dict[str, object] | None], ...
]:
    common: dict[str, object] = {"created_at": NOW, "validity_region": ("synthetic",)}
    return (
        (SenseProposal, {**common, "distinction": "d", "domain": "x", "probe": "p"}, None),
        (
            RealityObject,
            {
                **common,
                "state_space": StructuralType(kind=SpaceKind.SCALAR),
                "interfaces": ("observe",),
                "constructor_id": "constructor:1",
            },
            None,
        ),
        (
            MetricProposal,
            {
                **common,
                "dimension": "gain",
                "measurement_procedure": "difference",
                "ordering": "higher",
                "baseline_ids": ("b1",),
                "consequence": "predicts",
                "falsifiers": ("no gain",),
                "anti_gaming_tests": ("shuffle",),
                "complexity_cost": 1.0,
                "expiration_conditions": ("distribution shift",),
            },
            None,
        ),
        (
            EvaluationContract,
            {
                **common,
                "claim": "transfer",
                "baseline_ids": ("b1",),
                "hidden_test_ids": ("h1",),
                "decision_rule": "delta > 0",
            },
            None,
        ),
        (
            BridgeContract,
            {
                **common,
                "reality_tier": RealityTier.SIMULATED,
                "authority_id": "authority:1",
                "authorization_boundary": "read-only",
            },
            None,
        ),
        (
            OccurrenceReport,
            {
                **common,
                "proposal_id": CID_A,
                "contract_id": CID_B,
                "validator_id": "v1",
                "evidence_state": EvidenceState(
                    occurrence=OccurrenceMaturity.CLAIMED,
                    grounding=GroundingClass.SIMULATED,
                ),
                "resource_measurements": (("seconds", 1.0),),
            },
            None,
        ),
        (
            ImprovementReport,
            {
                **common,
                "metric_proposal_id": CID_A,
                "evaluation_contract_id": CID_B,
                "occurrence_report_id": OCCURRENCE.content_id,
                "validator_id": "v1",
                "claimed_grounding": GroundingClass.SIMULATED,
                "improvement_vector": (("gain", 1.0),),
                "baseline_results": (("b1", 0.0),),
                "resource_measurements": (("seconds", 1.0),),
            },
            {"occurrence_reports": {OCCURRENCE.content_id: OCCURRENCE}},
        ),
    )


def test_occurrence_and_grounding_are_independent_axes() -> None:
    state = EvidenceState(
        occurrence=OccurrenceMaturity.TRANSFERRED,
        grounding=GroundingClass.SIMULATED,
    )
    assert state.display == "O4/G-S"


@pytest.mark.parametrize(("model_type", "payload", "context"), canonical_object_cases())
def test_every_object_rejects_extra_fields(
    model_type: type[BaseModel], payload: dict[str, object], context: dict[str, object] | None
) -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        model_type.model_validate({**payload, "undeclared": True}, context=context)


def test_evaluation_contract_requires_baseline_and_hidden_test() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        EvaluationContract(
            created_at=NOW,
            claim="transfer",
            baseline_ids=(),
            hidden_test_ids=("h1",),
            decision_rule="delta > 0",
        )


def test_bridge_contract_requires_reality_tier_and_authorization_boundary() -> None:
    with pytest.raises(ValidationError, match="reality tier"):
        BridgeContract(
            created_at=NOW,
            reality_tier=RealityTier.SIMULATED,
            authority_id="authority:1",
            authorization_boundary="",
        )


def test_improvement_cannot_exceed_occurrence_grounding() -> None:
    with pytest.raises(ValidationError, match="occurrence report"):
        ImprovementReport.model_validate(
            {
                "created_at": NOW,
                "metric_proposal_id": CID_A,
                "evaluation_contract_id": CID_B,
                "occurrence_report_id": OCCURRENCE.content_id,
                "validator_id": "v1",
                "claimed_grounding": GroundingClass.PHYSICAL,
                "improvement_vector": (("gain", 1.0),),
                "baseline_results": (("b1", 0.0),),
                "resource_measurements": (("seconds", 1.0),),
            },
            context={"occurrence_reports": {OCCURRENCE.content_id: OCCURRENCE}},
        )


def test_improvement_requires_trusted_occurrence_resolution() -> None:
    with pytest.raises(ValidationError, match="trusted occurrence report resolver"):
        ImprovementReport(
            created_at=NOW,
            metric_proposal_id=CID_A,
            evaluation_contract_id=CID_B,
            occurrence_report_id=OCCURRENCE.content_id,
            validator_id="v1",
            claimed_grounding=GroundingClass.SIMULATED,
            improvement_vector=(("gain", 1.0),),
            baseline_results=(("b1", 0.0),),
            resource_measurements=(("seconds", 1.0),),
        )


def test_simulated_bridge_cannot_authorize_physical_claims() -> None:
    with pytest.raises(ValidationError, match="cannot authorize"):
        BridgeContract(
            created_at=NOW,
            reality_tier=RealityTier.SIMULATED,
            authority_id="authority:1",
            authorization_boundary="read-only",
            permitted_status_claims=(GroundingClass.PHYSICAL,),
        )


def test_transferred_occurrence_requires_transfer_evidence() -> None:
    with pytest.raises(ValidationError, match="requires"):
        OccurrenceReport(
            created_at=NOW,
            proposal_id=CID_A,
            contract_id=CID_B,
            validator_id="validator:1",
            evidence_state=EvidenceState(
                occurrence=OccurrenceMaturity.TRANSFERRED,
                grounding=GroundingClass.SIMULATED,
            ),
            resource_measurements=(("seconds", 1.0),),
        )


def test_measurement_vectors_are_sorted_and_finite() -> None:
    report = ImprovementReport.model_validate(
        {
            "created_at": NOW,
            "metric_proposal_id": CID_A,
            "evaluation_contract_id": CID_B,
            "occurrence_report_id": OCCURRENCE.content_id,
            "validator_id": "v1",
            "claimed_grounding": GroundingClass.SIMULATED,
            "improvement_vector": (("z", 1.0), ("a", 2.0)),
            "baseline_results": (("b1", 0.0),),
            "resource_measurements": (("seconds", 1.0),),
        },
        context={"occurrence_reports": {OCCURRENCE.content_id: OCCURRENCE}},
    )
    assert report.improvement_vector == (("a", 2.0), ("z", 1.0))

    with pytest.raises(ValidationError, match="finite"):
        OccurrenceReport(
            created_at=NOW,
            proposal_id=CID_A,
            contract_id=CID_B,
            validator_id="validator:1",
            evidence_state=EvidenceState(
                occurrence=OccurrenceMaturity.CLAIMED,
                grounding=GroundingClass.SIMULATED,
            ),
            resource_measurements=(("seconds", float("inf")),),
        )


def test_content_id_is_derived_and_ignores_human_label() -> None:
    left = SenseProposal(
        created_at=NOW, distinction="d", domain="x", probe="p", label="human label"
    )
    right = SenseProposal(
        created_at=NOW, distinction="d", domain="x", probe="p", label="other label"
    )
    assert left.content_id == right.content_id


def test_wire_serialization_round_trips_and_verifies_content_id() -> None:
    proposal = SenseProposal(created_at=NOW, distinction="d", domain="x", probe="p")
    wire = proposal.model_dump(mode="json")
    assert SenseProposal.from_wire(wire) == proposal

    wire["distinction"] = "tampered"
    with pytest.raises(ValueError, match="does not match"):
        SenseProposal.from_wire(wire)


def test_improvement_requires_nonempty_results_and_resources() -> None:
    payload = {
        "created_at": NOW,
        "metric_proposal_id": CID_A,
        "evaluation_contract_id": CID_B,
        "occurrence_report_id": OCCURRENCE.content_id,
        "validator_id": "v1",
        "claimed_grounding": GroundingClass.SIMULATED,
        "improvement_vector": (("gain", 1.0),),
        "baseline_results": (("b1", 0.0),),
        "resource_measurements": (("seconds", 1.0),),
    }
    for field_name in ("improvement_vector", "baseline_results", "resource_measurements"):
        with pytest.raises(ValidationError, match=f"{field_name} must not be empty"):
            ImprovementReport.model_validate(
                {**payload, field_name: ()},
                context={"occurrence_reports": {OCCURRENCE.content_id: OCCURRENCE}},
            )


def test_physically_replicated_grounding_requires_replication_evidence() -> None:
    with pytest.raises(ValidationError, match="independent replication"):
        OccurrenceReport(
            created_at=NOW,
            proposal_id=CID_A,
            contract_id=CID_B,
            validator_id="validator:1",
            evidence_state=EvidenceState(
                occurrence=OccurrenceMaturity.CLAIMED,
                grounding=GroundingClass.PHYSICALLY_REPLICATED,
            ),
            evidence_attachments=("instrument:1",),
            resource_measurements=(("seconds", 1.0),),
        )


def test_evidence_gates_reject_blank_placeholders() -> None:
    with pytest.raises(ValidationError, match="entries must be nonblank"):
        OccurrenceReport(
            created_at=NOW,
            proposal_id=CID_A,
            contract_id=CID_B,
            validator_id="validator:1",
            evidence_state=EvidenceState(
                occurrence=OccurrenceMaturity.CLAIMED,
                grounding=GroundingClass.PHYSICALLY_REPLICATED,
            ),
            evidence_attachments=(" ",),
            replication_evidence=(" ",),
            resource_measurements=(("seconds", 1.0),),
        )


def test_measurements_reject_duplicate_keys_and_negative_resources() -> None:
    with pytest.raises(ValidationError, match="keys must be unique"):
        OccurrenceReport(
            created_at=NOW,
            proposal_id=CID_A,
            contract_id=CID_B,
            validator_id="validator:1",
            evidence_state=EvidenceState(
                occurrence=OccurrenceMaturity.CLAIMED,
                grounding=GroundingClass.SIMULATED,
            ),
            resource_measurements=(("seconds", 1.0), ("seconds", 2.0)),
        )

    with pytest.raises(ValidationError, match="nonnegative"):
        OccurrenceReport(
            created_at=NOW,
            proposal_id=CID_A,
            contract_id=CID_B,
            validator_id="validator:1",
            evidence_state=EvidenceState(
                occurrence=OccurrenceMaturity.CLAIMED,
                grounding=GroundingClass.SIMULATED,
            ),
            resource_measurements=(("seconds", -1.0),),
        )
