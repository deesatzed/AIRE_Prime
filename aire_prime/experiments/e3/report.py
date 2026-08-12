import json
from pathlib import Path
from typing import Literal

from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.experiments.e3.analysis import E3AnalysisResult, E3Block, analyze_confirmatory
from aire_prime.experiments.e3.run import E3RunResult


class E3EvidenceManifest(FrozenModel):
    kind: Literal["e3-evidence-manifest"] = "e3-evidence-manifest"
    run_id: str
    manifest_id: str
    result_id: str
    analysis_id: str | None
    required_artifacts: tuple[str, ...]
    grounding: Literal["G-S"] = "G-S"

    @property
    def content_id(self) -> str:
        return content_id(self)


class E3Report(FrozenModel):
    kind: Literal["e3-report"] = "e3-report"
    version: str = "AIRE-E3-V1"
    classification: Literal["transferred", "partial", "negative", "undetermined"]
    grounding: Literal["G-S"] = "G-S"
    run_id: str
    analysis: E3AnalysisResult | None
    failed_gates: tuple[str, ...]
    limitations: tuple[str, ...]
    result_id: str

    @property
    def content_id(self) -> str:
        return content_id(self)


def blocks_for_analysis(result: E3RunResult) -> tuple[E3Block, ...]:
    grouped: dict[tuple[str, str, str], list[float]] = {}
    resources: dict[tuple[str, str, str], set[str]] = {}
    for block in result.blocks:
        if block.arm_id == "B9":
            continue
        key = (block.arm_id, block.world_id, block.shift_family)
        grouped.setdefault(key, []).append(block.accuracy)
        resources.setdefault(key, set()).add(block.resource_state)
    return tuple(
        E3Block(
            arm_id=arm_id,
            world_id=world_id,
            shift_family=shift_family,
            recipient_id="recipient-matrix",
            auc=sum(values) / len(values),
            valid="undetermined" not in resources[(arm_id, world_id, shift_family)],
            resource_state=(
                "undetermined"
                if "undetermined" in resources[(arm_id, world_id, shift_family)]
                else "observed"
            ),
        )
        for (arm_id, world_id, shift_family), values in sorted(grouped.items())
    )


def classify_run(result: E3RunResult, analysis: E3AnalysisResult | None) -> E3Report:
    failures: list[str] = []
    if analysis is None:
        failures.append("analysis-not-run")
    elif analysis.status == "undetermined":
        failures.append("missing-or-invalid-evidence")
    elif analysis.status == "rejected":
        failures.append("primary-effect-margin")
    failures.extend(("causal-ablation", "family-noninferiority", "independent-reproduction"))
    classification: Literal["transferred", "partial", "negative", "undetermined"]
    if analysis is None or analysis.status == "undetermined":
        classification = "undetermined"
    elif analysis.status == "rejected":
        classification = "negative"
    else:
        classification = "partial"
    return E3Report(
        classification=classification,
        run_id=result.content_id,
        analysis=analysis,
        failed_gates=tuple(dict.fromkeys(failures)),
        limitations=(
            "simulated procedural worlds only",
            "B7 and B8 incompatibility records remain open for E3 v2",
            "no independent external recipient reproduction",
        ),
        result_id=result.content_id,
    )


def write_e3_result(result: E3RunResult, output: Path, *, analyze: bool = False) -> E3Report:
    output.mkdir(parents=True, exist_ok=True)
    analysis = None
    if analyze:
        blocks = blocks_for_analysis(result)
        analysis = analyze_confirmatory(
            tuple(blocks), seed=result.manifest.root_seed, bootstrap_replicates=128
        )
    report = classify_run(result, analysis)
    required = ("e3_manifest.json", "e3_result.json", "e3_report.json")
    manifest = E3EvidenceManifest(
        run_id=result.content_id,
        manifest_id=result.manifest.content_id,
        result_id=result.content_id,
        analysis_id=analysis.content_id if analysis is not None else None,
        required_artifacts=required,
    )
    for name, value in (
        ("e3_manifest.json", manifest),
        ("e3_result.json", result),
        ("e3_report.json", report),
    ):
        payload = value.model_dump(mode="json")
        payload["content_id"] = value.content_id
        (output / name).write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


__all__ = [
    "E3EvidenceManifest",
    "E3Report",
    "blocks_for_analysis",
    "classify_run",
    "write_e3_result",
]
