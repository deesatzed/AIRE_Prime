import hashlib
import math
import os
import resource
import selectors
import signal
import stat
import subprocess
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Any

from pydantic import field_validator, model_validator

from aire_prime.agents.protocol import (
    AgentRequest,
    AgentResponse,
    MessageKind,
    ProtocolFailure,
    ProtocolFailureCode,
)
from aire_prime.core.canonical import content_id
from aire_prime.core.model import FrozenModel
from aire_prime.objects import ContentID

SAFE_ENVIRONMENT_KEYS = frozenset({"LANG", "LC_ALL", "TZ"})
FILE_ACCESS_FIELDS = frozenset(
    {"file_access", "file_access_request", "file_access_requests", "path_request"}
)
MAX_DIAGNOSTIC_COUNTEREXAMPLE_CHARS = 128


class CommandArtifact(FrozenModel):
    """A file dependency bound to the exact bytes approved by the caller."""

    path: str
    resolved_path: str
    digest: ContentID
    device: int
    inode: int
    size: int


class FailureDiagnostic(FrozenModel):
    """Local-only narrative detail that never enters scored protocol bytes."""

    code: ProtocolFailureCode
    message: str
    counterexample: str | None = None

    @field_validator("message")
    @classmethod
    def require_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("failure diagnostic message must be nonblank")
        return value


class TrustedCommand(FrozenModel):
    """A fixed command whose executable and absolute file arguments are attested.

    This is an explicit trusted-computing-base boundary, not a claim that an
    arbitrary executable is made safe by the adapter.
    """

    argv: tuple[str, ...]
    artifacts: tuple[CommandArtifact, ...]

    @field_validator("argv")
    @classmethod
    def require_fixed_absolute_command(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not part or "\0" in part for part in value):
            raise ValueError("trusted command must be a nonempty argument array")
        if not Path(value[0]).is_absolute():
            raise ValueError("trusted command executable must be an absolute path")
        return value

    @field_validator("artifacts")
    @classmethod
    def normalize_artifacts(
        cls, value: tuple[CommandArtifact, ...]
    ) -> tuple[CommandArtifact, ...]:
        paths = [artifact.path for artifact in value]
        if len(paths) != len(set(paths)):
            raise ValueError("trusted command artifact paths must be unique")
        return tuple(sorted(value, key=lambda artifact: artifact.path))

    @model_validator(mode="after")
    def require_complete_attestation(self) -> "TrustedCommand":
        required_paths = {argument for argument in self.argv if Path(argument).is_absolute()}
        artifact_paths = {artifact.path for artifact in self.artifacts}
        if self.argv[0] not in artifact_paths:
            raise ValueError("trusted command executable must have an artifact attestation")
        if artifact_paths != required_paths:
            if not required_paths <= artifact_paths:
                raise ValueError("trusted command must attest every absolute file argument")
            raise ValueError("trusted command artifacts must exactly match absolute file arguments")
        return self

    @staticmethod
    def _inspect(path: Path) -> tuple[Path, ContentID, os.stat_result]:
        resolved = path.resolve(strict=True)
        digest = hashlib.sha256()
        with resolved.open("rb") as stream:
            file_stat = os.fstat(stream.fileno())
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError(f"trusted command artifact is not a file: {path}")
            for chunk in iter(lambda: stream.read(1_048_576), b""):
                digest.update(chunk)
        return resolved, f"sha256:{digest.hexdigest()}", file_stat

    @classmethod
    def attest(cls, argv: tuple[str, ...]) -> "TrustedCommand":
        if not argv or any(not part or "\0" in part for part in argv):
            raise ValueError("trusted command must be a nonempty argument array")
        if not Path(argv[0]).is_absolute():
            raise ValueError("trusted command executable must be an absolute path")
        artifacts: list[CommandArtifact] = []
        for argument in argv:
            path = Path(argument)
            if not path.is_absolute():
                continue
            try:
                resolved, digest, file_stat = cls._inspect(path)
            except OSError as error:
                raise ValueError(f"trusted command artifact does not exist: {argument}") from error
            artifacts.append(
                CommandArtifact(
                    path=argument,
                    resolved_path=str(resolved),
                    digest=digest,
                    device=file_stat.st_dev,
                    inode=file_stat.st_ino,
                    size=file_stat.st_size,
                )
            )
        return cls(argv=argv, artifacts=tuple(artifacts))

    def verify(self) -> bool:
        for artifact in self.artifacts:
            try:
                resolved, digest, file_stat = self._inspect(Path(artifact.path))
                if str(resolved) != artifact.resolved_path:
                    return False
                if (
                    digest != artifact.digest
                    or file_stat.st_dev != artifact.device
                    or file_stat.st_ino != artifact.inode
                    or file_stat.st_size != artifact.size
                ):
                    return False
            except (OSError, ValueError):
                return False
        return True

    def execution_argv(self) -> tuple[str, ...]:
        resolved_by_path = {
            artifact.path: artifact.resolved_path for artifact in self.artifacts
        }
        return tuple(resolved_by_path.get(argument, argument) for argument in self.argv)


def _apply_child_limits() -> None:
    """Apply limits in the child after Popen forks and before it execs."""

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))


@dataclass
class _BoundedCapture:
    data: bytearray = field(default_factory=bytearray)
    total: int = 0

    def add(self, chunk: bytes, *, remaining: int) -> None:
        self.total += len(chunk)
        self.data.extend(chunk[: max(0, remaining)])

    def text(self) -> str:
        return bytes(self.data).decode("utf-8", errors="replace")


class SubprocessAdapter:
    def __init__(
        self,
        *,
        trusted_command: TrustedCommand,
        working_directory: Path,
        timeout_seconds: float = 30.0,
        max_output_bytes: int = 1_000_000,
        max_input_bytes: int = 1_000_000,
        environment_allowlist: tuple[str, ...] = ("LANG", "LC_ALL", "TZ"),
    ) -> None:
        if not working_directory.is_dir():
            raise ValueError("subprocess working directory must exist")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("subprocess timeout must be a finite positive number")
        if (
            isinstance(max_output_bytes, bool)
            or isinstance(max_input_bytes, bool)
            or not isinstance(max_output_bytes, int)
            or not isinstance(max_input_bytes, int)
            or max_output_bytes <= 0
            or max_input_bytes <= 0
        ):
            raise ValueError("subprocess input and output bounds must be positive")
        if not set(environment_allowlist) <= SAFE_ENVIRONMENT_KEYS:
            raise ValueError("subprocess environment allowlist contains an unsafe key")
        self._trusted_command = trusted_command
        self._working_directory = working_directory.resolve()
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._max_input_bytes = max_input_bytes
        self._environment_allowlist = tuple(sorted(set(environment_allowlist)))
        self._diagnostics: list[FailureDiagnostic] = []

    @property
    def diagnostics(self) -> tuple[FailureDiagnostic, ...]:
        return tuple(self._diagnostics)

    def run(self, request: AgentRequest) -> AgentResponse:
        self._diagnostics.clear()
        if not self._trusted_command.verify():
            return self._failure(
                request,
                ProtocolFailureCode.EXECUTION_ERROR,
                "trusted command artifact verification failed",
            )
        input_bytes = request.to_jsonl()
        if len(input_bytes) > self._max_input_bytes:
            return self._failure(
                request,
                ProtocolFailureCode.EXCESS_INPUT,
                "request exceeds the subprocess input bound",
            )

        environment = {
            key: os.environ[key]
            for key in self._environment_allowlist
            if key in os.environ
        }
        try:
            process = subprocess.Popen(
                list(self._trusted_command.execution_argv()),
                shell=False,
                cwd=self._working_directory,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
                start_new_session=True,
                preexec_fn=_apply_child_limits,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return self._failure(
                request,
                ProtocolFailureCode.EXECUTION_ERROR,
                "agent subprocess could not start",
                str(error),
            )

        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        stdout = _BoundedCapture()
        stderr = _BoundedCapture()
        selector = selectors.DefaultSelector()
        streams = (process.stdin, process.stdout, process.stderr)
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        selector.register(process.stdout, selectors.EVENT_READ, stdout)
        selector.register(process.stderr, selectors.EVENT_READ, stderr)
        input_offset = 0
        open_outputs = 2
        total_output = 0
        deadline = monotonic() + self._timeout_seconds
        timed_out = False
        excess_output = False
        return_code: int | None = None
        try:
            while True:
                remaining_time = deadline - monotonic()
                if remaining_time <= 0:
                    timed_out = True
                    break
                return_code = process.poll()
                if return_code is not None and open_outputs == 0:
                    break
                ready = selector.select(timeout=min(remaining_time, 0.05))
                for key, _ in ready:
                    if key.data == "stdin":
                        try:
                            written = os.write(
                                key.fd,
                                input_bytes[input_offset : input_offset + 8_192],
                            )
                            input_offset += written
                        except (BlockingIOError, BrokenPipeError, OSError):
                            input_offset = len(input_bytes)
                        if input_offset >= len(input_bytes):
                            self._close_selector_stream(selector, key.fileobj)
                        continue

                    capture = key.data
                    assert isinstance(capture, _BoundedCapture)
                    try:
                        chunk = os.read(key.fd, 8_192)
                    except BlockingIOError:
                        continue
                    except OSError:
                        chunk = b""
                    if not chunk:
                        self._close_selector_stream(selector, key.fileobj)
                        open_outputs -= 1
                        continue
                    remaining_capture = self._max_output_bytes - len(stdout.data) - len(
                        stderr.data
                    )
                    capture.add(chunk, remaining=remaining_capture)
                    total_output += len(chunk)
                    if total_output > self._max_output_bytes:
                        excess_output = True
                        break
                if excess_output:
                    break
                if process.poll() is not None:
                    self._close_selector_stream(selector, process.stdin)
        finally:
            self._kill_process_group(process)
            if process.poll() is None:
                with suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=0.2)
            for stream in streams:
                with suppress(OSError, ValueError):
                    selector.unregister(stream)
                with suppress(OSError, ValueError):
                    stream.close()
            selector.close()

        if excess_output:
            return self._failure(
                request,
                ProtocolFailureCode.EXCESS_OUTPUT,
                "agent subprocess exceeded its captured-output bound",
                (stdout.text() + stderr.text())[: self._max_output_bytes],
            )
        if timed_out:
            return self._failure(
                request,
                ProtocolFailureCode.TIMEOUT,
                "agent subprocess tree exceeded its timeout",
            )
        assert return_code is not None
        if return_code != 0:
            return self._failure(
                request,
                ProtocolFailureCode.NONZERO_EXIT,
                f"agent subprocess exited with status {return_code}",
                stderr.text(),
            )

        output = bytes(stdout.data)
        file_access = self._detect_file_access(output)
        if file_access is not None:
            return self._failure(
                request,
                ProtocolFailureCode.UNDECLARED_FILE_ACCESS,
                "agent requested undeclared file access",
                file_access,
            )
        try:
            response = AgentResponse.from_jsonl(output)
        except (ValueError, RecursionError) as error:
            return self._failure(
                request,
                ProtocolFailureCode.MALFORMED_JSON,
                "agent returned malformed or noncanonical JSONL",
                str(error),
            )
        if response.request_content_id != request.content_id:
            return self._failure(
                request,
                ProtocolFailureCode.PROTOCOL_VIOLATION,
                "agent response references a different request",
            )
        if response.sender != request.receiver or response.receiver != request.sender:
            return self._failure(
                request,
                ProtocolFailureCode.ROLE_CONFLICT,
                "agent response identities conflict with the request roles",
            )
        return response

    @staticmethod
    def _detect_file_access(output: bytes) -> str | None:
        import json

        try:
            payload = json.loads(output)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
            return None
        if type(payload) is not dict:
            return None
        fields = sorted(FILE_ACCESS_FIELDS & set(payload))
        return ",".join(fields) if fields else None

    @staticmethod
    def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            if process.poll() is None:
                with suppress(OSError):
                    process.kill()

    @staticmethod
    def _close_selector_stream(
        selector: selectors.BaseSelector, stream: Any
    ) -> None:
        with suppress(KeyError, ValueError):
            selector.unregister(stream)
        close = getattr(stream, "close", None)
        if callable(close):
            with suppress(OSError, ValueError):
                close()

    def _failure(
        self,
        request: AgentRequest,
        code: ProtocolFailureCode,
        message: str,
        counterexample: str | None = None,
    ) -> AgentResponse:
        # Raw diagnostic narratives are intentionally excluded from scored wire
        # bytes. A child-controlled counterexample must not become a covert
        # channel through an otherwise opaque content hash.
        detail_content_id = content_id({"failure_code": code.value})
        bounded_counterexample = (
            None
            if counterexample is None
            else counterexample[:MAX_DIAGNOSTIC_COUNTEREXAMPLE_CHARS]
        )
        self._diagnostics.append(
            FailureDiagnostic(
                code=code,
                message=message,
                counterexample=bounded_counterexample,
            )
        )
        return AgentResponse(
            message_kind=MessageKind.FAILURE,
            request_content_id=request.content_id,
            sender=request.receiver,
            receiver=request.sender,
            object_ids=request.object_ids,
            failures=(
                ProtocolFailure(
                    code=code,
                    detail_content_id=detail_content_id,
                ),
            ),
        )
