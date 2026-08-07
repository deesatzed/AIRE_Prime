# AIRE Prime Remaining-Steps Master Goal Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use @executing-plans to implement this plan task-by-task.

**Goal:** Execute `GOAL_REMAINING_STEPS.md` through a protected Q12D baseline and a remotely
checkpointed, evidence-bounded AIRE Prime v0.1 feature branch.

**Architecture:** Treat the master goal as a strict phase state machine. Preserve Q12D in a
separate repository, close the Task 7 containment gate, then execute the existing canonical Tasks
8--12 plan with progress, review, commit, push, and remote-verification checkpoints after every
phase.

**Tech Stack:** Python 3.12+, Pydantic, NumPy, pytest/Hypothesis, Ruff, mypy, JSON Schema, Git,
platform containment backends, standard-library argparse.

---

### Task 1: Establish the recoverable baseline

**Files:**
- Modify: `PROGRESS.md`
- Reference: `DECISIONS.md`
- Reference: `GOAL_REMAINING_STEPS.md`

**Steps:**

1. Fetch and inspect branch, upstream, worktrees, status, logs, reflogs, and Git object integrity.
2. Inventory the legacy Q12D sources without modifying them.
3. Record the starting commits, dirty state, assumptions, recovery findings, and next action.
4. Run `git diff --check` and review the progress-only diff.
5. Commit with `docs: record remaining-steps execution baseline`, push, and verify the remote head.

### Task 2: Preserve Q12D as an independent repository

**Files:**
- Read: legacy `Q12D.md`, `src/`, and `Quantum Maze Teaching Model Plan/`
- Create in distinct Q12D repository: `RECOVERY_MANIFEST.md`
- Create in distinct Q12D repository: `README.md`
- Create in distinct Q12D repository: copied legacy sources

**Steps:**

1. Resolve a distinct destination and already authorized remote; stop if ownership or visibility
   would have to be invented.
2. Generate source hashes, byte counts, and modification times.
3. Copy without moving or deleting originals.
4. Regenerate hashes in the destination and verify exact equality.
5. Document that this is a recovered teaching artifact and hypothesis, not a validated simulator.
6. Commit the baseline, push it, and verify the remote commit from a fresh read-only checkout.
7. Record the Q12D commit and remote proof in AIRE `PROGRESS.md` without committing Q12D content.

### Task 3: Close Task 7 containment

**Files:**
- Modify: `aire_prime/agents/`
- Modify: `tests/agents/`
- Modify: `README.md`
- Modify: `PROGRESS.md`
- Modify: `DECISIONS.md`
- Modify: `REVIEW.md`
- Modify: `docs/AIRE_V0_1_STATUS_AND_ROADMAP.md`

**Steps:**

1. Write failing integration tests for undeclared file read/write, loopback/external network,
   descendant creation, inherited descriptors, unavailable backend, and artifact swap.
2. Run the focused tests and preserve the intended failures.
3. Write and review the containment-backend decision, including supported platforms and fail-closed
   behavior.
4. Implement the minimum backend and immutable/pinned execution path needed to pass the tests.
5. Run focused agent tests after every batch.
6. Run specification, security, code-quality, and test-gap reviews; adjudicate every finding.
7. Run the full suite, Ruff, mypy, schema check, and diff check.
8. Update truth/evidence documents with exact commands and remaining limitations.
9. Commit the security phase, push, and verify the remote head before Task 4.

### Task 4: Implement and verify E1

**Files:**
- Create/modify: `aire_prime/experiments/e1/`
- Create/modify: `tests/experiments/e1/`
- Modify: `PROGRESS.md`

**Steps:** Follow Task 8 in `docs/plans/2026-08-03-aire-prime-v0.1-implementation.md`, including
RED/GREEN evidence, matched baselines, two seed-101 deterministic runs, full checks, focused commit,
push, and remote verification.

### Task 5: Implement Measurement Layer Zero

**Files:**
- Create/modify: `aire_prime/measurement/`
- Create/modify: `tests/measurement/`
- Modify: `PROGRESS.md`

**Steps:** Follow Task 9 in the canonical plan, preserving missing resources as `undetermined`,
then run focused/full checks, commit, push, and verify the remote head.

### Task 6: Implement and verify simulated E2

**Files:**
- Create/modify: `aire_prime/experiments/e2/`
- Create/modify: `tests/experiments/e2/`
- Modify: `PROGRESS.md`

**Steps:** Follow Task 10 in the canonical plan, including preregistered seed commitments,
matched controls, causal/sham ablations, fresh-recipient transfer, transformed tests, two seed-202
runs, claim scans, focused/full checks, commit, push, and remote verification.

### Task 7: Add the CLI and end-to-end reproduction

**Files:**
- Create: `aire_prime/cli.py`
- Create: `aire_prime/__main__.py`
- Create/modify: `tests/test_cli.py`
- Create/modify: `tests/test_end_to_end.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `PROGRESS.md`

**Steps:** Follow Task 11 in the canonical plan. Require at least 90% measured coverage, reproduce
E1/E2, verify both registries, commit, push, and verify the remote head.

### Task 8: Run adversarial release hardening

**Files:**
- Create: `docs/AIRE_V0_1_EVIDENCE.md`
- Create/modify: `tests/adversarial/`
- Modify as findings require: `aire_prime/`, `tests/`, and truth files

**Steps:** Follow Task 12 in the canonical plan. Run claim, covert-channel, containment, packet,
metric-gaming, test-gap, security, and reproducibility reviews; resolve and re-review every Critical
or Important finding; then commit, push, and verify the remote head.

### Task 9: Final evidence and remote handoff

**Files:**
- Modify: `README.md`
- Modify: `PROGRESS.md`
- Modify: `DECISIONS.md`
- Modify: `REVIEW.md`
- Modify: `docs/AIRE_V0_1_STATUS_AND_ROADMAP.md`
- Create or modify: final evidence matrix under `docs/`

**Steps:**

1. Map every master-goal criterion to current evidence.
2. Run the full release gate and fresh-clone reproduction.
3. Confirm all claims match the observed evidence and every limitation remains visible.
4. Run `git diff --check` and confirm only intended AIRE files changed.
5. Commit the final handoff, push, and confirm local `HEAD` equals the remote feature head.
6. Mark the goal complete only if the protected Q12D remote proof and every AIRE gate are green.

## Execution Handoff

Run `/goal GOAL_REMAINING_STEPS.md` from the durable feature worktree. Use @executing-plans for the
ordered implementation, @verification-before-completion at each claimed phase boundary, and the
review skills named by the goal. Do not start Task 8 implementation while Task 7 remains red.
