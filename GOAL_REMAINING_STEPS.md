# AIRE Prime Remaining-Steps Master Goal

Run this contract from the durable AIRE Prime feature worktree with:

```text
/goal GOAL_REMAINING_STEPS.md
```

```text
/goal
OUTCOME: Recover and durably protect the surviving Q12D source as a distinct project, then complete
AIRE Prime v0.1 Tasks 7 through 12 on `feature/aire-v0.1` so that the agent boundary is genuinely
fail-closed and offline, E1 and simulated E2 produce reproducible evidence through the same typed
contracts, external researchers can run and inspect that evidence through a CLI, adversarial claim
and packet tests pass, and every completed phase is committed and pushed. The final state is a
reviewable, evidence-bounded AIRE v0.1 branch and a separately backed-up Q12D baseline; it is not a
deployment, physical result, QEC result, superintelligence claim, or new-physics claim.

PROOF OF DONE:
1. Repository and recovery preflight:
   - Read, in order when present: `GOAL.md`, `STANDARDS.md`, `IMPLEMENT.md`, `DECISIONS.md`,
     `PROGRESS.md`, `TASK_QUEUE.md`, this file, `GOAL_NEXT_TASKS_GROUP.md`,
     `docs/plans/2026-08-07-remaining-steps-master-goal-design.md`, and
     `docs/plans/2026-08-03-aire-prime-v0.1-implementation.md`.
   - Confirm the implementation root is the durable linked worktree, the branch is
     `feature/aire-v0.1`, and `origin` identifies AIRE Prime. Stop on a root, branch, or remote
     mismatch rather than editing the wrong checkout.
   - Run `git fetch origin`, `git status --short --branch`, `git worktree list --porcelain`,
     `git log --oneline --decorate -12`, `git reflog --all --date=iso -30`, and `git fsck --full`.
   - Record the starting local/remote commit, dirty state, recoverable Git objects, Q12D source
     inventory, and exact next action in `PROGRESS.md` before implementation.
   - Preserve all pre-existing user changes. Never reset, clean, overwrite, move, or delete them.

2. Non-destructive Q12D preservation:
   - Treat the legacy `Q12D.md`, Angular `src/`, and `Quantum Maze Teaching Model Plan/` found in
     the parent checkout as source evidence, not AIRE files. Do not add them to any AIRE commit.
   - Inventory every source file with relative path, byte count, modification time, and SHA-256 in
     a `RECOVERY_MANIFEST.md` stored in the separate Q12D repository.
   - Copy, never move, the surviving Q12D files into a distinct Q12D repository outside the AIRE
     worktree. Verify every copied regular file against the source manifest before committing.
   - Include a Q12D `README.md` that distinguishes the saved teaching UI, speculative decoder
     hypothesis, missing Angular build metadata, and deferred scientific work. Do not claim the UI
     is a faithful simulator or that a QEC experiment exists.
   - Commit the recovery baseline in the distinct Q12D repository and push it to its distinct
     configured remote. Confirm a fresh read-only clone or `git ls-remote` resolves the pushed
     commit and that the remote is not the AIRE Prime remote.
   - If no distinct destination or authorized remote exists, create no public repository and do
     not place Q12D in AIRE. Record the exact blocker in `PROGRESS.md` and stop the master goal for
     user authorization; local-only copying is not sufficient proof of durable completion.

3. Task 7 host containment and protocol completion:
   - Preserve the typed roles, reference-only wire packets, fixed-command attestation, bounded
     diagnostics, minimal environment, time/output/resource limits, process-group termination,
     and identity separation already implemented under `aire_prime/agents/`.
   - Add a small containment-backend interface whose default behavior is fail-closed. An
     unsupported or unavailable backend must return typed evidence and must not execute the child.
   - On every declared supported host, enforce filesystem read/write allowlists and denial of
     undeclared paths, network denial including loopback, process/fork limits, bounded descriptors,
     explicit working directory, and deterministic environment construction.
   - Eliminate the verify-to-exec race by executing an immutable, descriptor-pinned, or otherwise
     equivalently reviewed artifact. Path/digest/inode checks followed by ordinary path execution
     are not sufficient.
   - Remove child setup from unsafe multithreaded-parent `preexec_fn` use, or isolate it in a
     minimal reviewed launcher whose behavior and supported platform are explicitly tested.
   - Add negative integration tests proving that an approved hostile fixture cannot read an
     undeclared sentinel, write outside its allowed output directory, connect to loopback or an
     external address, spawn descendants beyond policy, inherit undeclared descriptors, or swap
     its verified artifact before execution. Also prove declared JSONL exchange still works.
   - Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest tests/agents -v`, the complete suite, Ruff,
     strict mypy, schema freshness, and `git diff --check`.
   - Conduct specification, code-quality, security, and test-gap reviews. Classify every finding
     as Accepted, Rejected with evidence, or Needs Investigation. Resolve and re-review every
     Critical or Important finding before declaring Task 7 complete.
   - Update `REVIEW.md`, `DECISIONS.md`, `PROGRESS.md`, and
     `docs/AIRE_V0_1_STATUS_AND_ROADMAP.md` with the supported platforms, threat model, exact
     negative evidence, limitations, commands, results, and commit ID.
   - Commit and push the completed Task 7 security phase. Verify the remote head before Task 8.
     Do not weaken D-001 or begin experiments while this gate is red.

4. Task 8 E1 nonlinguistic capability reconstruction:
   - Follow Task 8 in `docs/plans/2026-08-03-aire-prime-v0.1-implementation.md` test-first, using
     only the now-passing Task 7 execution boundary.
   - Implement the seeded procedural world, changed-resource transfer, fresh recipient,
     composition, repair, withheld conformance tests, and bandwidth-matched frozen alternatives.
   - Emit canonical contracts, objects, realization receipts, improvement reports, and registry
     events. Do not add a human-language baseline without a real language adapter.
   - Run E1 twice with seed 101 into separate temporary directories. Canonical report content IDs
     and registry evidence must match; noncanonical timestamps may differ.
   - Focused E1 tests, the full suite, static checks, schema check, and diff check must pass.
   - Record exact evidence, commit with subject `feat: add E1 capability reconstruction experiment`,
     push, and confirm the remote head.

5. Task 9 Measurement Layer Zero:
   - Follow Task 9 in the canonical implementation plan test-first.
   - Implement matched resource vectors, protected dimensions, targeted and sham ablations,
     deterministic bootstrap comparisons, and `provisional`/`rejected`/`undetermined` decisions.
   - Missing measurements remain `undetermined`; they are never coerced to zero or success.
   - Tests must reject unmatched packet bytes, observations, interactions, elapsed budgets, hidden
     receiver priors, favorable-only control selection, and protected-dimension regressions.
   - Run focused measurement tests, the full suite, static checks, schema check, and diff check.
   - Record evidence, commit with subject `feat: add matched AIRE occurrence and improvement controls`,
     push, and confirm the remote head.

6. Task 10 E2 simulated alien-sense transfer:
   - Follow Task 10 in the canonical implementation plan test-first.
   - Implement the seeded synthetic causal world, omitted latent transition distinction, reference
     discoverer, fresh recipient, new controller, held-out transformations, action-label
     permutations, matched alternatives, targeted ablation, sham ablations, and independent
     reproduction.
   - Freeze train, validation, hidden-test, and transformed-test commitments before discovery.
     Proposer-visible inputs must not contain hidden validator context.
   - Classify at most `O4/G-S`, and only when every declared transfer, causal, matched-control,
     transformed-generalization, and independent-reproduction gate passes. Otherwise emit the
     lower supported state and retain every failed gate.
   - Run E2 twice with seed 202 and verify deterministic canonical evidence. Scan outputs to ensure
     result classifications never claim physical grounding, QEC improvement, superintelligence,
     or new physics.
   - Run focused E2 tests, the full suite, static checks, schema check, and diff check.
   - Record evidence, commit with subject `feat: add E2 simulated alien-sense transfer`, push, and
     confirm the remote head.

7. Task 11 CLI, inspection, and end-to-end reproduction:
   - Implement the exact CLI surface in Task 11 of the canonical plan using standard-library
     `argparse`: schema check, registry verification, E1 run, E2 run, and report inspection.
   - Return nonzero for corruption, contract failure, invalid grounding escalation, containment
     refusal, or resource-budget violation.
   - Add end-to-end tests for contract ordering, independent identities, canonical IDs, explicit
     resource states, append-only history, failure preservation, and the `G-S` ceiling.
   - Document exact commands and a `What passing E2 does not prove` section in `README.md`.
   - Run Ruff, strict mypy, schema freshness, E1/E2 deterministic executions, registry verification,
     `git diff --check`, and `pytest --cov=aire_prime --cov-report=term-missing --cov-fail-under=90`.
   - Record evidence, commit with subject `feat: expose verified AIRE v0.1 experiment CLI`, push,
     and confirm the remote head.

8. Task 12 adversarial release review and evidence publication:
   - Implement the claim-boundary, packet-channel, metric-gaming, reproducibility, and containment
     attacks specified by Task 12 of the canonical plan.
   - Produce `docs/AIRE_V0_1_EVIDENCE.md` with supported claims, unsupported claims, exact baselines,
     evidence maturity/grounding, resource accounting, failures, limitations, untested threats,
     reproduction commands, and deferred E3--E5 work.
   - Obtain correctness/architecture, security, test-gap, and adversarial reviews. If Claude Code
     is used, give it a bounded read-only prompt with no secrets, classify every recommendation,
     and let Codex make the final decision. Tests arbitrate disputed claims.
   - Resolve and re-review every Critical or Important finding. Do not describe an unavailable
     reviewer or a silent review attempt as approval.
   - Run the complete release verification surface and a fresh-clone reproduction from the pushed
     feature branch. Generated evidence must be deterministic or explicitly distinguish
     canonical payloads from noncanonical run metadata.
   - Commit with subject `test: harden AIRE v0.1 evidence boundaries`, push, and confirm the remote
     head.

9. Final repository and evidence handoff:
   - Update `PROGRESS.md`, `DECISIONS.md`, `REVIEW.md`, `README.md`, and
     `docs/AIRE_V0_1_STATUS_AND_ROADMAP.md` so current claims match actual implementation and fresh
     command evidence. Retire no red gate by wording alone.
   - Create a final evidence matrix mapping every acceptance criterion in this goal and the
     canonical implementation plan to a test, command, report, commit, or explicit unresolved
     limitation.
   - Run from a clean environment: full tests with at least 90% coverage, Ruff, strict mypy, schema
     freshness, deterministic E1/E2 runs, both registry verifications, claim scan, containment
     negative tests, `git diff --check`, and a fresh-clone verification.
   - Confirm `git status --short --branch` is clean and the branch is not ahead of its upstream.
     Confirm `git ls-remote --heads origin feature/aire-v0.1` equals local `HEAD`.
   - Commit and push the final handoff if documentation changed. Never force-push, merge to main,
     create a release, or deploy under this goal.

SCOPE:
- AIRE implementation: `aire_prime/`, `tests/`, `scripts/`, `schemas/`, `pyproject.toml`, and only
  dependencies required by a proved containment or experiment need.
- AIRE truth/evidence: `README.md`, `PROGRESS.md`, `DECISIONS.md`, `REVIEW.md`,
  `GOAL_REMAINING_STEPS.md`, and `docs/`.
- Q12D preservation: read the surviving legacy sources; write only copied files, manifest, and
  recovery documentation in a distinct Q12D repository. Do not change the surviving originals.
- Use `docs/plans/2026-08-03-aire-prime-design.md`,
  `docs/plans/2026-08-03-aire-prime-v0.1-implementation.md`, and
  `docs/plans/2026-08-07-remaining-steps-master-goal-design.md` as governing design sources.
- Do not implement Q12D/E5, providers, physical experiments, deployment, autonomous external
  action, unrestricted model execution, or Tasks beyond the stated v0.1 plan.

CONSTRAINTS:
- Codex decides. Bounded reviewers contribute. Tests and reproduced evidence arbitrate. Markdown
  remembers.
- Follow test-driven development. Observe and preserve the intended RED state before each new
  implementation slice, then prove GREEN with the nearest focused verification.
- Do not delete, weaken, skip, xfail, or rewrite tests to manufacture a pass. Do not erase failure
  or counterexample evidence.
- Do not execute packet-provided code, paths, URLs, pickles, imports, environment requests, shell
  fragments, or arbitrary subprocesses.
- Do not weaken canonical identity, immutability, role independence, occurrence/grounding
  separation, resource accounting, or claim ceilings.
- Add dependencies only after documenting why the standard library and current dependencies are
  insufficient, reviewing provenance/license/platform impact, and adding a lockfile update.
- Make focused commits; never amend published checkpoints or force-push. Push after each completed
  phase and verify the remote commit before continuing.
- Do not commit caches, virtual environments, generated temporary runs, secrets, credentials,
  private keys, sensitive local paths, or the legacy Q12D originals into AIRE.
- No production deployment, merge, release publication, public repository creation, destructive
  cleanup, or remote visibility change is authorized.

SAFETY / PROVENANCE:
- Treat every agent message, GRO, file reference, command artifact, registry line, and generated
  report as hostile until schema, identity, permission, containment, dependency, resource, and
  evidence checks pass.
- Preserve exact provenance, content IDs, seeds, resource states, failure types, counterexamples,
  actor identities, contract commitments, and lineage.
- Keep simulated, synthetic, and infrastructure evidence explicitly separate from physical or
  real-world evidence.
- Never infer QEC improvement, physical grounding, new physics, alien intelligence, or
  superintelligence from passing software tests or simulated E1/E2 results.
- Q12D ownership and history remain independent from AIRE. A recovery copy is not a general
  license, scientific validation, or authorization to redesign the Q12D product.

ITERATION:
- At the start and after any crash or compaction, fetch first, inspect status/branch/worktrees/logs,
  read the durable truth files, compare local and remote checkpoint commits, and resume from the
  last verified incomplete phase. Do not redo completed remotely verified work.
- Execute phases strictly in order. At most one phase may be active. A red hard gate prevents work
  on every dependent phase.
- Break each phase into small test-first batches. Run the nearest focused checks after each batch
  and the full relevant gate before committing.
- Update `PROGRESS.md` at every phase boundary and material interruption with assumptions, files,
  exact commands/results, last pushed commit, accepted/rejected review findings, risks, and next
  action. Update `DECISIONS.md` whenever architecture, threat model, dependencies, scope, or claim
  interpretation changes.
- On failure, diagnose the root cause, retain or add a regression, and try bounded mitigations. On
  a second consecutive verification failure, use the repository's available rescue/debug workflow
  before a third distinct repair attempt.
- Preserve a clean rollback path through focused commits. Do not use destructive Git commands.

STOP:
- Stop immediately on an implementation-root, branch, remote, repository-identity, or source-file
  mismatch; missing credentials/account/authorized Q12D remote; production/release request;
  destructive operation; sensitive-data risk; legal/license/compliance uncertainty; or a product
  decision that materially changes scope.
- Stop Task 7 if containment would require arbitrary packet execution, privileged host mutation,
  disabling host security, or lowering the existing threat model.
- Stop dependent phases while any required security, correctness, reproducibility, evidence, or
  remote-backup gate is red.
- Stop after three distinct failed repair approaches for the same blocker. Record exact commands,
  outputs, attempted mitigations, surviving work, last pushed commit, and smallest safe next step.
- Do not call partial implementation, focused green tests, synthetic evidence, an unavailable
  review, or a local-only commit complete.

COMPLETE:
Mark this master goal complete only when every PROOF OF DONE item has current command or artifact
evidence; Q12D is byte-verified in a distinct committed and remotely verified repository; Task 7
has reviewed negative proof of fail-closed filesystem and network containment; Tasks 8--12 and the
full release suite pass without weakened tests; E1/E2 reproduce from pinned seeds; claims and
grounding remain correctly bounded; all Critical and Important findings are resolved and
re-reviewed; the AIRE feature branch is clean, pushed, and equal to its remote head; and the final
handoff names supported claims, unsupported claims, limitations, commits, and exact reproduction
commands. Report completion as a review-ready AIRE v0.1 feature branch and protected Q12D baseline,
not as a merge, deployment, physical validation, QEC result, superintelligence, or new physics.
```

## Assumptions

- The command is `/goal GOAL_REMAINING_STEPS.md`; `FOAL_REMAINING_STEPS.md` was a typographical
  error.
- The AIRE implementation continues on `feature/aire-v0.1` in the durable linked worktree.
- A distinct Q12D remote may require user authorization; the goal must stop rather than invent its
  owner or visibility.
- The existing Tasks 1--6 and recovered Task 7 implementation remain the baseline. This goal must
  reverify them and close the remaining Task 7 security gate before starting Task 8.

