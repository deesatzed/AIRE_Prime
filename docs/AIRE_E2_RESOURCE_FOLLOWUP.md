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
- Full suite after the change: 300 passed.
- Ruff and strict mypy passed.
- Direct test-only backend: E2 retained report ID
  `sha256:3f60ac64e2190fbdd0705e8ef6bad7e8a701e9a42087a82a32d1afeb695a81bc`; the sidecar contained
  non-null elapsed and peak-RSS observations for all five recorded arms; CLI inspection passed.

The direct backend is protocol-mechanics verification, not production containment evidence. A
production rerun must pass the reviewed macOS Seatbelt backend. The current interactive host probe
returned `sandbox_apply: Operation not permitted`, so no new production E2 result is promoted.

## Interpretation

The observations are not yet substituted into the canonical `ResourceVector` comparison because host
timings and memory are noncanonical and may differ between runs. E2 therefore remains
`simulated-alien-sense-transfer-not-established`, `O0/G-S`, with `heldout-gain` and
`matched-controls` failed. A future adjudication must predeclare aggregation or tolerance before
using these observations to change the scientific decision.

## Next bounded action

Run seed 202 twice on a host where the reviewed containment probe is functional, inspect both sidecars,
and decide whether a preregistered aggregation rule can make resource matching valid. Preserve
`O0/G-S` if it cannot.
