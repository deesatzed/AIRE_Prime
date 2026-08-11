import base64
import hashlib
import json
import pickle
import sys
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pytest

from aire_prime.agents.ingress import IngressRejection, ingest_envelope_jsonl
from aire_prime.agents.protocol import (
    AgentRequest,
    AgentResponse,
    DeclaredInput,
    MessageKind,
    ProtocolFailureCode,
)
from aire_prime.agents.roles import AgentIdentity, Role
from aire_prime.agents.subprocess_adapter import (
    PathAllowance,
    PreparedExecution,
    SubprocessAdapter,
    TrustedCommand,
)
from aire_prime.core.canonical import canonical_bytes, content_id
from aire_prime.exchange.audit import realize_with_registry_evidence
from aire_prime.exchange.realize import RealizationContext, Realizer
from aire_prime.exchange.receipt import FailureCode, RealizationReceipt
from aire_prime.grc.constructor import ConstructorPlan, OperationSpec, ResourceBudget
from aire_prime.grc.types import SpaceKind, StructuralType
from aire_prime.registry.store import RegistryStore

OBJECT_ID = "sha256:" + "a" * 64
INPUT_ID = "sha256:" + "b" * 64
CLAIM_ID = "sha256:" + "c" * 64


def _context(inputs: Mapping[str, object]) -> RealizationContext:
    return RealizationContext(
        receiver_id="receiver:adversarial",
        local_realization_id="local:adversarial",
        inputs=inputs,
        budget=ResourceBudget(
            max_operations=4,
            max_elements=128,
            max_output_bytes=1024,
            max_elapsed_seconds=1.0,
        ),
        contract_tests=("task-12-hostile-packet",),
    )


def _plan(operation: OperationSpec, *, dependencies: tuple[str, ...] = ("x",)) -> ConstructorPlan:
    return ConstructorPlan(
        object_id=OBJECT_ID,
        dependencies=dependencies,
        operations=(operation,),
        output_ref="output",
        output_type=StructuralType(kind=SpaceKind.VECTOR, dimensions=(1,)),
    )


def _audited_realize(
    path: Path,
    attack: str,
    plan: ConstructorPlan,
    inputs: Mapping[str, object],
) -> RealizationReceipt:
    store = RegistryStore(path)
    outcome, event = realize_with_registry_evidence(
        Realizer(),
        plan,
        _context(inputs),
        registry=store,
        actor_role="adversary",
        actor_id="agent:task12-adversary",
        attack_label=attack,
    )
    events = store.verify()
    assert events[-1].event_content_id == event.event_content_id
    stored = RealizationReceipt.model_validate_json(events[-1].object_payload_json)
    assert stored == outcome.receipt
    assert events[-1].object_id == content_id(outcome.receipt)
    return outcome.receipt


def _request() -> AgentRequest:
    return AgentRequest(
        message_kind=MessageKind.REALIZE_REQUEST,
        sender=AgentIdentity(agent_id="agent:proposer", role=Role.PROPOSER),
        receiver=AgentIdentity(agent_id="agent:receiver", role=Role.RECEIVER),
        claim_id=CLAIM_ID,
        content_ids=(INPUT_ID,),
        declared_inputs=(DeclaredInput(name="packet", content_id=INPUT_ID),),
    )


def _hostile_wire(field: str, value: object) -> bytes:
    payload = _request().identity_payload()
    payload[field] = value
    return canonical_bytes({**payload, "content_id": content_id(payload)}) + b"\n"


def _assert_registered_ingress_rejection(
    path: Path,
    wire: bytes,
    expected: ProtocolFailureCode,
    *,
    max_input_bytes: int = 65_536,
) -> IngressRejection:
    store = RegistryStore(path)
    result = ingest_envelope_jsonl(
        wire,
        registry=store,
        actor_role="adversary",
        actor_id="agent:task12-adversary",
        max_input_bytes=max_input_bytes,
    )
    assert result.envelope is None
    assert result.rejection is not None
    assert result.rejection.failure.code is expected
    events = store.verify()
    assert events[-1].event_content_id == result.registry_event_id
    stored = IngressRejection.model_validate_json(events[-1].object_payload_json)
    assert stored == result.rejection
    assert stored.wire_content_id == "sha256:" + hashlib.sha256(wire).hexdigest()
    assert stored.failure.detail_content_id == content_id(
        {"failure_code": expected.value}
    )
    assert stored.failure.detail_content_id != stored.wire_content_id
    return stored


def test_valid_ingress_returns_typed_envelope_without_failure_event(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "valid.jsonl")
    request = _request()

    result = ingest_envelope_jsonl(
        request.to_jsonl(),
        registry=store,
        actor_role="receiver",
        actor_id="agent:receiver",
    )

    assert result.envelope == request
    assert result.rejection is None
    assert result.registry_event_id is None
    assert store.verify() == ()


def test_malformed_json_is_typed_and_registered(tmp_path: Path) -> None:
    wire = b'{"not":\n'

    rejection = _assert_registered_ingress_rejection(
        tmp_path / "malformed.jsonl",
        wire,
        ProtocolFailureCode.MALFORMED_JSON,
    )

    assert rejection.failure.detail_content_id != rejection.wire_content_id


@pytest.mark.parametrize(
    ("attack", "primitive"),
    (
        ("source-string", "__import__('os').system('touch should-not-exist')"),
        ("path-traversal", "../../../../bin/sh"),
        ("subprocess-request", "subprocess.run"),
        ("hidden-environment-request", "os.environ"),
    ),
)
def test_executable_channel_attacks_are_typed_and_registered_at_ingress(
    tmp_path: Path, attack: str, primitive: str
) -> None:
    marker = tmp_path / "must-not-exist"
    wire = _hostile_wire(attack, {"primitive": primitive, "sentinel": str(marker)})

    _assert_registered_ingress_rejection(
        tmp_path / f"{attack}.jsonl",
        wire,
        ProtocolFailureCode.PROTOCOL_VIOLATION,
    )

    assert not marker.exists()


def test_pickle_payload_is_data_not_executable_and_is_registered(tmp_path: Path) -> None:
    marker = tmp_path / "pickle-executed"

    class Sentinel:
        def __reduce__(self) -> tuple[object, tuple[str]]:
            import os

            return os.system, (f"/usr/bin/touch {marker}",)

    payload = base64.b64encode(pickle.dumps(Sentinel())).decode("ascii")
    wire = _hostile_wire("pickle_payload", payload)

    _assert_registered_ingress_rejection(
        tmp_path / "pickle.jsonl",
        wire,
        ProtocolFailureCode.PROTOCOL_VIOLATION,
    )

    assert not marker.exists()


def test_oversized_tensor_is_typed_and_registered(tmp_path: Path) -> None:
    receipt = _audited_realize(
        tmp_path / "oversized.jsonl",
        "oversized-tensor",
        _plan(OperationSpec(id="output", primitive="identity", inputs=("x",))),
        {"x": np.zeros(129)},
    )

    assert len(receipt.failures) == 1
    assert receipt.failures[0].code is FailureCode.RESOURCE_INFEASIBLE
    assert receipt.resources.operation_count == 0


def test_recursive_reference_is_typed_and_registered(tmp_path: Path) -> None:
    receipt = _audited_realize(
        tmp_path / "recursive.jsonl",
        "recursive-reference",
        _plan(
            OperationSpec(id="output", primitive="identity", inputs=("output",)),
            dependencies=(),
        ),
        {},
    )

    assert len(receipt.failures) == 1
    assert receipt.failures[0].code is FailureCode.CONSTRUCTOR_FAILURE
    assert receipt.resources.operation_count == 0


def test_oversized_wire_is_typed_and_registered_before_parsing(tmp_path: Path) -> None:
    wire = _hostile_wire("oversized_tensor", "x" * 1024)

    rejection = _assert_registered_ingress_rejection(
        tmp_path / "oversized-wire.jsonl",
        wire,
        ProtocolFailureCode.EXCESS_INPUT,
        max_input_bytes=128,
    )

    assert rejection.failure.detail_content_id != rejection.wire_content_id


def test_content_id_mismatch_becomes_typed_registered_protocol_failure(tmp_path: Path) -> None:
    request = _request()
    tampered = json.loads(request.to_jsonl())
    tampered["claim_id"] = "sha256:" + "d" * 64
    wire = json.dumps(tampered, separators=(",", ":"), sort_keys=True).encode() + b"\n"

    rejection = _assert_registered_ingress_rejection(
        tmp_path / "content-id.jsonl",
        wire,
        ProtocolFailureCode.PROTOCOL_VIOLATION,
    )

    assert rejection.failure.detail_content_id != rejection.wire_content_id


class _DirectTestContainment:
    @property
    def available(self) -> bool:
        return True

    def prepare(
        self,
        *,
        trusted_command: TrustedCommand,
        working_directory: Path,
        allowed_read_paths: tuple[PathAllowance, ...],
        allowed_write_paths: tuple[PathAllowance, ...],
    ) -> PreparedExecution:
        del working_directory, allowed_read_paths, allowed_write_paths
        return PreparedExecution(argv=trusted_command.execution_argv())


def _run_hostile_child(
    tmp_path: Path,
    *,
    name: str,
    output: bytes,
) -> tuple[AgentResponse, IngressRejection]:
    script = tmp_path / f"{name}.py"
    script.write_text(
        "import sys\nsys.stdin.read()\nsys.stdout.buffer.write(" + repr(output) + ")\n"
    )
    store = RegistryStore(tmp_path / f"{name}.jsonl")
    request = _request()
    adapter = SubprocessAdapter(
        trusted_command=TrustedCommand.attest((sys.executable, str(script))),
        working_directory=tmp_path,
        containment_backend=_DirectTestContainment(),
        evidence_registry=store,
    )

    response = adapter.run(request)
    event = store.verify()[-1]
    rejection = IngressRejection.model_validate_json(event.object_payload_json)
    assert event.object_id == rejection.content_id
    return response, rejection


def test_actual_subprocess_ingress_registers_child_content_id_rejection(
    tmp_path: Path,
) -> None:
    request = _request()
    tampered = json.loads(
        AgentRequest(
            message_kind=MessageKind.REALIZE_REQUEST,
            sender=request.sender,
            receiver=request.receiver,
            claim_id=request.claim_id,
            content_ids=request.content_ids,
            declared_inputs=request.declared_inputs,
        ).to_jsonl()
    )
    tampered["message_kind"] = "response"
    tampered["request_content_id"] = request.content_id
    tampered["sender"], tampered["receiver"] = tampered["receiver"], tampered["sender"]
    tampered.pop("claim_id")
    tampered.pop("declared_inputs")
    tampered["content_id"] = "sha256:" + "0" * 64
    output = json.dumps(tampered, separators=(",", ":"), sort_keys=True) + "\n"
    script = tmp_path / "hostile-child.py"
    script.write_text("import sys\nsys.stdin.read()\nsys.stdout.write(" + repr(output) + ")\n")
    store = RegistryStore(tmp_path / "adapter-evidence.jsonl")
    adapter = SubprocessAdapter(
        trusted_command=TrustedCommand.attest((sys.executable, str(script))),
        working_directory=tmp_path,
        containment_backend=_DirectTestContainment(),
        evidence_registry=store,
    )

    response = adapter.run(request)

    assert response.failures[0].code is ProtocolFailureCode.PROTOCOL_VIOLATION
    event = store.verify()[-1]
    rejection = IngressRejection.model_validate_json(event.object_payload_json)
    assert rejection.failure.code is ProtocolFailureCode.PROTOCOL_VIOLATION
    assert event.object_id == rejection.content_id


@pytest.mark.parametrize(
    ("attack", "expected"),
    (
        ("request-instead-of-response", ProtocolFailureCode.PROTOCOL_VIOLATION),
        ("wrong-request-link", ProtocolFailureCode.PROTOCOL_VIOLATION),
        ("role-conflict", ProtocolFailureCode.ROLE_CONFLICT),
        ("file-access-field", ProtocolFailureCode.UNDECLARED_FILE_ACCESS),
    ),
)
def test_actual_adapter_registers_schema_valid_semantic_rejections(
    tmp_path: Path,
    attack: str,
    expected: ProtocolFailureCode,
) -> None:
    request = _request()
    if attack == "request-instead-of-response":
        output = request.to_jsonl()
    else:
        response = AgentResponse(
            message_kind=MessageKind.RESPONSE,
            request_content_id=(
                "sha256:" + "e" * 64
                if attack == "wrong-request-link"
                else request.content_id
            ),
            sender=(
                AgentIdentity(agent_id="agent:intruder", role=Role.RECEIVER)
                if attack == "role-conflict"
                else request.receiver
            ),
            receiver=request.sender,
        )
        if attack == "file-access-field":
            payload = response.identity_payload()
            payload["file_access"] = "../../secret"
            output = canonical_bytes(
                {**payload, "content_id": content_id(payload)}
            ) + b"\n"
        else:
            output = response.to_jsonl()

    returned, rejection = _run_hostile_child(
        tmp_path,
        name=attack,
        output=output,
    )

    assert returned.failures[0].code is expected
    assert rejection.failure.code is expected
    assert rejection.failure.detail_content_id == content_id(
        {"failure_code": expected.value}
    )
