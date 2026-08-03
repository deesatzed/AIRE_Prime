from pathlib import Path

from scripts.export_schemas import SCHEMAS, export_schemas


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.glob("*.json"))}


def test_schema_export_is_deterministic(tmp_path: Path) -> None:
    assert export_schemas(tmp_path)
    first = snapshot(tmp_path)
    assert export_schemas(tmp_path)
    assert snapshot(tmp_path) == first
    assert len(first) == len(SCHEMAS) == 7
    assert all(b'"content_id"' in schema for schema in first.values())
    assert all(b'"label"' not in schema for schema in first.values())


def test_schema_check_rejects_obsolete_files(tmp_path: Path) -> None:
    assert export_schemas(tmp_path)
    (tmp_path / "obsolete.schema.json").write_bytes(b"{}\n")
    assert not export_schemas(tmp_path, check=True)
