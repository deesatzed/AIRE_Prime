import argparse
import json
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Export deterministic AIRE JSON schemas")
    parser.add_argument("--check", action="store_true", help="fail if committed schemas are stale")
    args = parser.parse_args()
    output_dir = Path(__file__).resolve().parents[1] / "schemas"
    return 0 if export_schemas(output_dir, check=args.check) else 1


if __name__ == "__main__":
    raise SystemExit(main())
