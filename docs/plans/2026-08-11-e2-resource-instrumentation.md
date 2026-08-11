# E2 Resource Instrumentation Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Observe elapsed time and peak resident memory for each contained E2 arm without weakening
the existing evidence boundary, then rerun the frozen E2 controls and preserve an honest result.

**Architecture:** Add an optional, typed resource observation to `SubprocessAdapter` at the process
boundary. On the supported macOS backend, use a sealed `/usr/bin/time -l` wrapper and parse only the
allow-listed machine-readable fields; all unsupported or malformed observations remain undetermined.
Thread the observation through `RecipientExchange` and E2 baseline/candidate resource vectors. Do not
put noncanonical host measurements into deterministic contract commitments; report them as observed
run evidence and let the existing comparison/decision logic decide whether matching is valid.

**Tech Stack:** Python 3.12+, standard library `subprocess`/`time`, Pydantic models, pytest,
Hypothesis, Ruff, mypy, uv.

---

### Task 1: Add typed subprocess resource observation

**Files:**
- Modify: `aire_prime/agents/subprocess_adapter.py`
- Test: `tests/agents/test_isolation.py` or a focused new test under `tests/agents/`

**Steps:**

1. Write a failing test for a parser that accepts the supported `/usr/bin/time -l` fields for elapsed
   seconds and maximum resident bytes, rejects missing/nonfinite/negative values, and returns an
   explicit undetermined observation when the platform format is unavailable.
2. Run the focused test and confirm it fails because the observation type/parser does not exist.
3. Add a frozen typed observation model or equivalent dataclass and an allow-listed parser. Store the
   most recent observation on the adapter without changing response wire bytes or failure identities.
4. Wrap only the E2 trusted child command, not arbitrary packet-provided commands; retain sealed-artifact
   attestation and containment checks.
5. Run the focused agent tests and `ruff check` on changed files.

### Task 2: Carry observations through recipient and baseline arms

**Files:**
- Modify: `aire_prime/experiments/e2/recipient.py`
- Modify: `aire_prime/experiments/e2/baselines.py`
- Modify: `aire_prime/measurement/resources.py` only if a typed conversion helper is needed
- Tests: `tests/experiments/e2/test_transfer.py`, `tests/agents/`

**Steps:**

1. Add a failing test that a successful contained recipient exposes elapsed and peak-memory states
   when the adapter supplied valid observations, while an unavailable parser remains undetermined.
2. Run the focused test and confirm failure.
3. Add the typed observation to `RecipientExchange`; build each baseline `ResourceVector` from its own
   exchange observation, preserving packet/operation/interaction counts and explicit unknown states.
4. Ensure no child-controlled stderr narrative, timestamps, or host path enters canonical response IDs.
5. Run E2 transfer tests and the full measurement test suite.

### Task 3: Use observed candidate resources without circular contract commitments

**Files:**
- Modify: `aire_prime/experiments/e2/run.py`
- Tests: `tests/experiments/e2/test_transfer.py`

**Steps:**

1. Add a failing regression test covering observed candidate/control resources and the required behavior
   when they are unequal or partially undetermined.
2. Run it to confirm the current implementation still reports both host dimensions as unknown.
3. Build comparison arms from the actual candidate and baseline exchange observations after the frozen
   evaluation contract is created. Keep the contract’s resource envelope as the predeclared
   instrumentation policy, not a post-hoc measured value.
4. Let `compare_arms` and `decide_improvement` retain `undetermined` or invalid matching outcomes;
   never coerce timing/memory to zero or silently normalize unequal arms.
5. Run focused E2 tests, deterministic claim scans, and the full suite.

### Task 4: Evidence and review update

**Files:**
- Modify: `README.md`, `PROGRESS.md`, `REVIEW.md`, `docs/AIRE_V0_1_STATUS_AND_ROADMAP.md`
- Modify: `docs/AIRE_V0_1_FINAL_EVIDENCE_MATRIX.md` only after fresh evidence exists
- Tests: claim-boundary tests and full release suite

**Steps:**

1. Run seed-202 E2 twice and compare canonical IDs plus observed resource sidecars.
2. Record whether the two dimensions are observed, mismatched, or still undetermined. Preserve failed
   gates and do not promote E2 solely because instrumentation exists.
3. Run Ruff, strict mypy, schema freshness, all tests with coverage, claim scan, and diff checks.
4. Request an adversarial review of the parser, platform boundary, and comparison semantics.
5. Commit the bounded change and push only after the complete gate passes; verify the remote head from a
   clean clone.
