import os
import selectors
import signal
import subprocess
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Any

from aire_prime.agents.protocol import (
    AgentRequest,
    AgentResponse,
    MessageKind,
    ProtocolFailure,
    ProtocolFailureCode,
)

SAFE_ENVIRONMENT_KEYS = frozenset({"LANG", "LC_ALL", "TZ"})
FILE_ACCESS_FIELDS = frozenset(
    {"file_access", "file_access_request", "file_access_requests", "path_request"}
)


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
        command: tuple[str, ...],
        working_directory: Path,
        timeout_seconds: float = 30.0,
        max_output_bytes: int = 1_000_000,
        max_input_bytes: int = 1_000_000,
        environment_allowlist: tuple[str, ...] = ("LANG", "LC_ALL", "TZ"),
    ) -> None:
        if not command or any(not part for part in command):
            raise ValueError("subprocess command must be a nonempty argument array")
        if not Path(command[0]).is_absolute():
            raise ValueError("subprocess command executable must be an absolute path")
        if not working_directory.is_dir():
            raise ValueError("subprocess working directory must exist")
        if timeout_seconds <= 0:
            raise ValueError("subprocess timeout must be positive")
        if max_output_bytes <= 0 or max_input_bytes <= 0:
            raise ValueError("subprocess input and output bounds must be positive")
        if not set(environment_allowlist) <= SAFE_ENVIRONMENT_KEYS:
            raise ValueError("subprocess environment allowlist contains an unsafe key")
        self._command = command
        self._working_directory = working_directory.resolve()
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._max_input_bytes = max_input_bytes
        self._environment_allowlist = tuple(sorted(set(environment_allowlist)))

    def run(self, request: AgentRequest) -> AgentResponse:
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
                list(self._command),
                shell=False,
                cwd=self._working_directory,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as error:
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

    @staticmethod
    def _failure(
        request: AgentRequest,
        code: ProtocolFailureCode,
        message: str,
        counterexample: str | None = None,
    ) -> AgentResponse:
        return AgentResponse(
            message_kind=MessageKind.FAILURE,
            request_content_id=request.content_id,
            sender=request.receiver,
            receiver=request.sender,
            object_ids=request.object_ids,
            failures=(
                ProtocolFailure(
                    code=code,
                    message=message,
                    counterexample=counterexample,
                ),
            ),
        )
