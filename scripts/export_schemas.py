import argparse
from pathlib import Path

from aire_prime.schema import SCHEMAS as SCHEMAS
from aire_prime.schema import export_schemas as export_schemas
from aire_prime.schema import schema_bytes as schema_bytes

__all__ = ["SCHEMAS", "export_schemas", "schema_bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export deterministic AIRE JSON schemas")
    parser.add_argument("--check", action="store_true", help="fail if committed schemas are stale")
    args = parser.parse_args()
    output_dir = Path(__file__).resolve().parents[1] / "schemas"
    return 0 if export_schemas(output_dir, check=args.check) else 1


if __name__ == "__main__":
    raise SystemExit(main())
