import argparse
import json
import sys
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aire_prime.agents import AgentRequest, AgentResponse, MessageKind
from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.exchange.receipt import RealizationReceipt
from aire_prime.experiments.e1.run import E1Report, run_e1
from aire_prime.experiments.e1.world import ProceduralWorld
from aire_prime.experiments.e2.baselines import E2BaselineResult
from aire_prime.experiments.e2.run import E2Report, run_e2
from aire_prime.measurement.decision import ImprovementDecision
from aire_prime.objects import CanonicalObject
from aire_prime.objects.contracts import BridgeContract, EvaluationContract
from aire_prime.objects.evidence import GroundingClass
from aire_prime.objects.proposals import MetricProposal, RealityObject, SenseProposal
from aire_prime.objects.reports import ImprovementReport, OccurrenceReport
from aire_prime.registry.store import RegistryStore, RegistryVerificationError
from aire_prime.schema import schemas_current


class InspectionError(ValueError):
    pass


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if type(value) is not dict:
        raise InspectionError(f"{path.name} must contain a JSON object")
    return value


def _validate_grounding(grounding: GroundingClass) -> None:
    if grounding not in {GroundingClass.UNGROUNDED, GroundingClass.SIMULATED}:
        raise InspectionError("v0.1 report attempts an invalid grounding escalation")


def _jsonl(path: Path, model: type[AgentRequest] | type[AgentResponse]) -> tuple[Any, ...]:
    lines = path.read_bytes().splitlines()
    if not lines:
        raise InspectionError(f"{path.name} must not be empty")
    return tuple(model.from_jsonl(line + b"\n") for line in lines)


def _validate_exchange_pair(
    request_path: Path, response_path: Path
) -> tuple[tuple[AgentRequest, ...], tuple[AgentResponse, ...]]:
    requests = _jsonl(request_path, AgentRequest)
    responses = _jsonl(response_path, AgentResponse)
    if len(requests) != len(responses):
        raise InspectionError("request and response counts differ")
    typed_requests = tuple(request for request in requests if isinstance(request, AgentRequest))
    typed_responses = tuple(
        response for response in responses if isinstance(response, AgentResponse)
    )
    for request, response in zip(typed_requests, typed_responses, strict=True):
        if response.request_content_id != request.content_id:
            raise InspectionError("response does not link to its paired request")
        if response.sender != request.receiver or response.receiver != request.sender:
            raise InspectionError("response identities do not invert the paired request")
        if response.message_kind is not MessageKind.RESPONSE or response.failures:
            raise InspectionError(f"contained response failure retained in {response_path.name}")
    return typed_requests, typed_responses


def _validate_receipts(directory: Path) -> tuple[RealizationReceipt, ...]:
    path = directory / "realization_receipts.json"
    values = json.loads(path.read_bytes())
    if type(values) is not list:
        raise InspectionError("realization receipts must be a JSON array")
    receipts = tuple(RealizationReceipt.model_validate(value) for value in values)
    if not receipts:
        raise InspectionError("realization receipt array must not be empty")
    for receipt in receipts:
        if not receipt.success:
            raise InspectionError("resource-budget or realization failure retained in receipt")
    return receipts


def _require_manifest(directory: Path, names: tuple[str, ...]) -> None:
    missing = tuple(name for name in names if not (directory / name).is_file())
    if missing:
        raise InspectionError(f"evidence directory is missing required artifacts: {missing}")


def _inspect_directory(directory: Path) -> dict[str, object]:
    e1_path = directory / "e1_report.json"
    e2_path = directory / "e2_report.json"
    if e1_path.exists() == e2_path.exists():
        raise InspectionError("evidence directory must contain exactly one E1 or E2 report")
    report: E1Report | E2Report
    exchange_pairs: tuple[tuple[str, str], ...]
    if e1_path.exists():
        _require_manifest(
            directory,
            (
                "e1_report.json",
                "world.json",
                "reality_object.json",
                "evaluation_contract.json",
                "bridge_contract.json",
                "metric_proposal.json",
                "occurrence_report.json",
                "improvement_report.json",
                "realization_receipts.json",
                "transfer_packet.json",
                "agent_requests.jsonl",
                "agent_responses.jsonl",
                "baseline_requests.jsonl",
                "baseline_responses.jsonl",
                "baseline_results.json",
                "registry.jsonl",
            ),
        )
        report = E1Report.from_wire(_load_object(e1_path))
        exchange_pairs = (
            ("agent_requests.jsonl", "agent_responses.jsonl"),
            ("baseline_requests.jsonl", "baseline_responses.jsonl"),
        )
    else:
        fixed = (
            "e2_report.json",
            "sense_proposal.json",
            "reality_object.json",
            "evaluation_contract.json",
            "bridge_contract.json",
            "metric_proposal.json",
            "occurrence_report.json",
            "improvement_report.json",
            "measurement_decision.json",
            "baseline_results.json",
            "ablation_evidence.json",
            "realization_receipts.json",
            "operator_packet.json",
            "reproduction_operator_packet.json",
            "registry.jsonl",
            "discovery_request.jsonl",
            "discovery_response.jsonl",
            "recipient_request.jsonl",
            "recipient_response.jsonl",
            "reproduction_discovery_request.jsonl",
            "reproduction_discovery_response.jsonl",
            "reproduction_request.jsonl",
            "reproduction_response.jsonl",
        )
        indexed = tuple(
            f"{kind}_{index}_{direction}.jsonl"
            for kind, count in (("baseline", 3), ("ablation", 4))
            for index in range(count)
            for direction in ("request", "response")
        )
        _require_manifest(directory, fixed + indexed)
        report = E2Report.from_wire(_load_object(e2_path))
        if not report.evidence_state.endswith("/G-S"):
            raise InspectionError("E2 report exceeds the simulated grounding ceiling")
        exchange_pairs = (
            ("discovery_request.jsonl", "discovery_response.jsonl"),
            ("recipient_request.jsonl", "recipient_response.jsonl"),
            ("reproduction_discovery_request.jsonl", "reproduction_discovery_response.jsonl"),
            ("reproduction_request.jsonl", "reproduction_response.jsonl"),
            *(
                (f"baseline_{index}_request.jsonl", f"baseline_{index}_response.jsonl")
                for index in range(3)
            ),
            *(
                (f"ablation_{index}_request.jsonl", f"ablation_{index}_response.jsonl")
                for index in range(4)
            ),
        )

    contract = EvaluationContract.from_wire(_load_object(directory / "evaluation_contract.json"))
    bridge = BridgeContract.from_wire(_load_object(directory / "bridge_contract.json"))
    reality = RealityObject.from_wire(_load_object(directory / "reality_object.json"))
    metric = MetricProposal.from_wire(_load_object(directory / "metric_proposal.json"))
    occurrence = OccurrenceReport.from_wire(_load_object(directory / "occurrence_report.json"))
    improvement = ImprovementReport.from_wire(
        _load_object(directory / "improvement_report.json"),
        context={"occurrence_reports": {occurrence.content_id: occurrence}},
    )
    _validate_grounding(occurrence.evidence_state.grounding)
    if report.reality_object_id != reality.content_id:
        raise InspectionError("report reality object link does not resolve")
    if improvement.metric_proposal_id != metric.content_id:
        raise InspectionError("improvement metric proposal link does not resolve")
    additional_ids = {reality.content_id, metric.content_id}
    if isinstance(report, E1Report):
        world = ProceduralWorld.model_validate(json.loads((directory / "world.json").read_bytes()))
        if report.world_id != world.content_id:
            raise InspectionError("E1 world link does not resolve")
        additional_ids.add(world.content_id)
    else:
        sense = SenseProposal.from_wire(_load_object(directory / "sense_proposal.json"))
        _validate_grounding(sense.grounding_claim)
        if report.sense_proposal_id != sense.content_id:
            raise InspectionError("E2 sense proposal link does not resolve")
        additional_ids.add(sense.content_id)
    if report.evaluation_contract_id != contract.content_id:
        raise InspectionError("report evaluation contract link does not resolve")
    if report.bridge_contract_id != bridge.content_id:
        raise InspectionError("report bridge contract link does not resolve")
    if report.occurrence_report_id != occurrence.content_id:
        raise InspectionError("report occurrence link does not resolve")
    if report.improvement_report_id != improvement.content_id:
        raise InspectionError("report improvement link does not resolve")
    if occurrence.contract_id != contract.content_id:
        raise InspectionError("occurrence contract link does not resolve")

    decision: ImprovementDecision | None = None
    resource_accounting: dict[str, object] | None = None
    if isinstance(report, E2Report):
        decision = ImprovementDecision.model_validate(
            json.loads((directory / "measurement_decision.json").read_bytes())
        )
        if report.measurement_decision_id != decision.content_id:
            raise InspectionError("E2 measurement decision link does not resolve")
        values = json.loads((directory / "baseline_results.json").read_bytes())
        if type(values) is not list:
            raise InspectionError("E2 baseline results must be a JSON array")
        baseline_results = tuple(E2BaselineResult.model_validate(value) for value in values)
        if not baseline_results:
            raise InspectionError("E2 baseline results must not be empty")
        resource_accounting = {
            name: measurement.model_dump(mode="json")
            for name, measurement in baseline_results[0].resources.measurements()
        }

    exchanges = tuple(
        _validate_exchange_pair(directory / request_name, directory / response_name)
        for request_name, response_name in exchange_pairs
    )
    receipts = _validate_receipts(directory)
    events = RegistryStore(directory / "registry.jsonl").verify()
    registered = {event.object_id for event in events}
    required = {
        report.content_id,
        contract.content_id,
        bridge.content_id,
        occurrence.content_id,
        improvement.content_id,
        *additional_ids,
        *(request.content_id for requests, _ in exchanges for request in requests),
        *(response.content_id for _, responses in exchanges for response in responses),
        *(content_id(receipt) for receipt in receipts),
    }
    if decision is not None:
        required.add(decision.content_id)
    if not required <= registered:
        missing = tuple(sorted(required - registered))
        raise InspectionError(f"required report chain does not resolve: {missing}")
    summary: dict[str, object] = {
        "report_id": report.content_id,
        "classification": report.classification,
        "grounding": occurrence.evidence_state.grounding.value,
        "occurrence": occurrence.evidence_state.occurrence.value,
        "failed_gates": report.failed_gates,
        "registry_head": events[-1].event_content_id,
    }
    if resource_accounting is not None:
        summary["baseline_resource_accounting"] = resource_accounting
    return summary


def _inspect_file(path: Path) -> tuple[CanonicalObject, dict[str, object]]:
    payload = _load_object(path)
    if "world_id" in payload:
        value: CanonicalObject = E1Report.from_wire(payload)
    elif isinstance(payload.get("evidence_state"), str):
        value = E2Report.from_wire(payload)
        if not value.evidence_state.endswith("/G-S"):
            raise InspectionError("E2 report exceeds the simulated grounding ceiling")
    elif "proposal_id" in payload and isinstance(payload.get("evidence_state"), dict):
        occurrence = OccurrenceReport.from_wire(payload)
        _validate_grounding(occurrence.evidence_state.grounding)
        value = occurrence
    else:
        raise InspectionError("unsupported report type")
    return value, payload


def _print(value: object) -> None:
    sys.stdout.buffer.write(canonical_bytes(value) + b"\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aire-prime")
    commands = parser.add_subparsers(dest="command", required=True)
    schema = commands.add_parser("schema")
    schema.add_subparsers(dest="schema_command", required=True).add_parser("check")
    registry = commands.add_parser("registry")
    verify = registry.add_subparsers(dest="registry_command", required=True).add_parser("verify")
    verify.add_argument("path", type=Path)
    for experiment in ("e1", "e2"):
        experiment_parser = commands.add_parser(experiment)
        run = experiment_parser.add_subparsers(dest="experiment_command", required=True).add_parser(
            "run"
        )
        run.add_argument("--seed", type=int, required=True)
        run.add_argument("--output", type=Path, required=True)
    report = commands.add_parser("report")
    show = report.add_subparsers(dest="report_command", required=True).add_parser("show")
    show.add_argument("path", type=Path)
    return parser


def run_cli(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "schema":
            schema_root = files("aire_prime").joinpath("schemas")
            if not schema_root.is_dir():
                schema_root = Path(__file__).resolve().parents[1] / "schemas"
            if not schemas_current(schema_root):
                raise InspectionError("committed schemas are stale")
            _print({"schema_status": "current"})
        elif args.command == "registry":
            events = RegistryStore(args.path).verify()
            if not events:
                raise InspectionError("registry contains no events")
            _print({"events": len(events), "head": events[-1].event_content_id})
        elif args.command in {"e1", "e2"}:
            experiment_report: E1Report | E2Report
            if args.command == "e1":
                experiment_report = run_e1(seed=args.seed, output=args.output).report
            else:
                experiment_report = run_e2(seed=args.seed, output=args.output).report
            pairs: tuple[tuple[str, str], ...]
            if args.command == "e1":
                pairs = (
                    ("agent_requests.jsonl", "agent_responses.jsonl"),
                    ("baseline_requests.jsonl", "baseline_responses.jsonl"),
                )
            else:
                pairs = (
                    ("discovery_request.jsonl", "discovery_response.jsonl"),
                    ("recipient_request.jsonl", "recipient_response.jsonl"),
                    (
                        "reproduction_discovery_request.jsonl",
                        "reproduction_discovery_response.jsonl",
                    ),
                    ("reproduction_request.jsonl", "reproduction_response.jsonl"),
                    *(
                        (f"baseline_{index}_request.jsonl", f"baseline_{index}_response.jsonl")
                        for index in range(3)
                    ),
                    *(
                        (f"ablation_{index}_request.jsonl", f"ablation_{index}_response.jsonl")
                        for index in range(4)
                    ),
                )
            for request_name, response_name in pairs:
                _validate_exchange_pair(args.output / request_name, args.output / response_name)
            _validate_receipts(args.output)
            _print(
                {
                    "report_id": experiment_report.content_id,
                    "failed_gates": experiment_report.failed_gates,
                }
            )
        else:
            if args.path.is_dir():
                _print(_inspect_directory(args.path))
            else:
                value, payload = _inspect_file(args.path)
                if value.content_id != payload["content_id"]:
                    raise InspectionError("report content ID mismatch")
                _print(payload)
        return 0
    except (
        InspectionError,
        RegistryVerificationError,
        ValidationError,
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        print(f"aire-prime: {error}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run_cli())
