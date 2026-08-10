import json
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from aire_prime.objects.contracts import BridgeContract, EvaluationContract
from aire_prime.objects.proposals import MetricProposal, RealityObject, SenseProposal
from aire_prime.objects.reports import ImprovementReport, OccurrenceReport

SCHEMAS: dict[str, type[BaseModel]] = {
    "bridge-contract": BridgeContract,
    "evaluation-contract": EvaluationContract,
    "improvement-report": ImprovementReport,
    "metric-proposal": MetricProposal,
    "occurrence-report": OccurrenceReport,
    "reality-object": RealityObject,
    "sense-proposal": SenseProposal,
}


def schema_bytes(model: type[BaseModel]) -> bytes:
    schema: dict[str, Any] = model.model_json_schema(mode="serialization")
    return (json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def export_schemas(output_dir: Path, *, check: bool = False) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_paths = {output_dir / f"{name}.schema.json" for name in SCHEMAS}
    current = not check or set(output_dir.glob("*.schema.json")) == expected_paths
    for name, model in sorted(SCHEMAS.items()):
        path = output_dir / f"{name}.schema.json"
        expected = schema_bytes(model)
        if check:
            current = path.exists() and path.read_bytes() == expected and current
        else:
            path.write_bytes(expected)
    return current


def schemas_current(output_dir: Traversable) -> bool:
    expected_names = {f"{name}.schema.json" for name in SCHEMAS}
    if not output_dir.is_dir():
        return False
    actual_names = {
        item.name for item in output_dir.iterdir() if item.name.endswith(".schema.json")
    }
    if actual_names != expected_names:
        return False
    return all(
        output_dir.joinpath(f"{name}.schema.json").read_bytes() == schema_bytes(model)
        for name, model in SCHEMAS.items()
    )
