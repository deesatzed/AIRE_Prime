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
from aire_prime.agents.subprocess_adapter import SubprocessAdapter

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
        command=(sys.executable, str(script)),
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
    assert len(outcome.failures[0].counterexample or "") <= 128


def test_excess_input_returns_distinct_typed_failure(tmp_path: Path) -> None:
    script = write_script(tmp_path / "unused.py", "raise SystemExit(99)\n")
    outcome = SubprocessAdapter(
        command=(sys.executable, str(script)),
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
    assert "7" in outcome.failures[0].message


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


def test_timeout_includes_escaped_descendant_holding_output_pipe(tmp_path: Path) -> None:
    script = write_script(
        tmp_path / "escaped_descendant.py",
        "import os, time\n"
        "pid = os.fork()\n"
        "if pid == 0:\n"
        "    os.setsid()\n"
        "    time.sleep(5)\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit(0)\n",
    )
    start = monotonic()
    outcome = adapter(script, timeout=0.05).run(request())

    assert outcome.failures[0].code is ProtocolFailureCode.TIMEOUT
    assert monotonic() - start < 1.0


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
        SubprocessAdapter(command=(), working_directory=tmp_path)
    with pytest.raises(ValueError, match="environment"):
        SubprocessAdapter(
            command=(sys.executable,),
            working_directory=tmp_path,
            environment_allowlist=("AIRE_SECRET_MUST_NOT_LEAK",),
        )
    with pytest.raises(ValueError, match="absolute"):
        SubprocessAdapter(command=("python",), working_directory=tmp_path)
    assert os.path.isdir(tmp_path)
