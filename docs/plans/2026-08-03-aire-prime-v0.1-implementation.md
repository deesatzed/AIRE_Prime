# AIRE Prime v0.1 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a deterministic, sandboxed AIRE research kernel that implements Generative Reality Objects, evidence contracts, append-only validation, E1 capability reconstruction, and E2 simulated alien-sense transfer.

**Architecture:** A small Python package provides immutable Pydantic schemas, canonical serialization, a typed hypergraph, an allow-listed constructor interpreter, isolated agent/role protocols, and an append-only evidence registry. E1 and E2 run as deterministic experiments through the same contracts and report surfaces that later AI adapters will use; v0.1 does not execute arbitrary packet code or claim physical grounding.

**Tech Stack:** Python 3.12+, uv, Pydantic 2, NumPy, pytest, Hypothesis, Ruff, mypy

---

## Execution status -- 2026-08-04

- Tasks 1--4 are implemented and independently reviewed on `feature/aire-v0.1` through commit
  `9498c4c`.
- Verified baseline: 45 tests pass; Ruff, strict mypy, deterministic schema export, and
  `git diff --check` pass.
- Tasks 1--4 establish the project scaffold, immutable content identity, minimal GRC structural
  kernel, and seven evidence-gated exchange objects. They do not establish capability transfer or
  alien-sense occurrence.
- Tasks 5--7 are the next dependency-ordered implementation group. Their completion contract is
  [`GOAL_NEXT_TASKS_GROUP.md`](../../GOAL_NEXT_TASKS_GROUP.md).
- Tasks 8--10 are the experimental proof group. Tasks 11--12 are integration, reproducibility, and
  adversarial release gates.

See [`docs/AIRE_V0_1_STATUS_AND_ROADMAP.md`](../AIRE_V0_1_STATUS_AND_ROADMAP.md) for the distinction
between verified implementation, potential value, and the question answered by each remaining
task.

---

## Preconditions and boundaries

- Read `docs/plans/2026-08-03-aire-prime-design.md` before implementation.
- Use @test-driven-development for every task.
- Use @verification-before-completion before any completion claim.
- Work on a feature branch or dedicated worktree, not directly on `main`.
- Do not add the pre-existing untracked `Q12D.md`, `src/`, or `Quantum Maze Teaching Model Plan/` files to AIRE commits.
- Do not add cloud-provider dependencies, model credentials, network calls, arbitrary code execution, physical device control, or production deployment.
- Treat E2 as `G-S` simulated evidence only.
- Keep proposer, validator, and authorizer as distinct role identifiers in every experiment record.

## Task 1: Create the clean Python project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `aire_prime/__init__.py`
- Create: `aire_prime/py.typed`
- Create: `tests/test_package.py`

**Step 1: Write the failing package test**

```python
# tests/test_package.py
from aire_prime import __version__


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"
```

**Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest tests/test_package.py -v
```

Expected: FAIL because the package and project metadata do not exist.

**Step 3: Add project metadata**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "aire-prime"
version = "0.1.0"
description = "Evidence-gated AI Reality Engineering research kernel"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "numpy>=2.2,<3",
  "pydantic>=2.11,<3",
]

[dependency-groups]
dev = [
  "hypothesis>=6.130,<7",
  "mypy>=1.15,<2",
  "pytest>=8.3,<9",
  "pytest-cov>=6,<7",
  "ruff>=0.11,<1",
]

[tool.hatch.build.targets.wheel]
packages = ["aire_prime"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["aire_prime"]
```

```python
# aire_prime/__init__.py
"""AIRE Prime research kernel."""

__version__ = "0.1.0"
```

Create an empty `aire_prime/py.typed` marker.

**Step 4: Add the README boundary statement**

The README must state:

- AIRE is an experimental methodology, not a superintelligence claim.
- v0.1 supports only E1 and simulated E2.
- packets cannot execute arbitrary code.
- simulated evidence is never physical evidence.
- the canonical design is `docs/plans/2026-08-03-aire-prime-design.md`.

**Step 5: Sync and run the test**

Run:

```bash
uv sync --dev
uv run pytest tests/test_package.py -v
```

Expected: one passing test.

**Step 6: Run formatting and type checks**

Run:

```bash
uv run ruff check .
uv run mypy
```

Expected: both commands succeed with no errors.

**Step 7: Commit**

```bash
git add pyproject.toml uv.lock README.md aire_prime/__init__.py aire_prime/py.typed tests/test_package.py
git commit -m "build: scaffold AIRE Prime Python package"
```

## Task 2: Implement canonical serialization and immutable identity

**Files:**
- Create: `aire_prime/core/__init__.py`
- Create: `aire_prime/core/model.py`
- Create: `aire_prime/core/canonical.py`
- Test: `tests/core/test_canonical.py`

**Step 1: Write failing canonicalization tests**

```python
# tests/core/test_canonical.py
import math

import pytest

from aire_prime.core.canonical import canonical_bytes, content_id


def test_canonical_bytes_ignore_mapping_insertion_order() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert canonical_bytes(left) == canonical_bytes(right)
    assert content_id(left) == content_id(right)


def test_canonical_bytes_reject_non_finite_float() -> None:
    with pytest.raises(ValueError, match="finite"):
        canonical_bytes({"bad": math.nan})
```

**Step 2: Run the tests to verify failure**

Run:

```bash
uv run pytest tests/core/test_canonical.py -v
```

Expected: FAIL because `aire_prime.core.canonical` is missing.

**Step 3: Implement the frozen base model**

```python
# aire_prime/core/model.py
from pydantic import BaseModel, ConfigDict


class FrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
    )
```

**Step 4: Implement canonical JSON and content identity**

```python
# aire_prime/core/canonical.py
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel


def _normalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, Mapping):
        return {str(key): _normalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("canonical values must be finite")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def content_id(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()
```

**Step 5: Run tests and quality checks**

Run:

```bash
uv run pytest tests/core/test_canonical.py -v
uv run ruff check aire_prime tests
uv run mypy
```

Expected: all commands pass.

**Step 6: Commit**

```bash
git add aire_prime/core tests/core
git commit -m "feat: add canonical object identity"
```

## Task 3: Implement the minimal GRC type and hypergraph kernel

**Files:**
- Create: `aire_prime/grc/__init__.py`
- Create: `aire_prime/grc/types.py`
- Create: `aire_prime/grc/graph.py`
- Test: `tests/grc/test_graph.py`
- Test: `tests/grc/test_types.py`

**Step 1: Write failing structural-type tests**

```python
# tests/grc/test_types.py
import pytest

from aire_prime.grc.types import SpaceKind, StructuralType


def test_structural_type_requires_positive_dimensions() -> None:
    with pytest.raises(ValueError):
        StructuralType(kind=SpaceKind.VECTOR, dimensions=(0,))


def test_human_label_is_not_part_of_structural_identity() -> None:
    left = StructuralType(kind=SpaceKind.VECTOR, dimensions=(4,), label="phase")
    right = StructuralType(kind=SpaceKind.VECTOR, dimensions=(4,), label="unnamed")
    assert left.structural_signature() == right.structural_signature()
```

**Step 2: Write the failing hypergraph reference test**

```python
# tests/grc/test_graph.py
import pytest
from pydantic import ValidationError

from aire_prime.grc.graph import GRCGraph, Hyperedge, Node


def test_hyperedge_rejects_unknown_node_reference() -> None:
    with pytest.raises(ValidationError, match="unknown"):
        GRCGraph(
            nodes=(Node(id="n1", type_ref="scalar"),),
            edges=(Hyperedge(id="e1", sources=("n1",), targets=("missing",)),),
        )
```

**Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest tests/grc/test_types.py tests/grc/test_graph.py -v
```

Expected: FAIL because the GRC modules are missing.

**Step 4: Implement structural types**

Define:

```python
class SpaceKind(str, Enum):
    SCALAR = "scalar"
    VECTOR = "vector"
    TENSOR = "tensor"
    DISTRIBUTION = "distribution"
    GRAPH = "graph"
    MANIFOLD = "manifold"
    OPERATOR = "operator"
    PROCESS = "process"
```

`StructuralType` must contain `kind`, `dimensions`, optional `field`, `unit`, `domain`, `precision`, and an excluded optional human `label`. Validate every dimension as positive. `structural_signature()` must omit `label`.

**Step 5: Implement the attributed hypergraph**

Define frozen `Node`, `Hyperedge`, and `GRCGraph` models. Require unique IDs, at least one source and target per edge, and references only to declared node IDs. Store tuples, never mutable lists.

**Step 6: Run tests and property tests**

Add a Hypothesis test that permuting node input order does not change the graph's canonical content ID after canonical sorting.

Run:

```bash
uv run pytest tests/grc -v
uv run ruff check aire_prime tests
uv run mypy
```

Expected: all tests and checks pass.

**Step 7: Commit**

```bash
git add aire_prime/grc tests/grc
git commit -m "feat: add minimal GRC hypergraph kernel"
```

## Task 4: Define the seven canonical AIRE objects

**Files:**
- Create: `aire_prime/objects/__init__.py`
- Create: `aire_prime/objects/evidence.py`
- Create: `aire_prime/objects/contracts.py`
- Create: `aire_prime/objects/proposals.py`
- Create: `aire_prime/objects/reports.py`
- Test: `tests/objects/test_objects.py`

**Step 1: Write failing evidence-separation tests**

```python
# tests/objects/test_objects.py
from aire_prime.objects.evidence import GroundingClass, OccurrenceMaturity, EvidenceState


def test_occurrence_and_grounding_are_independent_axes() -> None:
    state = EvidenceState(
        occurrence=OccurrenceMaturity.TRANSFERRED,
        grounding=GroundingClass.SIMULATED,
    )
    assert state.display == "O4/G-S"
```

Add tests that:

- every object rejects extra fields;
- an Evaluation Contract requires at least one baseline and hidden test ID;
- a Bridge Contract requires a reality tier and authorization boundary;
- an Improvement Report cannot claim a grounding class absent from its Occurrence Report reference.

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/objects/test_objects.py -v
```

Expected: FAIL because canonical objects are missing.

**Step 3: Implement evidence enums**

Implement exact O0--O4 and G-U/G-S/G-D/G-C/G-P/G-PR enum values. Do not define numeric ordering for grounding classes.

**Step 4: Implement proposals and contracts**

Create frozen models for:

- `SenseProposal`
- `RealityObject`
- `MetricProposal`
- `EvaluationContract`
- `BridgeContract`

Every object includes `schema_version`, `created_at`, `parents`, `validity_region`, and `content_id` derived through canonical serialization. Keep human labels optional and non-normative.

**Step 5: Implement reports**

Create `OccurrenceReport` and `ImprovementReport`. Reports must reference frozen proposal and contract IDs, validator identity, resource measurements, known failures, evidence attachments, and expiration conditions.

**Step 6: Generate and snapshot JSON schemas**

Create `schemas/` and export one JSON Schema per canonical object with a small script at `scripts/export_schemas.py`. The export must be deterministic and checked by a test that re-exporting produces identical bytes.

**Step 7: Run all object checks**

Run:

```bash
uv run pytest tests/objects -v
uv run python scripts/export_schemas.py --check
uv run ruff check aire_prime tests scripts
uv run mypy
```

Expected: all commands pass.

**Step 8: Commit**

```bash
git add aire_prime/objects tests/objects schemas scripts/export_schemas.py
git commit -m "feat: define canonical AIRE evidence objects"
```

## Task 5: Build the allow-listed constructor and realization protocol

**Files:**
- Create: `aire_prime/grc/operations.py`
- Create: `aire_prime/grc/constructor.py`
- Create: `aire_prime/exchange/__init__.py`
- Create: `aire_prime/exchange/receipt.py`
- Create: `aire_prime/exchange/realize.py`
- Test: `tests/exchange/test_realize.py`
- Test: `tests/exchange/test_security.py`

**Step 1: Write failing realization tests**

Test that a constructor composed of `select`, `affine`, and `concat` operations produces the expected array and emits a receipt containing measured resource use.

Test that an unknown operation returns `UnsupportedPrimitive` rather than importing or evaluating code.

Test that exceeding the operation, tensor-size, or elapsed-time budget returns `ResourceInfeasible`.

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/exchange -v
```

Expected: FAIL because the realization protocol is missing.

**Step 3: Implement declarative operations**

The v0.1 operation enum is limited to:

- `identity`
- `constant`
- `select`
- `affine`
- `concat`
- `normalize`
- `threshold`
- `lookup`

Operations accept and return NumPy arrays or JSON-compatible scalars. No operation accepts source strings, module names, paths, URLs, shell commands, pickles, or callables.

**Step 4: Implement resource-metered realization**

Define `ResourceBudget`, `ConstructorPlan`, `RealizationContext`, and `Realizer`. Count operations, maximum elements, output bytes, and elapsed monotonic time. Stop before an operation that would exceed a declared bound.

**Step 5: Implement typed receipts and failures**

`RealizationReceipt` records object ID, receiver ID, local realization ID, contract tests, resources, deviations, and typed failures. A failed receipt is still serializable evidence.

**Step 6: Add hostile-packet tests**

Verify rejection of:

- `__import__` strings;
- file paths;
- non-finite tensors;
- oversized lookup tables;
- recursive operation references;
- undeclared dependencies;
- output outside the declared structural type.

**Step 7: Run tests and quality checks**

Run:

```bash
uv run pytest tests/exchange -v
uv run ruff check aire_prime tests
uv run mypy
```

Expected: all tests and checks pass.

**Step 8: Commit**

```bash
git add aire_prime/grc aire_prime/exchange tests/exchange
git commit -m "feat: add bounded GRO realization protocol"
```

## Task 6: Implement append-only lifecycle and evidence registry

**Files:**
- Create: `aire_prime/registry/__init__.py`
- Create: `aire_prime/registry/events.py`
- Create: `aire_prime/registry/lifecycle.py`
- Create: `aire_prime/registry/store.py`
- Test: `tests/registry/test_lifecycle.py`
- Test: `tests/registry/test_store.py`

**Step 1: Write failing lifecycle tests**

Test valid transitions:

```text
Draft -> Submitted -> Contract-bound -> Validation pending -> Provisional -> Replicated
```

Test that `Rejected -> Provisional` is invalid and that superseding creates a new object ID rather than mutating the old record.

**Step 2: Write failing append-only tests**

Test that:

- every registry event includes the previous event hash;
- changing an earlier JSONL line breaks verification;
- duplicate object IDs with different bytes are rejected;
- failure evidence remains after supersession.

**Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest tests/registry -v
```

Expected: FAIL because registry modules are missing.

**Step 4: Implement lifecycle state and transition table**

Use an explicit mapping of permitted transitions. Do not derive transitions through enum ordering.

**Step 5: Implement the JSONL hash chain**

Each `RegistryEvent` contains:

- sequence number;
- timestamp;
- actor role and ID;
- object ID;
- event type;
- previous event hash;
- payload content ID;
- event content ID.

Use atomic file replacement for appending a verified event. Do not provide update or delete operations.

**Step 6: Run tests and corruption checks**

Run:

```bash
uv run pytest tests/registry -v
uv run ruff check aire_prime tests
uv run mypy
```

Expected: all tests pass, including tamper detection.

**Step 7: Commit**

```bash
git add aire_prime/registry tests/registry
git commit -m "feat: add append-only AIRE evidence registry"
```

## Task 7: Add isolated role and agent exchange interfaces

**Files:**
- Create: `aire_prime/agents/__init__.py`
- Create: `aire_prime/agents/roles.py`
- Create: `aire_prime/agents/protocol.py`
- Create: `aire_prime/agents/subprocess_adapter.py`
- Test: `tests/agents/test_protocol.py`
- Test: `tests/agents/test_isolation.py`

**Step 1: Write failing role-separation tests**

Test that the same role identity cannot be proposer, final validator, and authorizer for one claim. Test that a validator cannot receive hidden proposer context fields.

**Step 2: Write failing JSONL protocol tests**

Define request and response envelopes carrying only object IDs, schema versions, content IDs, declared inputs, and receipts. Test deterministic parsing and rejection of unknown message kinds.

**Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest tests/agents -v
```

Expected: FAIL because role and protocol modules are missing.

**Step 4: Implement the agent protocol**

Define `Role`, `AgentIdentity`, `MessageKind`, `AgentRequest`, and `AgentResponse`. Natural-language sidecars may be logged separately but cannot enter scored packet bytes.

**Step 5: Implement the subprocess adapter**

Use argument arrays with `subprocess.run(..., shell=False)`, a timeout, explicit working directory, a minimal environment allowlist, captured output limits, and JSONL stdin/stdout. Tests use a fixture executable; no real model provider is required.

**Step 6: Verify isolation failures**

Test timeout, malformed JSON, excess output, nonzero exit, undeclared file access requests, and role conflict. Return typed evidence rather than raising unclassified exceptions.

**Step 7: Run all checks**

Run:

```bash
uv run pytest tests/agents -v
uv run ruff check aire_prime tests
uv run mypy
```

Expected: all tests pass.

**Step 8: Commit**

```bash
git add aire_prime/agents tests/agents
git commit -m "feat: add isolated AIRE agent protocol"
```

## Task 8: Implement E1 nonlinguistic capability reconstruction

**Files:**
- Create: `aire_prime/experiments/__init__.py`
- Create: `aire_prime/experiments/e1/__init__.py`
- Create: `aire_prime/experiments/e1/world.py`
- Create: `aire_prime/experiments/e1/tasks.py`
- Create: `aire_prime/experiments/e1/baselines.py`
- Create: `aire_prime/experiments/e1/run.py`
- Test: `tests/experiments/e1/test_world.py`
- Test: `tests/experiments/e1/test_transfer.py`

**Step 1: Write the failing procedural-world tests**

Model components as typed ports, capabilities, costs, and local resource constraints. Test that two different constructions can satisfy the same capability contract and that a hidden resource substitution invalidates a hard-coded instance but not a generative constructor.

**Step 2: Write the failing transfer test**

Agent A's fixture GRO must allow fresh Agent B to:

- realize a capability with different resources;
- compose it with an independent object;
- repair one removed component; and
- pass withheld conformance tests.

The serialized-policy baseline must fail at least the changed-resource test.

**Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest tests/experiments/e1 -v
```

Expected: FAIL because E1 is not implemented.

**Step 4: Implement deterministic world generation**

Generate worlds from an explicit seed. Store the seed in the Evaluation Contract but withhold hidden task details from the proposer. Every component and task must have a canonical content ID.

**Step 5: Implement E1 baselines**

Include bandwidth-matched:

- fixed instance;
- demonstration list;
- lookup policy;
- random opaque packet;
- conventional feature schema.

Do not claim a human-language baseline until an actual language adapter exists.

**Step 6: Emit frozen reports**

E1 must produce:

- Sense Proposal only if a distinction is actually claimed;
- Reality Object;
- Evaluation Contract;
- Bridge Contract;
- Realization Receipts;
- Improvement Report;
- registry events.

**Step 7: Run E1 twice for determinism**

Run:

```bash
uv run python -m aire_prime.experiments.e1.run --seed 101 --output /tmp/aire-e1-a
uv run python -m aire_prime.experiments.e1.run --seed 101 --output /tmp/aire-e1-b
```

Expected: report content IDs match across both runs; timestamps may be stored outside canonical result payloads.

**Step 8: Run tests and commit**

```bash
uv run pytest tests/experiments/e1 -v
git add aire_prime/experiments/e1 tests/experiments/e1
git commit -m "feat: add E1 capability reconstruction experiment"
```

## Task 9: Implement Measurement Layer Zero controls

**Files:**
- Create: `aire_prime/measurement/__init__.py`
- Create: `aire_prime/measurement/resources.py`
- Create: `aire_prime/measurement/ablation.py`
- Create: `aire_prime/measurement/comparison.py`
- Create: `aire_prime/measurement/decision.py`
- Test: `tests/measurement/test_ablation.py`
- Test: `tests/measurement/test_decision.py`

**Step 1: Write failing matched-control tests**

Test that a comparison is invalid when packet bytes, interaction count, elapsed budget, or observation access differ without a declared adjustment.

**Step 2: Write failing ablation tests**

Test targeted ablation, equal-size random-subspace ablation, activation permutation, and representation replacement. The report must retain every control result, not only the best or favorable one.

**Step 3: Write the failing decision-rule test**

Using deterministic bootstrap samples, verify that provisional improvement requires the proposed effect to exceed the maximum matched-control effect by `delta` at confidence `1 - alpha`, while protected dimensions remain above their floors.

**Step 4: Run tests to verify failure**

Run:

```bash
uv run pytest tests/measurement -v
```

Expected: FAIL because Measurement Layer Zero modules are missing.

**Step 5: Implement resource accounting and comparison**

Use a resource vector containing:

- packet bytes;
- peak resident bytes;
- operation count;
- interaction count;
- elapsed time;
- external calls;
- declared energy proxy;
- declared bandwidth.

Missing resource dimensions must be `undetermined`, never silently zero.

**Step 6: Implement deterministic bootstrap decisions**

Require a seed, store the full effect distribution summary, and return `provisional`, `rejected`, or `undetermined`. Do not expose a single generic `better=True` field.

**Step 7: Run tests and commit**

```bash
uv run pytest tests/measurement -v
uv run ruff check aire_prime tests
uv run mypy
git add aire_prime/measurement tests/measurement
git commit -m "feat: add matched AIRE occurrence and improvement controls"
```

## Task 10: Implement E2 simulated alien-sense transfer

**Files:**
- Create: `aire_prime/experiments/e2/__init__.py`
- Create: `aire_prime/experiments/e2/world.py`
- Create: `aire_prime/experiments/e2/discoverer.py`
- Create: `aire_prime/experiments/e2/recipient.py`
- Create: `aire_prime/experiments/e2/baselines.py`
- Create: `aire_prime/experiments/e2/ablations.py`
- Create: `aire_prime/experiments/e2/run.py`
- Test: `tests/experiments/e2/test_world.py`
- Test: `tests/experiments/e2/test_occurrence.py`
- Test: `tests/experiments/e2/test_transfer.py`

**Step 1: Write failing distributed-origin world tests**

Create a synthetic causal world with:

- an unknown starting state distribution;
- latent transition classes omitted from the baseline feature schema;
- identical raw observation and intervention access for all contenders;
- held-out transformations and action-label permutations;
- outcomes that require the latent distinction for efficient prediction or control.

Test that the baseline schema conflates at least one consequential state pair.

**Step 2: Write the failing discovery and transfer tests**

The deterministic reference discoverer must infer a compact action-conditioned latent operator from training interventions and emit a GRO. A fresh recipient must reconstruct the operator and improve on held-out prediction and control tasks.

**Step 3: Write anti-policy tests**

Reveal downstream goals only after transfer. Verify that:

- the transferred object works with a new controller;
- permuted actions can be rebound through declared interfaces;
- a frozen lookup policy fails;
- a bandwidth-matched opaque tensor does not match systematic generalization;
- targeted sense ablation removes more performance than sham ablations.

**Step 4: Run tests to verify failure**

Run:

```bash
uv run pytest tests/experiments/e2 -v
```

Expected: FAIL because E2 is not implemented.

**Step 5: Implement the seeded causal world**

Keep world generation deterministic and separate training, validation, hidden-test, and transformed-test seeds. Store their commitments in the Evaluation Contract before discovery.

**Step 6: Implement reference discoverer and recipient adapters**

The reference algorithm exists to validate the protocol, not to claim general AI discovery. It must use only declared observations and interventions, export its learned operator through allow-listed GRC operations, and run through the same agent protocol available to future AI adapters.

**Step 7: Produce the occurrence classification**

Classify `O4/G-S` only when:

- conditional held-out gain is positive beyond matched controls;
- causal/sham ablation criteria pass;
- transformed-environment generalization passes;
- a fresh recipient reconstructs the sense;
- the Bridge consequence is reproduced in an independent run.

Otherwise emit the lower supported occurrence state and record the failed gate.

**Step 8: Run deterministic E2 verification**

Run:

```bash
uv run python -m aire_prime.experiments.e2.run --seed 202 --output /tmp/aire-e2
uv run pytest tests/experiments/e2 -v
```

Expected: a complete simulated evidence packet and passing tests. The command must never print `new physics` or `superintelligence` as a result classification.

**Step 9: Commit**

```bash
git add aire_prime/experiments/e2 tests/experiments/e2
git commit -m "feat: add E2 simulated alien-sense transfer"
```

## Task 11: Add CLI, evidence inspection, and end-to-end verification

**Files:**
- Create: `aire_prime/cli.py`
- Create: `aire_prime/__main__.py`
- Create: `tests/test_cli.py`
- Create: `tests/test_end_to_end.py`
- Modify: `pyproject.toml`
- Modify: `README.md`

**Step 1: Write failing CLI tests**

Test commands:

```text
aire-prime schema check
aire-prime registry verify PATH
aire-prime e1 run --seed N --output PATH
aire-prime e2 run --seed N --output PATH
aire-prime report show PATH
```

The CLI must return nonzero for registry corruption, contract failure, invalid grounding escalation, or resource-budget violation.

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_cli.py tests/test_end_to_end.py -v
```

Expected: FAIL because the CLI is missing.

**Step 3: Implement a thin argparse CLI**

Use the standard library `argparse`; do not add a CLI framework dependency. CLI handlers call existing library functions and serialize typed reports. Add:

```toml
[project.scripts]
aire-prime = "aire_prime.cli:main"
```

**Step 4: Add end-to-end evidence tests**

The E1 and E2 end-to-end test must verify:

- contracts precede result events;
- proposer, validator, and authorizer IDs differ;
- report object IDs match canonical bytes;
- resources are present or explicitly undetermined;
- evidence is append-only;
- E2 never exceeds G-S;
- failures remain visible after supersession.

**Step 5: Document exact usage and interpretation**

README examples must show how to run E1/E2, inspect evidence, and interpret O/G states. Add a section titled `What passing E2 does not prove`.

**Step 6: Run the full verification suite**

Run:

```bash
uv run ruff check .
uv run mypy
uv run pytest --cov=aire_prime --cov-report=term-missing --cov-fail-under=90
uv run python scripts/export_schemas.py --check
uv run aire-prime e1 run --seed 101 --output /tmp/aire-prime-e1
uv run aire-prime e2 run --seed 202 --output /tmp/aire-prime-e2
uv run aire-prime registry verify /tmp/aire-prime-e1/registry.jsonl
uv run aire-prime registry verify /tmp/aire-prime-e2/registry.jsonl
git diff --check
```

Expected: all checks pass, coverage is at least 90%, and both registries verify.

**Step 7: Commit**

```bash
git add pyproject.toml README.md aire_prime tests
git commit -m "feat: expose verified AIRE v0.1 experiment CLI"
```

## Task 12: Conduct adversarial release review and publish evidence boundaries

**Files:**
- Create: `docs/AIRE_V0_1_EVIDENCE.md`
- Create: `tests/adversarial/test_claim_boundaries.py`
- Create: `tests/adversarial/test_packet_channels.py`
- Create: `tests/adversarial/test_metric_gaming.py`

**Step 1: Write claim-boundary tests**

Scan all CLI report classifications and generated Markdown. Fail if simulated results are labeled physical, if E1/E2 output claims superintelligence or new physics, or if a missing metric is rendered as zero.

**Step 2: Add packet-channel attacks**

Attempt source strings, pickle payloads, path traversal, subprocess requests, oversized tensors, recursive references, hidden environment requests, and content-ID mismatches. Every attack must produce a typed failure and registry evidence.

**Step 3: Add metric-gaming fixtures**

Create agents that maximize novelty by random output, empowerment by consuming all authorized state, prediction by refusing difficult cases, and packet efficiency by relying on undeclared receiver priors. Confirm that protected dimensions or contract checks reject them.

**Step 4: Write the evidence-boundary document**

Document:

- what E1 establishes;
- what E2 establishes;
- evidence maturity and grounding;
- declared baselines;
- known limitations;
- failed attacks and untested threats;
- why v0.1 is not a new-physics or superintelligence claim;
- deferred E3--E5 work.

**Step 5: Invoke independent reviews**

Use @requesting-code-review for correctness and architecture review. Use @test_gap_finder for missing unit, integration, adversarial, and reproducibility tests. Classify each finding as Accepted, Rejected, or Needs Investigation before changing code.

**Step 6: Re-run release verification**

Run:

```bash
uv run ruff check .
uv run mypy
uv run pytest --cov=aire_prime --cov-report=term-missing --cov-fail-under=90
uv run python scripts/export_schemas.py --check
git diff --check
git status --short --branch
```

Expected: all automated checks pass. Only intentional AIRE files are modified; the legacy untracked files remain uncommitted.

**Step 7: Commit the evidence boundary**

```bash
git add docs/AIRE_V0_1_EVIDENCE.md tests/adversarial aire_prime
git commit -m "test: harden AIRE v0.1 evidence boundaries"
```

## Final verification gate

Before claiming v0.1 complete, use @verification-before-completion and confirm:

- every design acceptance criterion has an evidence pointer;
- E1 and E2 reports reproduce from pinned seeds;
- the validator did not share proposer-only context;
- no packet executes arbitrary code;
- occurrence and grounding remain separate;
- E2 is at most O4/G-S;
- matched resource accounting is complete or explicitly undetermined;
- failures and counterexamples remain in the registry;
- no unrelated legacy files are committed;
- the branch is ready for review but not automatically deployed.

## Execution handoff

Plan complete and saved to `docs/plans/2026-08-03-aire-prime-v0.1-implementation.md`. Two execution options:

1. **Subagent-Driven (this session)** -- dispatch a fresh subagent per task with review between tasks. Required sub-skill: `superpowers:subagent-driven-development`.
2. **Parallel Session (separate)** -- open a new session in a dedicated worktree and use `superpowers:executing-plans` with batch checkpoints.
