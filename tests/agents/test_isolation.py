import json
import os
import platform
import shlex
import shutil
import socket
import sys
from pathlib import Path
from time import monotonic
from typing import Any

import pytest

from aire_prime.agents import subprocess_adapter as subprocess_adapter_module
from aire_prime.agents.protocol import (
    AgentRequest,
    AgentResponse,
    DeclaredInput,
    MessageKind,
    ProtocolFailureCode,
)
from aire_prime.agents.roles import AgentIdentity, Role
from aire_prime.agents.subprocess_adapter import (
    MacOSSandboxBackend,
    PreparedExecution,
    SubprocessAdapter,
    TrustedCommand,
)

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
        containment_backend=DirectTestContainmentBackend(),
    )


class UnavailableContainmentBackend:
    @property
    def available(self) -> bool:
        return False


class DirectTestContainmentBackend:
    """Test-only execution path for protocol mechanics, never production containment."""

    @property
    def available(self) -> bool:
        return True

    def prepare(
        self,
        *,
        trusted_command: TrustedCommand,
        working_directory: Path,
        allowed_read_paths: tuple[Path, ...],
        allowed_write_paths: tuple[Path, ...],
    ) -> PreparedExecution:
        del working_directory, allowed_read_paths, allowed_write_paths
        return PreparedExecution(argv=trusted_command.execution_argv())


def test_unavailable_containment_backend_fails_closed(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-run"
    script = write_script(
        tmp_path / "agent.py",
        "import pathlib\npathlib.Path(" + repr(str(marker)) + ").write_text('ran')\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest((sys.executable, str(script))),
        working_directory=tmp_path,
        containment_backend=UnavailableContainmentBackend(),
    )

    outcome = configured.run(request())

    assert outcome.failures[0].code.value == "ContainmentUnavailable"
    assert not marker.exists()


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_backend_is_available_on_supported_host() -> None:
    backend_type = getattr(subprocess_adapter_module, "MacOSSandboxBackend", None)

    assert backend_type is not None
    assert shutil.which("sandbox-exec") == "/usr/bin/sandbox-exec"
    assert backend_type().available is True


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_availability_requires_functional_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(MacOSSandboxBackend, "sandbox_executable", Path("/usr/bin/false"))

    assert MacOSSandboxBackend().available is False


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_fails_closed_on_unreviewed_os_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess_adapter_module.platform,
        "mac_ver",
        lambda: ("99.0", ("", "", ""), ""),
    )

    assert MacOSSandboxBackend().available is False


def test_platform_selector_fails_closed_off_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess_adapter_module.sys, "platform", "linux")

    backend = subprocess_adapter_module._platform_containment_backend()

    assert backend.available is False


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_fails_closed_on_unreviewed_architecture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subprocess_adapter_module.platform, "machine", lambda: "x86_64")

    assert MacOSSandboxBackend().available is False


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_denies_undeclared_file_read(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    secret = tmp_path / "undeclared-secret.txt"
    secret.write_text("must-not-be-readable\n")
    script = write_script(
        tmp_path / "read-secret.sh",
        "#!/bin/sh\n"
        "IFS= read -r _request || exit 10\n"
        "if IFS= read -r leaked < "
        + shlex.quote(str(secret))
        + "; then\n"
        "  printf '%s\\n' \"$leaked\"\n"
        "  exit 41\n"
        "fi\n"
        "printf '%s' "
        + shlex.quote(response_jsonl)
        + "\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/bin/sh", str(script))),
        working_directory=tmp_path,
        containment_backend=MacOSSandboxBackend(),
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics
    assert "must-not-be-readable" not in outcome.model_dump_json()


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_denies_undeclared_metadata_probe(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    sentinel = tmp_path / "metadata-sentinel.txt"
    sentinel.write_text("exists\n")
    script = write_script(
        tmp_path / "metadata-probe.sh",
        "#!/bin/sh\n"
        "IFS= read -r _request || exit 10\n"
        "if [ -e "
        + shlex.quote(str(sentinel))
        + " ]; then exit 41; fi\n"
        "printf '%s' "
        + shlex.quote(response_jsonl)
        + "\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/bin/sh", str(script))),
        working_directory=tmp_path,
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_overrides_imported_system_file_allowances(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    script = write_script(
        tmp_path / "read-system-secret.sh",
        "#!/bin/sh\n"
        "IFS= read -r _request || exit 10\n"
        "if IFS= read -r leaked < /private/etc/passwd; then exit 41; fi\n"
        "printf '%s' "
        + shlex.quote(response_jsonl)
        + "\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/bin/sh", str(script))),
        working_directory=tmp_path,
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_default_adapter_uses_fail_closed_platform_containment(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    marker = tmp_path / "default-must-not-write"
    script = write_script(
        tmp_path / "default-containment.sh",
        "#!/bin/sh\n"
        "IFS= read -r _request || exit 10\n"
        "printf 'escaped\\n' > "
        + shlex.quote(str(marker))
        + " 2>/dev/null || true\n"
        "printf '%s' "
        + shlex.quote(response_jsonl)
        + "\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/bin/sh", str(script))),
        working_directory=tmp_path,
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics
    assert not marker.exists()


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_allows_only_declared_file_paths(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    declared_input = tmp_path / "declared-input.txt"
    declared_input.write_text("declared-value\n")
    output_directory = tmp_path / "allowed-output"
    output_directory.mkdir()
    output = output_directory / "result.txt"
    script = write_script(
        tmp_path / "declared-paths.sh",
        "#!/bin/sh\n"
        "IFS= read -r _request || exit 10\n"
        "IFS= read -r value < "
        + shlex.quote(str(declared_input))
        + " || exit 11\n"
        "printf '%s\\n' \"$value\" > "
        + shlex.quote(str(output))
        + " || exit 12\n"
        "printf '%s' "
        + shlex.quote(response_jsonl)
        + "\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/bin/sh", str(script))),
        working_directory=tmp_path,
        allowed_read_paths=(declared_input,),
        allowed_write_paths=(output_directory,),
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics
    assert output.read_text() == "declared-value\n"


def _local_nonloopback_address() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        return str(probe.getsockname()[0])
    finally:
        probe.close()


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
@pytest.mark.parametrize("address_kind", ("loopback", "external-interface"))
def test_macos_containment_denies_network_connections(
    tmp_path: Path, address_kind: str
) -> None:
    agent_request = request()
    host = "127.0.0.1" if address_kind == "loopback" else _local_nonloopback_address()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", 0))
    listener.listen()
    port = int(listener.getsockname()[1])
    control = socket.create_connection((host, port), timeout=1)
    accepted, _ = listener.accept()
    control.close()
    accepted.close()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    script = write_script(
        tmp_path / f"network-{address_kind}.pl",
        "use strict; use warnings; use IO::Socket::INET; use Errno qw(EPERM EACCES);\n"
        "scalar <STDIN>;\n"
        f"my $socket = IO::Socket::INET->new(PeerAddr => {host!r}, "
        f"PeerPort => {port}, Proto => 'tcp');\n"
        "if (defined $socket) { close $socket; exit 41; }\n"
        "exit 42 unless $!{EPERM} || $!{EACCES};\n"
        f"print {json.dumps(response_jsonl)};\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/usr/bin/perl", str(script))),
        working_directory=tmp_path,
    )
    try:
        outcome = configured.run(agent_request)
        listener.settimeout(0.1)
        with pytest.raises(TimeoutError):
            listener.accept()
    finally:
        listener.close()

    assert outcome == expected_response(agent_request), configured.diagnostics


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_denies_routed_nonlocal_address(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        control.connect(("192.0.2.1", 9))
    finally:
        control.close()
    script = write_script(
        tmp_path / "network-routed-nonlocal.pl",
        "use strict; use warnings; use IO::Socket::INET; use Errno qw(EPERM EACCES);\n"
        "scalar <STDIN>;\n"
        "my $socket = IO::Socket::INET->new(PeerAddr => '192.0.2.1', "
        "PeerPort => 9, Proto => 'udp');\n"
        "if (defined $socket) { close $socket; exit 41; }\n"
        "exit 42 unless $!{EPERM} || $!{EACCES};\n"
        f"print {json.dumps(response_jsonl)};\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/usr/bin/perl", str(script))),
        working_directory=tmp_path,
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_denies_descendant_fork(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    marker = tmp_path / "forked-descendant"
    script = write_script(
        tmp_path / "fork.pl",
        "use strict; use warnings; use Errno qw(EPERM EACCES EAGAIN);\n"
        "scalar <STDIN>;\n"
        "my $pid = fork();\n"
        "if (!defined $pid) {\n"
        "  exit 42 unless $!{EPERM} || $!{EACCES} || $!{EAGAIN};\n"
        f"  print {json.dumps(response_jsonl)}; exit 0;\n"
        "}\n"
        "if ($pid == 0) {\n"
        f"  open(my $file, '>', {str(marker)!r}) or exit 43;\n"
        "  print $file 'escaped'; close $file; exit 0;\n"
        "}\n"
        "waitpid($pid, 0); exit 41;\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/usr/bin/perl", str(script))),
        working_directory=tmp_path,
        allowed_write_paths=(tmp_path,),
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics
    assert not marker.exists()


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_does_not_inherit_undeclared_descriptor(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    secret = tmp_path / "descriptor-secret.txt"
    secret.write_text("must-not-cross-descriptor-boundary\n")
    descriptor = os.open(secret, os.O_RDONLY)
    os.set_inheritable(descriptor, True)
    script = write_script(
        tmp_path / "descriptor.sh",
        "#!/bin/sh\n"
        "IFS= read -r _request || exit 10\n"
        "if IFS= read -r leaked <&"
        + str(descriptor)
        + "; then\n"
        "  printf '%s\\n' \"$leaked\"\n"
        "  exit 41\n"
        "fi\n"
        "printf '%s' "
        + shlex.quote(response_jsonl)
        + "\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/bin/sh", str(script))),
        working_directory=tmp_path,
    )
    try:
        outcome = configured.run(agent_request)
    finally:
        os.close(descriptor)

    assert outcome == expected_response(agent_request)
    assert "must-not-cross-descriptor-boundary" not in outcome.model_dump_json()


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_executes_pinned_artifact_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    marker = tmp_path / "swapped-artifact-ran"
    script = write_script(
        tmp_path / "approved.sh",
        "#!/bin/sh\n"
        "IFS= read -r _request || exit 10\n"
        "printf '%s' "
        + shlex.quote(response_jsonl)
        + "\n",
    )
    backend = MacOSSandboxBackend()
    assert backend.available
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/bin/sh", str(script))),
        working_directory=tmp_path,
        allowed_write_paths=(tmp_path,),
        containment_backend=backend,
    )
    real_popen = subprocess_adapter_module.subprocess.Popen

    def swapping_popen(*args: Any, **kwargs: Any) -> Any:
        script.write_text("#!/bin/sh\nprintf escaped > " + shlex.quote(str(marker)) + "\n")
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(subprocess_adapter_module.subprocess, "Popen", swapping_popen)

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics
    assert not marker.exists()


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_snapshot_descriptor_is_read_only(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    script = write_script(
        tmp_path / "read-only-snapshot.sh",
        "#!/bin/sh\n"
        "IFS= read -r _request || exit 10\n"
        "if printf 'mutated\\n' > \"$0\" 2>/dev/null; then exit 41; fi\n"
        "printf '%s' "
        + shlex.quote(response_jsonl)
        + "\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/bin/sh", str(script))),
        working_directory=tmp_path,
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request)


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_rejects_allowlist_path_type_swap(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    allowed = tmp_path / "allowed"
    allowed.write_text("approved-file\n")
    script = write_script(
        tmp_path / "allowlist-swap.sh",
        "#!/bin/sh\n"
        "IFS= read -r _request || exit 10\n"
        "if IFS= read -r leaked < "
        + shlex.quote(str(allowed / "undeclared-child"))
        + "; then exit 41; fi\n"
        "printf '%s' "
        + shlex.quote(response_jsonl)
        + "\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/bin/sh", str(script))),
        working_directory=tmp_path,
        allowed_read_paths=(allowed,),
    )
    allowed.unlink()
    allowed.mkdir()
    (allowed / "undeclared-child").write_text("must-not-be-readable\n")

    outcome = configured.run(agent_request)

    assert outcome.failures[0].code is ProtocolFailureCode.CONTAINMENT_UNAVAILABLE


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_enforces_child_descriptor_ceiling(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    script = write_script(
        tmp_path / "descriptor-limit.pl",
        "use strict; use warnings; use Errno qw(EMFILE);\n"
        "scalar <STDIN>; my @handles;\n"
        "for (1..400) {\n"
        "  my $handle;\n"
        "  if (!open($handle, '<', '/dev/null')) {\n"
        "    exit 42 unless $!{EMFILE};\n"
        f"    print {json.dumps(response_jsonl)}; exit 0;\n"
        "  }\n"
        "  push @handles, $handle;\n"
        "}\n"
        "exit 41;\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/usr/bin/perl", str(script))),
        working_directory=tmp_path,
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_macos_containment_denies_undeclared_executable(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    script = write_script(
        tmp_path / "exec-denial.pl",
        "use strict; use warnings; use Errno qw(EPERM EACCES);\n"
        "scalar <STDIN>;\n"
        "exec '/usr/bin/true';\n"
        "exit 42 unless $!{EPERM} || $!{EACCES};\n"
        f"print {json.dumps(response_jsonl)};\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/usr/bin/perl", str(script))),
        working_directory=tmp_path,
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS containment backend")
def test_reviewed_shell_launcher_cannot_expand_child_authority(tmp_path: Path) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    sentinel = tmp_path / "launcher-sentinel.txt"
    sentinel.write_text("must-not-be-readable\n")
    shell_command = (
        "if IFS= read -r leaked < "
        + shlex.quote(str(sentinel))
        + "; then exit 41; fi; printf '%s' "
        + shlex.quote(response_jsonl)
    )
    script = write_script(
        tmp_path / "launcher-reexec.pl",
        "use strict; use warnings;\n"
        "scalar <STDIN>;\n"
        f"exec '/bin/bash', '-c', {json.dumps(shell_command)};\n"
        "exit 42;\n",
    )
    configured = SubprocessAdapter(
        trusted_command=TrustedCommand.attest(("/usr/bin/perl", str(script))),
        working_directory=tmp_path,
    )

    outcome = configured.run(agent_request)

    assert outcome == expected_response(agent_request), configured.diagnostics


def test_subprocess_uses_explicit_cwd_minimal_env_and_jsonl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent_request = request()
    response_jsonl = expected_response(agent_request).to_jsonl().decode()
    monkeypatch.setenv("AIRE_SECRET_MUST_NOT_LEAK", "secret")
    captured_environment: dict[str, str] = {}
    real_popen = subprocess_adapter_module.subprocess.Popen

    def capturing_popen(*args: Any, **kwargs: Any) -> Any:
        captured_environment.update(kwargs["env"])
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(subprocess_adapter_module.subprocess, "Popen", capturing_popen)
    script = write_script(
        tmp_path / "agent.py",
        "import os, sys\n"
        "line = sys.stdin.buffer.readline()\n"
        "if not line.endswith(b'\\n'): raise SystemExit(11)\n"
        "if os.getcwd() != " + repr(str(tmp_path)) + ": raise SystemExit(12)\n"
        "if (os.getenv('LANG'), os.getenv('LC_ALL'), os.getenv('TZ')) != "
        "('C', 'C', 'UTC'): raise SystemExit(13)\n"
        "sys.stdout.write(" + repr(response_jsonl) + ")\n",
    )

    outcome = adapter(script).run(agent_request)

    assert outcome == expected_response(agent_request)
    assert captured_environment == {"LANG": "C", "LC_ALL": "C", "TZ": "UTC"}


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
        containment_backend=DirectTestContainmentBackend(),
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


def test_timeout_terminates_child_process_group(tmp_path: Path) -> None:
    marker = tmp_path / "escaped-child"
    script = write_script(
        tmp_path / "escaped_descendant.py",
        "import os, pathlib, sys, time\n"
        "sys.stdin.buffer.readline()\n"
        "pid = os.fork()\n"
        "if pid == 0:\n"
        "    time.sleep(5)\n"
        "    pathlib.Path(" + repr(str(marker)) + ").write_text(str(os.getpid()))\n"
        "raise SystemExit(0)\n",
    )
    start = monotonic()
    outcome = adapter(script, timeout=0.05).run(request())

    assert outcome.failures[0].code is ProtocolFailureCode.TIMEOUT
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
    configured = SubprocessAdapter(
        trusted_command=command,
        working_directory=tmp_path,
        containment_backend=DirectTestContainmentBackend(),
    )
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


@pytest.mark.parametrize("argument", ("agent.py", "--config=agent.py"))
def test_adapter_rejects_unattested_relative_file_arguments(
    tmp_path: Path, argument: str
) -> None:
    write_script(tmp_path / "agent.py", "raise SystemExit(0)\n")

    with pytest.raises(ValueError, match="explicitly classified as literal"):
        TrustedCommand.attest((sys.executable, argument))

    with pytest.raises(ValueError, match="opaque-token syntax"):
        TrustedCommand.attest(
            (sys.executable, argument),
            literal_argument_indexes=(1,),
        )


def test_trusted_command_accepts_explicit_bounded_literal_argument() -> None:
    command = TrustedCommand.attest(
        (sys.executable, "--version"),
        literal_argument_indexes=(1,),
    )

    assert command.literal_argument_indexes == (1,)


def test_trusted_command_rejects_oversized_literal_and_argument_vector() -> None:
    accepted = TrustedCommand.attest(
        (sys.executable, "a" * 64),
        literal_argument_indexes=(1,),
    )
    assert accepted.argv[1] == "a" * 64

    with pytest.raises(ValueError, match="opaque-token syntax"):
        TrustedCommand.attest(
            (sys.executable, "a" * 65),
            literal_argument_indexes=(1,),
        )

    with pytest.raises(ValueError, match="argument vector"):
        TrustedCommand.attest(
            (sys.executable, *("value" for _ in range(64))),
            literal_argument_indexes=tuple(range(1, 65)),
        )


def test_attested_artifacts_bind_file_identity_metadata(tmp_path: Path) -> None:
    script = write_script(tmp_path / "agent.py", "raise SystemExit(0)\n")
    command = TrustedCommand.attest((sys.executable, str(script)))
    script_artifact = next(item for item in command.artifacts if item.path == str(script))

    assert script_artifact.device >= 0
    assert script_artifact.inode > 0
    assert script_artifact.size == script.stat().st_size


def test_trusted_command_bounds_artifact_descriptors(tmp_path: Path) -> None:
    paths = tuple(
        str(write_script(tmp_path / f"artifact-{index}.txt", str(index)))
        for index in range(64)
    )

    with pytest.raises(ValueError, match="at most 64"):
        TrustedCommand.attest((sys.executable, *paths))


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
