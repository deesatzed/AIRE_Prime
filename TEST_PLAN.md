# AIRE Prime v0.1 Adversarial Test Plan

## Behavior Changed

Task 12 adds release-facing claim scans and hostile evidence fixtures. It does not widen the v0.1
runtime, grounding ceiling, provider surface, or experiment scope.

## Existing Test Coverage

The Task 11 baseline of 251 tests covers canonical identities, immutable typed objects, schema freshness,
registry lifecycle and tamper detection, the bounded GRC realizer, isolated agent protocol and
containment, Measurement Layer Zero, deterministic E1/E2 runs, CLI inspection, and installed-wheel
operation. Coverage is 91.89%.

The completed Task 12 development gate contains 296 passing tests at 92.29% coverage. Ruff,
strict mypy, schema freshness, and diff checks also pass.

## Missing Tests

No required automated test gap remains within the v0.1 implementation scope. Pinned E1/E2
identity reproduction and the full CLI/registry/report workflow passed from a fresh clone of the
pushed Task 12 checkpoint.

Implemented Task 12 coverage now includes CLI-rendered classification/grounding checks, a
denial-aware release-claim scanner with mutation fixtures, audited typed ingress and realization
evidence for every named packet attack, public rendering of undetermined resource states, and four
bounded hostile gaming agents evaluated through frozen Measurement Layer Zero contracts.

## Edge Cases

- Negative explanatory text may name forbidden claims; scans must distinguish denial from positive
  assertion.
- An E2 execution can be operationally valid while scientific gates fail; CLI inspection must not
  convert that honest negative result into a process failure.
- Typed rejection evidence must itself survive canonical registry verification.
- Resource mismatch and missing resource observations must remain distinct (`invalid` versus
  `undetermined`).

## Regression Tests

- E1 remains exactly `simulated-capability-transfer`, `O4/G-S` for seed 101.
- E2 remains exactly `simulated-alien-sense-transfer-not-established`, `O0/G-S` with
  `heldout-gain` and `matched-controls` failed for seed 202.
- Physical grounding never passes the v0.1 CLI inspector.
- Undeclared receiver priors and observation access cannot be adjusted away.

## Manual Smoke Tests

- Read `docs/AIRE_V0_1_EVIDENCE.md` against the generated reports and registry heads.
- Run the documented CLI workflow from a fresh clone of the pushed feature branch.
- Confirm the repository and remote branch heads match and the final worktree is clean.

## Commands To Run

| Purpose | Command | Expected Result |
| --- | --- | --- |
| Focused adversarial suite | `uv run pytest -q tests/adversarial` | All attacks are rejected with asserted evidence |
| Static quality | `uv run ruff check .` | No findings |
| Type safety | `uv run mypy` | Success |
| Full verification | `uv run pytest --cov=aire_prime --cov-report=term-missing --cov-fail-under=90` | All tests pass; coverage at least 90% |
| Schema freshness | `uv run python scripts/export_schemas.py --check` | Exit 0 |
| Patch hygiene | `git diff --check` | Exit 0 |

## Coverage Gaps Accepted For Now

- Apple Seatbelt remains private, patch-mutable platform TCB; only the declared macOS 27 arm64
  functional probe is supported.
- Reproducible observed peak RSS and elapsed-time evidence is unavailable, so E2 remains O0/G-S.
- Root, kernel, compromised-parent, concurrent same-UID pathname races, and native address-space
  enforcement remain untested or out of the v0.1 threat model as documented in `REVIEW.md`.
- E3 physical augmentation, E4 recursive discovery, E5 Q12D/QEC, providers, deployment, and
  autonomous external action are deferred.

## Done Criteria

- Every named Task 12 attack has a targeted regression.
- Every Critical or Important review finding is resolved and re-reviewed.
- The evidence-boundary document matches reproducible report and registry evidence.
- Full verification, fresh-clone reproduction, remote-head equality, and a clean worktree pass.
