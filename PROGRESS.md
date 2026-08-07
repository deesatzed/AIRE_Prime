# AIRE Prime Progress

## 2026-08-06 Power-Outage Recovery

- Backed up the four previously local-only commits to
  `origin/feature/aire-v0.1` at `13cd8fa` before reconstruction.
- Recreated the feature worktree at the durable path
  `/Volumes/WS4TB/Q12D/.worktrees/aire-prime-v0.1`.
- Replayed the persisted two-file regression patch and reproduced the intended RED state:
  `TrustedCommand` was missing during agent-test collection.
- Replayed the persisted four-file implementation patch and reached 31 passing focused tests.
- Accepted and repaired additional review findings covering incomplete absolute-file attestation,
  device/inode/size binding, canonical execution paths, child-controlled failure hashes, response
  identity separation, boolean timeout validation, explicit descriptor closure, and local bounded
  failure diagnostics.
- Committed the six-file hardening change as `babd013`.

## Fresh Verification

Run from the durable feature worktree:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/agents -q` -> 36 passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q` -> 168 passed.
- `.venv/bin/ruff check .` -> all checks passed.
- `.venv/bin/mypy` -> success in 25 source files.
- `.venv/bin/python scripts/export_schemas.py --check` -> exit 0.
- `git diff --check` -> exit 0.

## Current Gate

**Blocked for Tasks 5--7 completion.** `SubprocessAdapter` is a verified trusted-command boundary,
not an OS sandbox. Filesystem and network syscalls remain available to the approved child. The
remaining verify-to-exec race and `preexec_fn` portability/thread-safety also require resolution or
an explicit accepted threat-model decision.

Do not begin Task 8, E1, E2, CLI, provider, physical, or deployment work.

## 2026-08-07 Remaining-Steps Goal Preparation

- The user approved one phased master goal covering non-destructive Q12D preservation, Task 7
  containment, Tasks 8--12, final evidence review, and commit/push checkpoints.
- Added the approved design record at
  `docs/plans/2026-08-07-remaining-steps-master-goal-design.md` and pushed it as `75e21a2`.
- Added the executable contract `GOAL_REMAINING_STEPS.md` and its execution overlay at
  `docs/plans/2026-08-07-remaining-steps-master-goal.md`.
- This preparation does not close the Task 7 gate and does not begin Task 8. The contract must be
  invoked from the durable feature worktree with `/goal GOAL_REMAINING_STEPS.md`.
