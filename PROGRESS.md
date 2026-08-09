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

## 2026-08-07 Master Goal Execution Baseline

- Activated `GOAL_REMAINING_STEPS.md` from the durable linked worktree on
  `feature/aire-v0.1`.
- Starting AIRE feature checkpoint: local `HEAD` and `origin/feature/aire-v0.1` both
  `eb1827caf934997640b257fb2b0029992fb8dc71`; the feature worktree was clean.
- Refreshed remote refs after the sandboxed fetch could not write linked-worktree `FETCH_HEAD`.
  `origin/main` is now `d0edd2f0321d015175b7ec624d43aef6312ade39`, while the legacy parent
  checkout's local `main` remains 11 commits behind at `9d3f215`; that parent checkout and its
  untracked Q12D sources were not changed.
- `git fsck --full` reported no corruption. It reported only two dangling blobs, both previously
  inspected superseded versions of AIRE design/status documentation:
  `104c10bd8b9997146ea4fc4eb156fc9a7e69745d` and
  `71048a5439989ccb1b4fe2909fb13987e8c7ddee`.
- Q12D recovery inventory: 26 non-`.DS_Store` files, 591,420 total bytes, covering `Q12D.md`,
  `src/`, and `Quantum Maze Teaching Model Plan/`. The deterministic stream digest of the sorted
  per-file SHA-256 inventory is
  `c48fbbce1885c88f293222421033a9885562207bc57ed283d6bfb97be1e3a5f5`.
- GitHub authentication for the existing `deesatzed` account is available, but no repository named
  `deesatzed/Q12D` and no other Q12D/quantum repository under that account was found. No remote was
  created because remote ownership/visibility must not be invented.
- Created a non-destructive distinct local recovery repository at
  `/Volumes/WS4TB/Q12D-Recovered`. Its root commit is
  `cbd14aa` (`chore: preserve recovered Q12D baseline`). The repository adds only recovery
  documentation and `.gitignore`; all 26 preserved source files remain byte-identical to the
  original inventory, with 591,420 bytes and stream digest
  `c48fbbce1885c88f293222421033a9885562207bc57ed283d6bfb97be1e3a5f5`.
- The initial recovery commit intentionally retains source whitespace and file modes rather than
  normalizing recovered content. Subsequent repository status is clean.
- Phase 2 remains incomplete because the local recovery repository has no remote. Next action:
  obtain authorization for the distinct Q12D remote owner/name/visibility, push `cbd14aa`, and
  verify it from the remote before Task 7. Task 7 and all experiments remain gated.

## 2026-08-07 Q12D Recovery Remote Verification

- The user selected the existing public remote
  `https://github.com/deesatzed/Q12Dgates.git`. It was empty before the recovery push: no default
  branch, heads, or tags were present.
- Added that remote as `origin` in `/Volumes/WS4TB/Q12D-Recovered` and pushed local `main` without
  force. Local `main`, `origin/main`, and remote `HEAD` now resolve to
  `cbd14aa8d08f1ea73469353a1cf4722b572df82c`.
- Verified through a fresh depth-one clone that the remote contains 26 preserved source files,
  591,420 source bytes, and inventory stream digest
  `c48fbbce1885c88f293222421033a9885562207bc57ed283d6bfb97be1e3a5f5`.
- Q12D Phase 2 is complete. The surviving originals remain unchanged and uncommitted in the legacy
  parent checkout; the recovery baseline and its history are distinct from AIRE Prime.
- Next action: begin Task 7 containment RED tests. Task 8 remains gated until Task 7 security,
  review, and full-verification evidence are green.

## 2026-08-07 Task 7 Host Containment

- Added a fail-closed containment backend. Production support is deliberately limited to macOS 27
  arm64 with a successful functional Seatbelt probe; every other environment returns typed
  `ContainmentUnavailable` evidence without executing the child.
- Replaced mutable verify-then-path execution with verified, read-only, unlinked artifact snapshots
  passed by descriptor. Absolute artifacts bind digest/path/device/inode/size; nonabsolute tokens
  require explicit bounded-literal classification. Process execution is restricted to the
  attested executable and reviewed shell launcher variants.
- Removed `preexec_fn`. The reviewed launcher applies core, process, CPU, file-size, and open-file
  limits before the attested executable, while the adapter retains wall-time, input/output,
  artifact/argv, environment, descriptor-inheritance, and process-group bounds.
- Bound read/write allowances to resolved path/type/device/inode and re-verify them before profile
  construction. Explicit hostile fixtures prove undeclared content and metadata denial, declared
  reads/writes, write denial, loopback/local-interface/routed-nonlocal network denial, fork denial,
  descriptor isolation/exhaustion, executable replacement denial, immutable snapshots, and
  canonical JSONL exchange.
- Conducted specification/code-quality, security, and test-gap reviews in repeated rounds. All
  Critical findings were accepted and resolved. Important findings were resolved or explicitly
  adjudicated in `REVIEW.md` and D-007--D-009; residual `system.sb`, same-UID race, and memory-limit
  boundaries remain stated limitations rather than erased threats.
- Focused containment evidence: 63 tests collected. Final full commands and phase commit IDs will
  be recorded after the clean verification and push checkpoint.
- Next action: complete Task 7 full verification, commit, push, and verify the remote head. Task 8
  remains gated until that checkpoint is durable.
