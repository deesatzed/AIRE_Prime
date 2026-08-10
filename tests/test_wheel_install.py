import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest


def test_built_wheel_installs_cli_and_packaged_schemas(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is required by the documented build workflow")
    root = Path(__file__).resolve().parents[1]
    wheel_dir = tmp_path / "wheel"
    subprocess.run(
        (uv, "build", "--wheel", "--out-dir", str(wheel_dir)),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(wheel_dir.glob("*.whl"))
    with ZipFile(wheel) as archive:
        names = set(archive.namelist())
    assert "aire_prime/schemas/evaluation-contract.schema.json" in names

    environment = tmp_path / "venv"
    subprocess.run(
        (uv, "venv", "--system-site-packages", str(environment)),
        check=True,
        capture_output=True,
        text=True,
    )
    python = environment / "bin" / "python"
    subprocess.run(
        (uv, "pip", "install", "--python", str(python), "--no-deps", str(wheel)),
        check=True,
        capture_output=True,
        text=True,
    )
    executable = environment / "bin" / "aire-prime"
    dependency_path = os.pathsep.join(path for path in sys.path if path.endswith("site-packages"))
    clean_environment = {**os.environ, "PYTHONPATH": dependency_path}
    subprocess.run(
        (str(executable), "--help"),
        cwd=tmp_path,
        env=clean_environment,
        check=True,
        capture_output=True,
        text=True,
    )
    checked = subprocess.run(
        (str(executable), "schema", "check"),
        cwd=tmp_path,
        env=clean_environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"schema_status":"current"' in checked.stdout
