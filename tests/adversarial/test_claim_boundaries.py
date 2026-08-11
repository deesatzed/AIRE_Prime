import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aire_prime.cli import run_cli
from aire_prime.core.canonical import canonical_bytes
from aire_prime.experiments.e1.run import E1Report
from aire_prime.experiments.e2.baselines import resources
from aire_prime.experiments.e2.run import E2Report
from aire_prime.measurement.resources import MeasurementState

ROOT = Path(__file__).resolve().parents[2]


CID = "sha256:" + "a" * 64
ALLOWED_CLASSIFICATIONS = {
    "simulated-capability-transfer",
    "simulated-capability-transfer-not-established",
    "simulated-alien-sense-transfer",
    "simulated-alien-sense-transfer-not-established",
}
RELEASE_MARKDOWN = (
    "README.md",
    "docs/AIRE_V0_1_EVIDENCE.md",
    "docs/AIRE_V0_1_STATUS_AND_ROADMAP.md",
)
TOPIC = (
    r"(?:physical(?:ly)?(?: replicated| grounding| sense)?|qec|q12d|"
    r"quantum error[- ]correction|superintelligen(?:ce|t)|general intelligence|new physics)"
)
CLAIM_VERB = (
    r"(?:achiev(?:e|es|ed)|confirm(?:s|ed)?|demonstrat(?:e|es|ed)|establish(?:es|ed)?|"
    r"prov(?:e|es|ed)|support(?:s|ed)?|validat(?:e|es|ed))"
)
POSITIVE_FORBIDDEN = re.compile(
    rf"\b(?:{CLAIM_VERB}\b[^,;:.!?]{{0,60}}\b{TOPIC}\b|"
    rf"(?:is|are|was|were)\s+(?:physically grounded|physically replicated|"
    rf"superintelligent|general intelligence|new physics)\b|"
    rf"(?:has|have)\b[^,;:.!?]{{0,40}}\b{TOPIC}\b[^,;:.!?]{{0,30}}\badvantage\b|"
    rf"{TOPIC}\b[^,;:.!?]{{0,30}}\b(?:is|are|was|were)\s+"
    rf"(?:established|validated|confirmed|proved|demonstrated)\b)"
)
LOCAL_NEGATION = re.compile(
    r"\b(?:no|never|cannot|can't|unsupported|without|does not|do not|did not|"
    r"can not|could not|would not|will not|is not|are not|was not|were not|"
    r"has not|have not)\b"
)


def _positive_forbidden_claims(markdown: str) -> tuple[str, ...]:
    findings: list[str] = []
    normalized = re.sub(r"\s+", " ", markdown).strip()
    for raw_clause in re.split(
        r"(?<!\d)[,;.!?]+(?!\d)|"
        r"\b(?:and|but|yet|while|whereas|although|though|because|however|despite)\b",
        normalized,
        flags=re.IGNORECASE,
    ):
        line = raw_clause.strip().lower()
        for match in POSITIVE_FORBIDDEN.finditer(line):
            prefix = line[max(0, match.start() - 48) : match.start()]
            if not LOCAL_NEGATION.search(prefix):
                findings.append(raw_clause.strip())
                break
    return tuple(findings)


def _report_payloads() -> tuple[E1Report, E2Report]:
    created_at = datetime(2026, 8, 7, tzinfo=UTC)
    e1 = E1Report(
        created_at=created_at,
        classification="simulated-capability-transfer",
        seed=101,
        world_id=CID,
        reality_object_id=CID,
        evaluation_contract_id=CID,
        bridge_contract_id=CID,
        occurrence_report_id=CID,
        improvement_report_id=CID,
        agent_response_ids=(CID,),
        transfer_packet_bytes=4096,
        passed_gates=("transfer",),
        baseline_packet_ids=(CID,),
        baseline_ids=(CID,),
    )
    e2 = E2Report(
        created_at=created_at,
        classification="simulated-alien-sense-transfer-not-established",
        evidence_state="O0/G-S",
        seed=202,
        sense_proposal_id=CID,
        reality_object_id=CID,
        evaluation_contract_id=CID,
        bridge_contract_id=CID,
        occurrence_report_id=CID,
        improvement_report_id=CID,
        measurement_decision_id=CID,
        transfer_packet_bytes=4096,
        heldout_accuracy=1.0,
        transformed_accuracy=1.0,
        independent_reproduction_accuracy=1.0,
        passed_gates=("causal-ablation",),
        failed_gates=("heldout-gain", "matched-controls"),
    )
    return e1, e2


def test_cli_rendered_report_classifications_are_simulated_and_bounded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rendered = []
    for index, report in enumerate(_report_payloads()):
        path = tmp_path / f"report-{index}.json"
        path.write_bytes(canonical_bytes(report.model_dump(mode="json")))
        assert run_cli(["report", "show", str(path)]) == 0
        rendered.append(json.loads(capsys.readouterr().out))

    classifications = {payload["classification"] for payload in rendered}

    assert classifications <= ALLOWED_CLASSIFICATIONS
    assert rendered[1]["evidence_state"] == "O0/G-S"
    assert not any(
        token in classification
        for classification in classifications
        for token in ("physical", "superintelligence", "new-physics", "qec", "q12d")
    )


def test_release_markdown_contains_no_positive_forbidden_claim() -> None:
    markdown = "\n".join(
        (ROOT / path).read_text() for path in RELEASE_MARKDOWN
    )

    assert _positive_forbidden_claims(markdown) == ()


@pytest.mark.parametrize(
    "claim",
    (
        "AIRE validates QEC.",
        "AIRE achieved physical grounding.",
        "The result supports a physically replicated sense.",
        "AIRE is superintelligent.",
        "This demonstrates general intelligence.",
        "The experiment confirms new physics.",
        "AIRE has a Q12D resource advantage.",
        "AIRE only validates QEC.",
        "AIRE is superintelligent only after training.",
        "AIRE establishes physical grounding and is not simulated.",
        "AIRE is superintelligent, not ordinary.",
        "AIRE is not merely simulated and is physically grounded.",
        "AIRE cannot demonstrate QEC while it demonstrates physical grounding.",
        "AIRE does not establish QEC because AIRE establishes physical grounding.",
    ),
)
def test_claim_scanner_rejects_positive_paraphrases(claim: str) -> None:
    assert _positive_forbidden_claims(claim)


@pytest.mark.parametrize(
    "denial",
    (
        "AIRE does not validate QEC.",
        "No physical grounding is established.",
        "The result cannot support superintelligence or new physics.",
        "## Unsupported claims\n- A Q12D resource advantage is absent from v0.1.",
    ),
)
def test_claim_scanner_allows_explicit_denials(denial: str) -> None:
    assert _positive_forbidden_claims(denial) == ()


@pytest.mark.parametrize(
    "bypass",
    (
        "AIRE does not establish QEC; it establishes physical grounding.",
        "## Limitations\nAIRE is superintelligent.",
        "AIRE validates\nQ12D as a resource advantage.",
    ),
)
def test_claim_scanner_rejects_mixed_section_and_wrapping_bypasses(bypass: str) -> None:
    assert _positive_forbidden_claims(bypass)


def test_missing_host_metrics_remain_undetermined_not_zero() -> None:
    vector = resources(packet_bytes=4096, observations=32)

    for measurement in (vector.peak_resident_bytes, vector.elapsed_time):
        assert measurement.state is MeasurementState.UNDETERMINED
        assert measurement.value is None
        assert measurement.model_dump(mode="json") == {
            "state": "undetermined",
            "value": None,
        }
