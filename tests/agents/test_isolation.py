import os
import sys
from pathlib import Path
from time import monotonic

import pytest

from aire_prime.agents.protocol import (
    AgentRequest,
    AgentResponse,
    DeclaredInput,
    MessageKind,
    ProtocolFailureCode,
)
from aire_prime.agents.roles import AgentIdentity, Role
from aire_prime.agents.subprocess_adapter import SubprocessAdapter, TrustedCommand

CLAIM_ID = "sha256:" + "5" * 64
OBJECT_ID = "sha256:" + "6" * 64


def identity(role: Role, suffix: str) -> AgentIdentity:
    return AgentIdentity(agent_id=f"agent:{suffix}", role=role)


def request() -> AgentRequest:
    return AgentRequest(
        message_kind=MessageKind.VALIDATE_REQUEST,
        sender=identity(Role.PROPOSER, "proposer"),
        receiver=identity(Role.VALIDATOR, "validator"),
        claim_id=CLAIM_ID,
        object_ids=(OBJECT_ID,),
    )


def expected_response(agent_request: AgentRequest) -> AgentResponse:
    return AgentResponse(
        message_kind=MessageKind.RESPONSE,
        request_content_id=agent_request.content_id,
        sender=agent_request.receiver,
        receiver=agent_request.sender,
        object_ids=agent_request.object_ids,
    )


def write_script(path: Path, source: str) -> Path:
    path.write_text(source)
    return path


def adapter(script: Path, *, output_limit: int = 8_192, timeout: float = 1.0) -> SubprocessAdapter:
    return SubprocessAdapter(
        trusted_command=TrustedCommand.attest((sys.executable, str(script))),
        working_directory=script.parent,
        timeout_seconds=timeout,
        max_output_bytes=output_limit,
    )


def test_subprocess_uses_explicit_cwd_minimal_env_and_jsonl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    monkeypatch.setenv("AIRE_SECRET_MUST_NOT_LEAK", "secret")
    script = write_script(
        tmp_path / "agent.py",
        "import os, sys\n"
        "line = sys.stdin.buffer.readline()\n"
        "if not line.endswith(b'\\n'): raise SystemExit(11)\n"
        "if os.getcwd() != " + repr(str(tmp_path)) + ": raise SystemExit(12)\n"
        "if os.getenv('AIRE_SECRET_MUST_NOT_LEAK'): raise SystemExit(13)\n"
        "sys.stdout.write(" + repr(response_jsonl) + ")\n",
    )

    outcome = adapter(script).run(agent_request)

    assert outcome == expected_response(agent_request)


def test_timeout_returns_typed_failure(tmp_path: Path) -> None:
    script = write_script(tmp_path / "timeout.py", "import time\ntime.sleep(5)\n")
    outcome = adapter(script, timeout=0.05).run(request())
    assert outcome.failures[0].code is ProtocolFailureCode.TIMEOUT


def test_malformed_json_returns_typed_failure(tmp_path: Path) -> None:
    script = write_script(tmp_path / "malformed.py", "print('not-json')\n")
    outcome = adapter(script).run(request())
    assert outcome.failures[0].code is ProtocolFailureCode.MALFORMED_JSON


def test_excess_output_returns_typed_failure(tmp_path: Path) -> None:
    script = write_script(tmp_path / "excess.py", "print('x' * 10_000)\n")
    outcome = adapter(script, output_limit=128).run(request())
    assert outcome.failures[0].code is ProtocolFailureCode.EXCESS_OUTPUT
    assert outcome.failures[0].detail_content_id is not None


def test_excess_input_returns_distinct_typed_failure(tmp_path: Path) -> None:
    script = write_script(tmp_path / "unused.py", "raise SystemExit(99)\n")
    outcome = SubprocessAdapter(
        trusted_command=TrustedCommand.attest((sys.executable, str(script))),
        working_directory=tmp_path,
        max_input_bytes=10,
    ).run(request())
    assert outcome.failures[0].code is ProtocolFailureCode.EXCESS_INPUT


def test_nonzero_exit_returns_typed_failure(tmp_path: Path) -> None:
    script = write_script(
        tmp_path / "nonzero.py",
        "import sys\nsys.stderr.write('bounded failure')\nraise SystemExit(7)\n",
    )
    outcome = adapter(script).run(request())
    assert outcome.failures[0].code is ProtocolFailureCode.NONZERO_EXIT
    assert outcome.failures[0].detail_content_id is not None


def test_undeclared_file_access_request_returns_typed_failure(tmp_path: Path) -> None:
    script = write_script(
        tmp_path / "file_access.py",
        "import json\nprint(json.dumps({'file_access_requests': ['/etc/passwd']}))\n",
    )
    outcome = adapter(script).run(request())
    assert outcome.failures[0].code is ProtocolFailureCode.UNDECLARED_FILE_ACCESS


def test_role_conflict_response_returns_typed_failure(tmp_path: Path) -> None:
    agent_request = request()
    conflict = AgentResponse(
        message_kind=MessageKind.RESPONSE,
        request_content_id=agent_request.content_id,
        sender=identity(Role.AUTHORIZER, "wrong"),
        receiver=agent_request.sender,
    )
    script = write_script(
        tmp_path / "role_conflict.py",
        "import sys\nsys.stdin.buffer.readline()\nsys.stdout.write("
        + repr(conflict.to_jsonl().decode())
        + ")\n",
    )
    outcome = adapter(script).run(agent_request)
    assert outcome.failures[0].code is ProtocolFailureCode.ROLE_CONFLICT


def test_deep_hostile_response_is_contained_as_typed_failure(tmp_path: Path) -> None:
    script = write_script(
        tmp_path / "deep.py",
        "print('[' * 2000 + '0' + ']' * 2000)\n",
    )
    outcome = adapter(script).run(request())
    assert outcome.failures[0].code is ProtocolFailureCode.MALFORMED_JSON


def test_timeout_includes_child_that_never_reads_large_stdin(tmp_path: Path) -> None:
    large_request = AgentRequest(
        message_kind=MessageKind.VALIDATE_REQUEST,
        sender=identity(Role.PROPOSER, "proposer"),
        receiver=identity(Role.VALIDATOR, "validator"),
        claim_id=CLAIM_ID,
        object_ids=(OBJECT_ID,),
        declared_inputs=tuple(
            DeclaredInput(
                name=f"input-{index:05d}",
                content_id="sha256:" + f"{index:064x}",
            )
            for index in range(2_000)
        ),
    )
    script = write_script(tmp_path / "no_read.py", "import time\ntime.sleep(5)\n")
    start = monotonic()
    outcome = adapter(script, timeout=0.05).run(large_request)

    assert outcome.failures[0].code is ProtocolFailureCode.TIMEOUT
    assert monotonic() - start < 1.0


def test_child_cannot_fork_an_escaped_descendant(tmp_path: Path) -> None:
    marker = tmp_path / "escaped-child"
    script = write_script(
        tmp_path / "escaped_descendant.py",
        "import os, pathlib, sys, time\n"
        "sys.stdin.buffer.readline()\n"
        "try:\n"
        "    pid = os.fork()\n"
        "except OSError:\n"
        "    raise SystemExit(23)\n"
        "if pid == 0:\n"
        "    os.setsid()\n"
        "    pathlib.Path(" + repr(str(marker)) + ").write_text(str(os.getpid()))\n"
        "    time.sleep(5)\n"
        "raise SystemExit(0)\n",
    )
    start = monotonic()
    outcome = adapter(script).run(request())

    assert outcome.failures[0].code is ProtocolFailureCode.NONZERO_EXIT
    assert not marker.exists()
    assert monotonic() - start < 1.0


def test_arbitrary_child_output_cannot_exfiltrate_file_contents(tmp_path: Path) -> None:
    secret = "do-not-return-this-secret"
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text(secret)
    script = write_script(
        tmp_path / "exfiltrate.py",
        "import json, pathlib, sys\n"
        "sys.stdin.buffer.readline()\n"
        "print(json.dumps({'secret': pathlib.Path(" + repr(str(secret_path)) + ").read_text()}))\n",
    )

    outcome = adapter(script).run(request())

    assert outcome.failures[0].code is ProtocolFailureCode.MALFORMED_JSON
    assert secret not in outcome.model_dump_json()


def test_attested_command_rejects_artifact_changed_after_configuration(tmp_path: Path) -> None:
    script = write_script(tmp_path / "agent.py", "raise SystemExit(0)\n")
    command = TrustedCommand.attest((sys.executable, str(script)))
    configured = SubprocessAdapter(trusted_command=command, working_directory=tmp_path)
    script.write_text("raise SystemExit(7)\n")

    outcome = configured.run(request())

    assert outcome.failures[0].code is ProtocolFailureCode.EXECUTION_ERROR


def test_trusted_command_rejects_omitted_or_unreferenced_artifacts(tmp_path: Path) -> None:
    script = write_script(tmp_path / "agent.py", "raise SystemExit(0)\n")
    attested = TrustedCommand.attest((sys.executable, str(script)))

    with pytest.raises(ValueError, match="every absolute file argument"):
        TrustedCommand(argv=attested.argv, artifacts=(attested.artifacts[0],))

    unrelated = TrustedCommand.attest((sys.executable,)).artifacts[0].model_copy(
        update={"path": str(tmp_path / "not-an-argument")}
    )
    with pytest.raises(ValueError, match="exactly match"):
        TrustedCommand(argv=attested.argv, artifacts=attested.artifacts + (unrelated,))


def test_attested_artifacts_bind_file_identity_metadata(tmp_path: Path) -> None:
    script = write_script(tmp_path / "agent.py", "raise SystemExit(0)\n")
    command = TrustedCommand.attest((sys.executable, str(script)))
    script_artifact = next(item for item in command.artifacts if item.path == str(script))

    assert script_artifact.device >= 0
    assert script_artifact.inode > 0
    assert script_artifact.size == script.stat().st_size


@pytest.mark.parametrize("timeout", (float("nan"), float("inf")))
def test_nonfinite_timeout_is_rejected(tmp_path: Path, timeout: float) -> None:
    script = write_script(tmp_path / "agent.py", "raise SystemExit(0)\n")
    with pytest.raises(ValueError, match="finite positive number"):
        adapter(script, timeout=timeout)


def test_boolean_timeout_is_rejected(tmp_path: Path) -> None:
    script = write_script(tmp_path / "agent.py", "raise SystemExit(0)\n")
    with pytest.raises(ValueError, match="finite positive number"):
        adapter(script, timeout=True)


def test_hostile_output_cannot_control_failure_reference(tmp_path: Path) -> None:
    first = write_script(tmp_path / "first.py", "print('secret-alpha')\n")
    second = write_script(tmp_path / "second.py", "print('secret-beta')\n")

    first_adapter = adapter(first)
    first_failure = first_adapter.run(request()).failures[0]
    second_failure = adapter(second).run(request()).failures[0]

    assert first_failure.code is ProtocolFailureCode.MALFORMED_JSON
    assert second_failure.code is ProtocolFailureCode.MALFORMED_JSON
    assert first_failure.detail_content_id == second_failure.detail_content_id
    assert len(first_adapter.diagnostics) == 1
    assert first_adapter.diagnostics[0].code is ProtocolFailureCode.MALFORMED_JSON
    assert first_adapter.diagnostics[0].message
    assert first_adapter.diagnostics[0].counterexample is None or len(
        first_adapter.diagnostics[0].counterexample
    ) <= 128


def test_stdout_and_stderr_share_one_aggregate_capture_bound(tmp_path: Path) -> None:
    agent_request = request()
    response = expected_response(agent_request).to_jsonl().decode()
    limit = len(response.encode()) + 50
    script = write_script(
        tmp_path / "aggregate.py",
        "import sys\n"
        "sys.stdin.buffer.readline()\n"
        "sys.stderr.write('e' * 100)\n"
        "sys.stdout.write(" + repr(response) + ")\n",
    )

    outcome = adapter(script, output_limit=limit).run(agent_request)

    assert outcome.failures[0].code is ProtocolFailureCode.EXCESS_OUTPUT


def test_command_and_environment_configuration_rejects_unsafe_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="command"):
        TrustedCommand.attest(())
    command = TrustedCommand.attest((sys.executable,))
    with pytest.raises(ValueError, match="environment"):
        SubprocessAdapter(
            trusted_command=command,
            working_directory=tmp_path,
            environment_allowlist=("AIRE_SECRET_MUST_NOT_LEAK",),
        )
    with pytest.raises(ValueError, match="absolute"):
        TrustedCommand.attest(("python",))
    assert os.path.isdir(tmp_path)
