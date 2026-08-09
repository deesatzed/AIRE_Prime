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
- Task 7 implementation and review commit: `b19cfb3`
  (`feat: enforce fail-closed Task 7 host containment`).
- Final local verification from the durable worktree:
  - `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/agents -v` -> 63 passed;
  - `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q` -> 195 passed;
  - `.venv/bin/ruff check .` -> all checks passed;
  - `.venv/bin/mypy` -> success in 25 source files;
  - `.venv/bin/python scripts/export_schemas.py --check` -> exit 0;
  - `git diff --check` -> exit 0.
- Next action: push the Task 7 checkpoint and confirm the remote head equals the local evidence
  commit, then begin Task 8 E1. No experiment work began while the containment gate was red.

## 2026-08-07 Task 8 E1 Capability Reconstruction

- Implemented the deterministic seed-driven E1 procedural world with typed components, ports,
  local resource constraints, construction costs, changed-resource transfer, composition,
  single-component repair, and validator-only conformance details.
- The recipient-visible capability packet excludes hidden conformance names and downstream task
  labels. Three later canonical task requests independently ask a fresh contained receiver to
  transfer, compose, and repair; returned reference-only artifact IDs are checked by the hidden
  parent validator.
- Added five distinct executable frozen alternatives: fixed instance, demonstration list, lookup
  policy, deterministic opaque packet, and conventional feature schema. Their packet commitments
  are bound into the Evaluation Contract before execution. Every arm receives the same three-task
  schedule, 2,171-byte packet budget per interaction, interaction count, and aggregate transmitted
  input budget; observed failures are retained rather than assigned in advance.
- E1 emits and registers the capability packet, task packets, requests, responses, baseline packet
  commitments/results, Reality Object, Evaluation Contract, Bridge Contract, GRC kernel-smoke
  receipts, Occurrence Report, Improvement Report, and final E1 report. `SenseProposal` remains
  absent because E1 does not claim a new distinction.
- Three review rounds initially found hidden-test leakage, unevaluated labeled baselines,
  parent-only task execution, weak identity/conformance checks, incomplete lineage, post-observation
  baseline binding, disclosed downstream goals, and unmatched resource accounting. All findings
  were accepted and resolved. Final review verdict: Ready, with no remaining findings.
- Final local verification from the durable feature worktree:
  - `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/experiments/e1` -> 8 passed;
  - `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q` -> 203 passed;
  - `uv run ruff check .` -> all checks passed;
  - `uv run mypy aire_prime` -> success in 31 source files;
  - `uv run python scripts/export_schemas.py --check` -> exit 0;
  - `git diff --check` -> exit 0.
- Two independent seed-101 runs were byte-identical. Both report content ID
  `sha256:b709fbf42e25d2a8db6e4244472b739503e2d4fb458967bcc2080ddbf3348813`;
  report-file SHA-256 is `729363194ec8023dd08d8631aca5feaea2b626b4543a6d399a24cb3703501f7a`;
  registry-file SHA-256 is `e64a3db081bde8eb2ffd68349630619fca7c8767ba8a6bf9ba8d9afeb7bb16ff`.
- The passing classification is only `simulated-capability-transfer`. It is not physical, QEC,
  alien-sense, superintelligence, or new-physics evidence. Next action after remote verification:
  begin Task 9 Measurement Layer Zero.
- Task 8 phase commit `4bd84a6bc82846daaf7cd01dd14a702216104373` was pushed without
  force. `git ls-remote --heads origin feature/aire-v0.1` resolved that exact commit before Task 9.

## 2026-08-07 Task 9 Measurement Layer Zero

- Added a complete eight-dimension `ResourceVector`: packet bytes, peak resident bytes, operation
  count, interaction count, elapsed time, external calls, declared energy proxy, and declared
  bandwidth. Missing values are typed `undetermined` with `None`; discrete resources reject
  fractional counts.
- Resource comparisons recompute evidence from frozen candidate/control arms. Their dimension
  buckets are disjoint and exhaustive, status is derived from those buckets, hidden priors and
  observation access cannot be adjusted, and structured resource adjustments retain method,
  rationale, magnitude bound, and content ID.
- Added deterministic targeted, disjoint equal-size random-subspace, activation-permutation, and
  representation-replacement ablations. Reports retain every control and bind activation, target,
  evaluator, metric, and replacement-strategy commitments.
- Added deterministic seeded bootstrap decisions with full sorted effect distributions, one-sided
  decision quantiles, maximum-control comparison plus delta, and protected-dimension floors.
  Outcomes are only `provisional`, `rejected`, or `undetermined`.
- Control contracts precommit the exact control-arm set; protected contracts precommit exact names
  and floors; candidate samples bind candidate arm, metric, and measurement artifact. Missing,
  extra, substituted, unmatched, or post-hoc omitted evidence cannot produce `provisional`.
- Review initially found forgeable comparison status, favorable-only controls, unaudited
  adjustments, sham overlap, weak ablation provenance, unbound candidate samples, and omittable
  protected dimensions. All were accepted and resolved. Final review: Ready, with no Critical,
  Important, or blocking Minor findings.
- Final local verification:
  - `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/measurement -q` -> 19 passed;
  - `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q` -> 222 passed;
  - `.venv/bin/ruff check .` -> all checks passed;
  - `.venv/bin/mypy aire_prime` -> success in 36 source files;
  - `.venv/bin/python scripts/export_schemas.py --check` -> exit 0;
  - `git diff --check` -> exit 0.
- Next action after commit/push verification: Task 10 E2 simulated alien-sense transfer. Task 9 is
  measurement infrastructure; it does not itself establish E1/E2 improvement or physical evidence.
