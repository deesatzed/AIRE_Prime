# AIRE Prime

AIRE Prime is an experimental framework for evidence-gated discovery and validation of
AI-native representations. It is not a claim of superintelligence or new physics.

Version 0.1 is limited to E1 nonlinguistic capability reconstruction and E2 simulated
alien-sense transfer. The Q12D/QEC bridge is the deferred E5 experiment; it is not implemented in
v0.1. Object packets are data and never arbitrary executable code. Simulated evidence never
upgrades to physical evidence without independent physical validation.

The governing methodology and boundaries are defined in the
[canonical design](docs/plans/2026-08-03-aire-prime-design.md).

## Current implementation status

Tasks 1--11 have implementations on `feature/aire-v0.1`:

- reproducible Python research scaffold and explicit claim boundaries;
- canonical serialization, content-addressed identity, and deeply immutable models;
- the minimal Generative Reality Calculus structural-type and hypergraph kernel;
- seven immutable AIRE proposal, contract, and report objects with deterministic JSON Schemas.
- an allow-listed bounded GRO realizer and realization receipts;
- an append-only, tamper-evident evidence registry; and
- typed isolated-role packets plus a fail-closed, attested macOS containment boundary;
- E1 simulated capability reconstruction with byte-matched executable alternatives;
- Measurement Layer Zero with contract-bound controls and protected dimensions; and
- E2 contained simulated discovery, transfer, executable controls/ablations, and distinct-seed
  reproduction; and
- a packaged `aire-prime` CLI for schema checks, experiment execution, registry verification, and
  fail-closed evidence inspection.

Task 7 supports macOS 27 arm64 only when its functional Seatbelt probe passes. It fails closed on
other hosts. The contained boundary uses immutable artifact snapshots, explicit bounded command
literals, deterministic environment construction, filesystem allowlists, network/fork denial,
resource limits, descriptor isolation, bounded JSONL exchange, and typed refusal evidence. See
`REVIEW.md` for its exact threat model and residual Apple-private-profile, same-UID-race, and memory
limitations.

E1 currently reports reproducible simulated capability transfer. E2 currently reports
`simulated-alien-sense-transfer-not-established`, `O0/G-S`: its behavioral subtests pass, but
unobserved peak-RSS and elapsed-time dimensions remain `undetermined`, so matched-resource and
provisional-improvement gates do not pass.

The next gated phase is Task 12 adversarial release review under
[GOAL_REMAINING_STEPS.md](GOAL_REMAINING_STEPS.md). The complete status, review findings, and
experimental roadmap are documented in
[AIRE v0.1 Status and Roadmap](docs/AIRE_V0_1_STATUS_AND_ROADMAP.md).

## Command-line usage

From the repository root:

```bash
uv sync
uv run aire-prime schema check
uv run aire-prime e1 run --seed 101 --output /tmp/aire-prime-e1
uv run aire-prime e2 run --seed 202 --output /tmp/aire-prime-e2
uv run aire-prime registry verify /tmp/aire-prime-e1/registry.jsonl
uv run aire-prime registry verify /tmp/aire-prime-e2/registry.jsonl
uv run aire-prime report show /tmp/aire-prime-e1
uv run aire-prime report show /tmp/aire-prime-e2
```

Each experiment command writes canonical report, contract, request/response, receipt, and registry
artifacts. Inspection returns nonzero for corrupt registries, broken contract/report links,
contained response failures, realization or resource-budget failures, and grounding above the v0.1
simulated ceiling. A nonempty scientific `failed_gates` list remains visible but is not treated as
a CLI execution error when the evidence packet itself is valid.

Evidence states use `O0` through `O4` for occurrence maturity and `G-U`, `G-S`, `G-D`, `G-C`, `G-P`,
or `G-PR` for grounding. The v0.1 E1/E2 commands are limited to simulated grounding (`G-S`).

## What passing E2 does not prove

Even a future E2 packet that passes every declared gate would establish only transfer inside the
frozen simulated protocol. It would not prove:

- physical grounding or physically replicated evidence;
- quantum error-correction improvement or any Q12D/QEC result;
- superintelligence, general intelligence, consciousness, or sentience;
- new physics or a newly discovered physical sense; or
- production safety, deployment readiness, or performance outside the stated validity region.

The present v0.1 E2 packet does not pass every gate. Its `O0/G-S` classification is an explicit
negative/undetermined result, not established alien-sense transfer.
