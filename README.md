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

Tasks 1--7 have implementations on `feature/aire-v0.1`:

- reproducible Python research scaffold and explicit claim boundaries;
- canonical serialization, content-addressed identity, and deeply immutable models;
- the minimal Generative Reality Calculus structural-type and hypergraph kernel;
- seven immutable AIRE proposal, contract, and report objects with deterministic JSON Schemas.
- an allow-listed bounded GRO realizer and realization receipts;
- an append-only, tamper-evident evidence registry; and
- typed isolated-role packets plus a fixed, attested trusted-command subprocess boundary.

The recovered and hardened branch has 168 passing tests plus Ruff, strict mypy, and
schema-freshness checks. This establishes an auditable representation and evidence substrate. It
does **not** yet satisfy the Tasks 5--7 completion goal: the subprocess boundary is not an OS
sandbox and does not block filesystem or network syscalls by the approved child. It also does not
establish capability transfer, an alien AI sense, QEC improvement, superintelligence, or new
physics.

The current work remains Task 7 security remediation under
[GOAL_NEXT_TASKS_GROUP.md](GOAL_NEXT_TASKS_GROUP.md). Do not begin E1 or E2. The complete status,
review findings, and experimental roadmap are documented in
[AIRE v0.1 Status and Roadmap](docs/AIRE_V0_1_STATUS_AND_ROADMAP.md).
