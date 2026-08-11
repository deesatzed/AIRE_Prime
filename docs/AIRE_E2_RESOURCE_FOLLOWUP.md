# AIRE E2 Resource-Instrumentation Follow-up

**Scope:** Option B only
**Status:** Instrumentation implemented; scientific E2 classification remains unchanged

## What changed

The contained subprocess adapter can now optionally observe elapsed wall-clock time with a trusted
parent monotonic clock and per-child peak resident memory with POSIX `wait4` when the host exposes it.
If the host cannot provide per-child usage, the observation remains undetermined. No fallback value or
zero is invented, and response wire bytes and failure identities are unchanged.

E2 writes `resource_observations.json` as noncanonical host metadata for the candidate, three baseline
arms, and independent reproduction. The CLI requires and displays this file, while the canonical
report and matched-resource decision remain governed by the existing frozen contracts.

## Verification

- New parser tests cover valid BSD `time -l` text, missing fields, and nonfinite/negative rejection.
- Agent/adversarial tests: 82 passed.
- Focused implementation/static gate: 148 passed, Ruff, strict mypy, schema freshness, and diff
  checks passed.
- A prior complete 300-test attempt was blocked by 30 containment-dependent failures because the
  interactive host Seatbelt probe returned `sandbox_apply: Operation not permitted`; this was an
  external host gate, not evidence of a positive E2 result.
- Ruff and strict mypy passed.
- Direct test-only backend: E2 retained report ID
  `sha256:3f60ac64e2190fbdd0705e8ef6bad7e8a701e9a42087a82a32d1afeb695a81bc`; the sidecar contained
  non-null elapsed and peak-RSS observations for all five recorded arms; CLI inspection passed.

The direct backend is protocol-mechanics verification, not production containment evidence. The
reviewed elevated Seatbelt probe subsequently passed, and two real seed-202 production runs
completed successfully. Their canonical report IDs matched exactly:

`sha256:3f60ac64e2190fbdd0705e8ef6bad7e8a701e9a42087a82a32d1afeb695a81bc`

Both runs also reproduced registry head
`sha256:026454dd53f2fd1c6363b7ad4213f0fcf5a0ba2257aa73e9619aa68542d4c314`. The two temporary
sidecars were hashed `0f82f6064174218b8227a41fc2f210ce4f82ffca909bdbfde32497937f559017` and
`0407b344b1687f960f742c3029ddb2f45612641325baccfe389ec274bb17807b`. They contain non-null
elapsed-time and peak-RSS values for all five arms. These are now production containment
observations, but they are not a post-hoc license to change the frozen scientific decision.

## Interpretation

The observations are not yet substituted into the canonical `ResourceVector` comparison because host
timings and memory are noncanonical and may differ between runs. E2 therefore remains
`simulated-alien-sense-transfer-not-established`, `O0/G-S`, with `heldout-gain` and
`matched-controls` failed. A future adjudication must predeclare aggregation or tolerance before
using these observations to change the scientific decision.

## Next bounded action

Define and preregister a resource aggregation/tolerance rule in a subsequent experiment version,
then rerun under that contract if resource matching is still scientifically required. Do not mutate
the v0.1 decision from these observations: both runs remain
`simulated-alien-sense-transfer-not-established`, `O0/G-S`, with `heldout-gain` and
`matched-controls` failed.
