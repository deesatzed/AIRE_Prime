# AIRE Prime Remaining-Steps Master Goal Design

**Status:** Approved by the user on 2026-08-07  
**Branch:** `feature/aire-v0.1`  
**Primary artifact:** `GOAL_REMAINING_STEPS.md`

## Purpose

Provide one crash-resilient `/goal` contract that protects the surviving Q12D materials without
mixing them into AIRE Prime, closes AIRE's Task 7 security gate, completes Tasks 8--12 in order,
and pushes evidence-backed checkpoints without deploying or escalating scientific claims.

## Approaches Considered

### A. One phased master goal -- selected

A single contract owns recovery, containment, experiments, release evidence, and remote backup.
Hard phase gates prevent later work from starting early, while persistent progress and focused
commits make resumption after an outage deterministic.

### B. AIRE-only master goal

This is simpler, but it leaves the untracked Q12D files exposed to another local failure and does
not complete the recovery work identified in the 2026-08-07 audit.

### C. Separate recovery and implementation goals

This gives the strongest scope isolation, but it does not satisfy the request for one autonomous
completion contract and creates another handoff boundary that could be lost during a crash.

## Selected Architecture

The master goal is a state machine with six ordered phases:

1. Verify repository identity, branch, remote state, control files, and recovery evidence.
2. Preserve Q12D non-destructively in a distinct repository and remote; never add it to AIRE.
3. Close Task 7 with fail-closed host filesystem and network containment.
4. Implement Tasks 8--10: E1, Measurement Layer Zero, and simulated E2.
5. Implement Tasks 11--12: CLI, reproducibility, adversarial review, and evidence boundaries.
6. Run the final release gate, update durable truth files, commit, push, and verify remote heads.

Every phase begins with a clean-state and source-of-truth check, uses test-first batches, records
exact evidence in `PROGRESS.md`, records meaningful choices in `DECISIONS.md`, and ends with a
focused commit and verified push. A failed hard gate blocks dependent phases without permitting
the goal to redefine success.

## Repository Boundary

AIRE Prime work stays in the durable linked worktree and on `feature/aire-v0.1`. The legacy
`Q12D.md`, Angular `src/`, and `Quantum Maze Teaching Model Plan/` remain outside AIRE history.
Q12D preservation may create a separate repository and push a baseline only when the destination,
remote ownership, and visibility are already configured or explicitly authorized. It must never
move or delete the surviving originals.

## Security and Evidence Boundary

Task 7 is not complete merely because typed protocol tests pass. Completion requires a fail-closed
containment backend with negative proof that an approved child cannot access undeclared files or
the network. Unsupported hosts must refuse execution. The verify-to-exec artifact race and
`preexec_fn` risk must be removed or resolved by an explicit reviewed design that does not weaken
the existing goal.

E1 and E2 remain deterministic simulated experiments. E2 may classify at most `O4/G-S` and may
not imply physical grounding, superintelligence, new physics, or QEC improvement. Q12D/QEC stays
deferred as E5 and receives no scientific implementation under this goal.

## Crash-Recovery Design

- Push a focused checkpoint after every completed phase.
- Never amend or force-push checkpoint commits.
- Keep the feature worktree clean between phases.
- Update `PROGRESS.md` with the phase, last verified commit, commands, outputs, and next action.
- On restart, fetch first, compare local and remote heads, inspect worktrees/reflogs/status, and
  resume from the last remotely verified checkpoint rather than replaying completed work.
- Preserve failures and counterexamples; do not erase them to regain a green run.

## Completion Boundary

The goal completes only when Q12D has a distinct verified remote baseline, Task 7's hard security
gate passes, Tasks 8--12 pass their focused and full verification, evidence documents state exact
supported and unsupported claims, the feature branch is clean and pushed, and remote branch heads
match local heads. Completion does not authorize merging, releasing, deploying, physical-device
work, provider access, E3--E5, or cleanup of the legacy source directory.
