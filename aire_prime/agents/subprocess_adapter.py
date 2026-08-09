import hashlib
import json
import math
import os
import platform
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
from contextlib import suppress
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from time import monotonic
from typing import Any, Protocol

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

DETERMINISTIC_ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
FILE_ACCESS_FIELDS = frozenset(
    {"file_access", "file_access_request", "file_access_requests", "path_request"}
)
MAX_DIAGNOSTIC_COUNTEREXAMPLE_CHARS = 128
MAX_COMMAND_ARTIFACTS = 64
MAX_COMMAND_ARGUMENTS = 64
MAX_COMMAND_ARGV_BYTES = 8_192
MAX_LITERAL_ARGUMENT_CHARS = 64
MAX_CHILD_OPEN_FILES = 256
RESOURCE_LIMIT_LAUNCHER = (
    "set -e; "
    "ulimit -c 0; "
    f"ulimit -n {MAX_CHILD_OPEN_FILES}; "
    "ulimit -u 0; "
    "ulimit -t 30; "
    "ulimit -f 2048; "
    'exec "$@"'
)


@dataclass(frozen=True)
class PathAllowance:
    path: Path
    is_directory: bool
    device: int
    inode: int

    @classmethod
    def attest(cls, path: Path) -> "PathAllowance":
        resolved = path.resolve(strict=True)
        file_stat = resolved.lstat()
        if not (stat.S_ISREG(file_stat.st_mode) or stat.S_ISDIR(file_stat.st_mode)):
            raise ValueError("allowed path must be a regular file or directory")
        return cls(
            path=resolved,
            is_directory=stat.S_ISDIR(file_stat.st_mode),
            device=file_stat.st_dev,
            inode=file_stat.st_ino,
        )

    def verify(self) -> bool:
        try:
            file_stat = self.path.lstat()
        except OSError:
            return False
        return (
            stat.S_ISDIR(file_stat.st_mode) == self.is_directory
            and (stat.S_ISREG(file_stat.st_mode) or self.is_directory)
            and file_stat.st_dev == self.device
            and file_stat.st_ino == self.inode
        )


class ContainmentBackend(Protocol):
    @property
    def available(self) -> bool: ...

    def prepare(
        self,
        *,
        trusted_command: "TrustedCommand",
        working_directory: Path,
        allowed_read_paths: tuple[PathAllowance, ...],
        allowed_write_paths: tuple[PathAllowance, ...],
    ) -> "PreparedExecution": ...


class ContainmentPreparationError(RuntimeError):
    """The required host containment could not be prepared safely."""


class UnavailableContainmentBackend:
    """Fail-closed backend used when no supported host containment exists."""

    @property
    def available(self) -> bool:
        return False

    def prepare(
        self,
        *,
        trusted_command: "TrustedCommand",
        working_directory: Path,
        allowed_read_paths: tuple[PathAllowance, ...],
        allowed_write_paths: tuple[PathAllowance, ...],
    ) -> "PreparedExecution":
        del trusted_command, working_directory, allowed_read_paths, allowed_write_paths
        raise ContainmentPreparationError("no supported host containment backend is available")


@dataclass
class PreparedExecution:
    argv: tuple[str, ...]
    pass_fds: tuple[int, ...] = ()

    def close(self) -> None:
        for descriptor in self.pass_fds:
            with suppress(OSError):
                os.close(descriptor)


class MacOSSandboxBackend:
    """Fail-closed host containment using the macOS Seatbelt launcher."""

    sandbox_executable = Path("/usr/bin/sandbox-exec")
    _supported_macos_major_versions = frozenset({27})
    _supported_machines = frozenset({"arm64"})
    _trusted_executable_roots = (
        Path("/bin"),
        Path("/sbin"),
        Path("/usr/bin"),
        Path("/usr/sbin"),
        Path("/System"),
    )
    _system_read_roots = (
        Path("/System"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
        Path("/Library/Apple"),
        Path("/private/var/select"),
        Path("/dev/fd"),
        Path("/dev/null"),
        Path("/dev/random"),
        Path("/dev/urandom"),
    )

    @cached_property
    def available(self) -> bool:
        if sys.platform != "darwin":
            return False
        try:
            macos_major = int(platform.mac_ver()[0].split(".", 1)[0])
        except (ValueError, IndexError):
            return False
        if (
            macos_major not in self._supported_macos_major_versions
            or platform.machine() not in self._supported_machines
        ):
            return False
        try:
            file_stat = self.sandbox_executable.stat()
        except OSError:
            return False
        metadata_is_trusted = (
            stat.S_ISREG(file_stat.st_mode)
            and file_stat.st_uid == 0
            and file_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH) == 0
            and os.access(self.sandbox_executable, os.X_OK)
        )
        if not metadata_is_trusted:
            return False
        try:
            probe = subprocess.run(
                [
                    str(self.sandbox_executable),
                    "-p",
                    self._profile(
                        working_directory=Path("/"),
                        executable_path=Path("/usr/bin/true"),
                        allowed_read_paths=(),
                        allowed_write_paths=(),
                    ),
                    "/usr/bin/true",
                ],
                check=False,
                close_fds=True,
                capture_output=True,
                env=DETERMINISTIC_ENVIRONMENT,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return probe.returncode == 0

    @staticmethod
    def _profile_path_filter(path: Path) -> str:
        operation = "subpath" if path.is_dir() else "literal"
        return f"({operation} {json.dumps(str(path))})"

    @staticmethod
    def _allowance_filter(allowance: PathAllowance) -> str:
        operation = "subpath" if allowance.is_directory else "literal"
        return f"({operation} {json.dumps(str(allowance.path))})"

    @classmethod
    def _is_sealed_system_executable(cls, path: Path, file_stat: os.stat_result) -> bool:
        if file_stat.st_uid != 0 or file_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            return False
        return any(
            path == root or path.is_relative_to(root)
            for root in cls._trusted_executable_roots
        )

    @staticmethod
    def _open_verified_artifact(artifact: "CommandArtifact") -> int:
        flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(artifact.resolved_path, flags)
        except OSError as error:
            raise ContainmentPreparationError("trusted artifact could not be pinned") from error
        snapshot_descriptor = -1
        snapshot_path = ""
        try:
            file_stat = os.fstat(descriptor)
            digest = hashlib.sha256()
            snapshot_descriptor, snapshot_path = tempfile.mkstemp(prefix="aire-artifact-")
            while chunk := os.read(descriptor, 1_048_576):
                digest.update(chunk)
                unwritten = memoryview(chunk)
                while unwritten:
                    unwritten = unwritten[os.write(snapshot_descriptor, unwritten) :]
            if (
                not stat.S_ISREG(file_stat.st_mode)
                or f"sha256:{digest.hexdigest()}" != artifact.digest
                or file_stat.st_dev != artifact.device
                or file_stat.st_ino != artifact.inode
                or file_stat.st_size != artifact.size
            ):
                raise ContainmentPreparationError("trusted artifact changed before execution")
            os.fsync(snapshot_descriptor)
            read_flags = os.O_RDONLY | os.O_CLOEXEC
            if hasattr(os, "O_NOFOLLOW"):
                read_flags |= os.O_NOFOLLOW
            return os.open(snapshot_path, read_flags)
        finally:
            os.close(descriptor)
            if snapshot_descriptor >= 0:
                os.close(snapshot_descriptor)
            if snapshot_path:
                with suppress(OSError):
                    os.unlink(snapshot_path)

    def _profile(
        self,
        *,
        working_directory: Path,
        executable_path: Path,
        allowed_read_paths: tuple[PathAllowance, ...],
        allowed_write_paths: tuple[PathAllowance, ...],
    ) -> str:
        read_filters = " ".join(
            (
                f"(literal {json.dumps(str(working_directory))})",
                *(
                    self._profile_path_filter(path)
                    for path in self._system_read_roots
                ),
                *(self._allowance_filter(item) for item in allowed_read_paths),
            )
        )
        write_filters = " ".join(
            (
                self._profile_path_filter(Path("/dev/null")),
                *(self._allowance_filter(item) for item in allowed_write_paths),
            )
        )
        working_directory_metadata_rule = (
            ""
            if working_directory == Path("/")
            else "(allow file-read-metadata file-test-existence "
            f"(literal {json.dumps(str(working_directory))}) "
            f"(path-ancestors {json.dumps(str(working_directory))}))"
        )
        return " ".join(
            (
                "(version 1)",
                "(deny default)",
                '(import "system.sb")',
                '(deny file-read* (literal "/private/etc/master.passwd") '
                '(literal "/private/etc/passwd"))',
                '(deny file-write* (subpath "/cores"))',
                "(allow process-exec "
                f"(literal {json.dumps('/bin/sh')}) "
                f"(literal {json.dumps('/bin/bash')}) "
                f"(literal {json.dumps(str(executable_path))}))",
                working_directory_metadata_rule,
                f"(allow file-read* {read_filters})",
                f"(allow file-write* {write_filters})",
                "(deny network*)",
                "(deny process-fork)",
            )
        )

    def prepare(
        self,
        *,
        trusted_command: "TrustedCommand",
        working_directory: Path,
        allowed_read_paths: tuple[PathAllowance, ...],
        allowed_write_paths: tuple[PathAllowance, ...],
    ) -> PreparedExecution:
        if not self.available:
            raise ContainmentPreparationError("macOS containment backend is unavailable")
        if not all(
            allowance.verify() for allowance in (*allowed_read_paths, *allowed_write_paths)
        ):
            raise ContainmentPreparationError("allowed filesystem path changed before execution")
        descriptors: dict[str, int] = {}
        try:
            for artifact in trusted_command.artifacts:
                descriptors[artifact.path] = self._open_verified_artifact(artifact)
            executable_artifact = next(
                artifact
                for artifact in trusted_command.artifacts
                if artifact.path == trusted_command.argv[0]
            )
            executable_path = Path(executable_artifact.resolved_path)
            executable_stat = executable_path.stat()
            if not self._is_sealed_system_executable(executable_path, executable_stat):
                raise ContainmentPreparationError(
                    "contained command executable must be on the sealed root-owned system volume"
                )
            execution_argv = tuple(
                executable_artifact.resolved_path
                if index == 0
                else f"/dev/fd/{descriptors[argument]}"
                if argument in descriptors
                else argument
                for index, argument in enumerate(trusted_command.argv)
            )
            profile = self._profile(
                working_directory=working_directory,
                executable_path=executable_path,
                allowed_read_paths=allowed_read_paths,
                allowed_write_paths=allowed_write_paths,
            )
            pass_fds = tuple(descriptors.values())
            if any(descriptor >= MAX_CHILD_OPEN_FILES for descriptor in pass_fds):
                raise ContainmentPreparationError(
                    "artifact descriptor exceeds the contained open-file ceiling"
                )
            return PreparedExecution(
                argv=(
                    str(self.sandbox_executable),
                    "-p",
                    profile,
                    "/bin/sh",
                    "-c",
                    RESOURCE_LIMIT_LAUNCHER,
                    "aire-resource-launcher",
                    *execution_argv,
                ),
                pass_fds=pass_fds,
            )
        except BaseException:
            for descriptor in descriptors.values():
                with suppress(OSError):
                    os.close(descriptor)
            raise


def _platform_containment_backend() -> ContainmentBackend:
    if sys.platform == "darwin":
        return MacOSSandboxBackend()
    return UnavailableContainmentBackend()


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
    literal_argument_indexes: tuple[int, ...] = ()

    @field_validator("argv")
    @classmethod
    def require_fixed_absolute_command(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not part or "\0" in part for part in value):
            raise ValueError("trusted command must be a nonempty argument array")
        if len(value) > MAX_COMMAND_ARGUMENTS or sum(
            len(argument.encode("utf-8")) for argument in value
        ) > MAX_COMMAND_ARGV_BYTES:
            raise ValueError("trusted command argument vector exceeds its deterministic bound")
        if not Path(value[0]).is_absolute():
            raise ValueError("trusted command executable must be an absolute path")
        return value

    @field_validator("artifacts")
    @classmethod
    def normalize_artifacts(
        cls, value: tuple[CommandArtifact, ...]
    ) -> tuple[CommandArtifact, ...]:
        if len(value) > MAX_COMMAND_ARTIFACTS:
            raise ValueError("trusted command may attest at most 64 artifacts")
        paths = [artifact.path for artifact in value]
        if len(paths) != len(set(paths)):
            raise ValueError("trusted command artifact paths must be unique")
        return tuple(sorted(value, key=lambda artifact: artifact.path))

    @field_validator("literal_argument_indexes")
    @classmethod
    def normalize_literal_argument_indexes(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(index <= 0 for index in value) or len(value) != len(set(value)):
            raise ValueError("literal argument indexes must be unique positive indexes")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def require_complete_attestation(self) -> "TrustedCommand":
        required_paths = {argument for argument in self.argv if Path(argument).is_absolute()}
        artifact_paths = {artifact.path for artifact in self.artifacts}
        nonabsolute_indexes = {
            index
            for index, argument in enumerate(self.argv)
            if index > 0 and not Path(argument).is_absolute()
        }
        if set(self.literal_argument_indexes) != nonabsolute_indexes:
            raise ValueError(
                "every non-absolute command argument must be explicitly classified as literal"
            )
        if any(
            len(self.argv[index]) > MAX_LITERAL_ARGUMENT_CHARS
            or re.fullmatch(
                r"(?:--?[a-z0-9][a-z0-9-]*|[a-z0-9][a-z0-9_-]*|[0-9]+)",
                self.argv[index],
            )
            is None
            for index in self.literal_argument_indexes
        ):
            raise ValueError("literal command arguments must use the bounded opaque-token syntax")
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
    def attest(
        cls,
        argv: tuple[str, ...],
        *,
        literal_argument_indexes: tuple[int, ...] = (),
    ) -> "TrustedCommand":
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
        return cls(
            argv=argv,
            artifacts=tuple(artifacts),
            literal_argument_indexes=literal_argument_indexes,
        )

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
        containment_backend: ContainmentBackend | None = None,
        allowed_read_paths: tuple[Path, ...] = (),
        allowed_write_paths: tuple[Path, ...] = (),
    ) -> None:
        if not working_directory.is_dir():
            raise ValueError("subprocess working directory must exist")
        resolved_working_directory = working_directory.resolve()
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
        if not set(environment_allowlist) <= DETERMINISTIC_ENVIRONMENT.keys():
            raise ValueError("subprocess environment allowlist contains an unsafe key")
        self._trusted_command = trusted_command
        self._working_directory = resolved_working_directory
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._max_input_bytes = max_input_bytes
        self._environment_allowlist = tuple(sorted(set(environment_allowlist)))
        self._containment_backend = (
            _platform_containment_backend()
            if containment_backend is None
            else containment_backend
        )
        self._allowed_read_paths = tuple(PathAllowance.attest(path) for path in allowed_read_paths)
        self._allowed_write_paths = tuple(
            PathAllowance.attest(path) for path in allowed_write_paths
        )
        self._diagnostics: list[FailureDiagnostic] = []

    @property
    def diagnostics(self) -> tuple[FailureDiagnostic, ...]:
        return tuple(self._diagnostics)

    def run(self, request: AgentRequest) -> AgentResponse:
        self._diagnostics.clear()
        if not self._containment_backend.available:
            return self._failure(
                request,
                ProtocolFailureCode.CONTAINMENT_UNAVAILABLE,
                "required subprocess containment backend is unavailable",
            )
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
            key: DETERMINISTIC_ENVIRONMENT[key] for key in self._environment_allowlist
        }
        prepared: PreparedExecution | None = None
        try:
            prepared = self._containment_backend.prepare(
                trusted_command=self._trusted_command,
                working_directory=self._working_directory,
                allowed_read_paths=self._allowed_read_paths,
                allowed_write_paths=self._allowed_write_paths,
            )
            process = subprocess.Popen(
                list(prepared.argv),
                shell=False,
                cwd=self._working_directory,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
                start_new_session=True,
                pass_fds=prepared.pass_fds,
            )
        except ContainmentPreparationError as error:
            return self._failure(
                request,
                ProtocolFailureCode.CONTAINMENT_UNAVAILABLE,
                "required subprocess containment could not be prepared",
                str(error),
            )
        except (OSError, subprocess.SubprocessError) as error:
            return self._failure(
                request,
                ProtocolFailureCode.EXECUTION_ERROR,
                "agent subprocess could not start",
                str(error),
            )
        finally:
            if prepared is not None:
                prepared.close()

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
