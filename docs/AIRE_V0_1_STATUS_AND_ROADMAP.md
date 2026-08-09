# AIRE v0.1 Status and Roadmap

**Status date:** 2026-08-07

**Implementation branch:** `feature/aire-v0.1`

**Reviewed implementation baseline:** Task 8 E1 phase ready for its published checkpoint

## Evidence boundary

Tasks 1--8 now have deterministic, typed implementations for object representation, bounded GRO
realization, append-only evidence, isolated-role exchange, and simulated E1 capability transfer.
The Task 8 checkpoint gate produced 203 passing tests plus Ruff, strict mypy, deterministic JSON
Schema export, clean diff checks, and byte-identical independent seed-101 evidence runs.

The Tasks 5--7 substrate gate is **green on its declared host boundary**: macOS 27 arm64 with a
passing functional Seatbelt probe. Other hosts fail closed. The Task 7 adapter enforces immutable
artifact snapshots, explicit bounded literals, deterministic environment, filesystem allowlists,
network/fork denial, resource and descriptor bounds, process-group termination, reference-only
wire packets, and typed failures. See `REVIEW.md` and D-007--D-009 for exact limitations.

This is infrastructure evidence, not experimental evidence. It does not demonstrate:

- successful transfer of a reusable capability;
- occurrence of an alien or AI-native sense;
- improvement in intelligence;
- a quantum-error-correction resource advantage;
- a physical 12-dimensional manifold;
- superintelligence or new physics.

## What Tasks 1--4 created

### Task 1 -- Reproducible research scaffold

Created a Python 3.12+ package with pinned dependency ranges, strict tests, linting, typing, and
explicit README claim boundaries.

**Value:** a reproducible laboratory that prevents speculative output from silently becoming a
scientific or physical claim.

### Task 2 -- Canonical identity and immutability

Created deterministic canonical serialization, SHA-256 content IDs, deeply immutable models,
golden identity vectors, and defenses against mutable values, non-finite numbers, ambiguous keys,
and identity collisions.

**Value:** AI-to-AI objects can have stable identities independent of human names, mapping order,
or local implementation. Any substantive change creates a new identity.

### Task 3 -- Minimal Generative Reality Calculus kernel

Created structural types for scalars, vectors, tensors, distributions, graphs, manifolds,
operators, and processes, plus typed hypergraphs with canonical ordering and validated references.

**Value:** begins a machine-oriented exchange language in which structure and compositional
interfaces, rather than human semantic labels, determine compatibility.

### Task 4 -- Evidence and governance objects

Created Sense Proposal, Reality Object, Metric Proposal, Evaluation Contract, Bridge Contract,
Occurrence Report, and Improvement Report models with deterministic wire schemas. Added separate
occurrence and grounding axes, trusted grounding resolution, reality-tier claim constraints,
authority boundaries, resource measurements, replication evidence, and verified wire content IDs.

**Value:** converts a speculative AI distinction into a contract-bound, externally auditable claim.
The proposer can suggest a sense or metric but cannot self-certify its occurrence, improvement, or
grounding.

## Tasks 5--7 implementation and gate status

### Substrate completion -- Tasks 5--7

1. **Task 5: bounded realization protocol**

   Can a Generative Reality Object create a useful local capability using only allow-listed
   operations, while refusing arbitrary code, undeclared dependencies, invalid structure, and
   hidden resource costs?

2. **Task 6: append-only evidence registry**

   Can object lineage, validation, failures, supersession, and counterexamples remain verifiable
   over time, with detectable corruption and no history rewriting?

3. **Task 7: isolated agent roles and exchange**

   Can proposer, receiver, validator, adversary, and authorizer independence be enforced by the
   protocol rather than trusted as a social promise?

These tasks should tell us whether AIRE is safe and auditable enough to begin experiments. They do
not themselves prove capability or sense transfer.

Task 5 is committed at `8777470`, Task 6 at `7764155`, the initial Task 7 implementation at
`13cd8fa`, and recovered Task 7 hardening at `babd013`. The final containment checkpoint and remote
verification are recorded in `PROGRESS.md`. Repeated specification, security, and test-gap reviews
found no unresolved Critical issue inside the approved threat model.

## Task 7 verification evidence

The pre-containment recovery baseline was 36 focused and 168 full tests. The completed Task 7
surface adds functional and hostile-child integration for platform refusal, file contents and
metadata, writes, network address classes, forks, descriptors, executable replacement, artifact
and allowlist races, resource ceilings, deterministic environment, and JSONL exchange. Exact final
counts and commands are recorded in `PROGRESS.md`.

- focused Task 7 suite: green with real containment integrations executed;
- complete suite, Ruff, strict mypy, deterministic schema check, and diff check: green at the
  phase checkpoint.

The original four local-only commits were backed up to GitHub before reconstruction. The recovered
test patch was observed RED before implementation was replayed. No test was skipped, weakened, or
deleted to obtain the green result.

Task 7 remains infrastructure evidence. Task 8 now adds reproducible simulated E1 protocol
evidence; E2 has not been implemented or demonstrated.

### Experimental proof -- Tasks 8--10

4. **Task 8: E1 capability reconstruction**

   Does a bounded GRO let a fresh recipient reconstruct, adapt, compose, and repair a capability
   under changed resources better than bandwidth-matched frozen alternatives? Passing supports
   only the claim that the object-transfer protocol works.

   **Current evidence:** green. A fresh contained receiver handles three separately committed
   tasks after receiving a hidden-test-free capability packet. Five precommitted executable
   alternatives receive identical packet, task, interaction, and transmitted-byte budgets. The
   seed-101 report is deterministic and classified only as `simulated-capability-transfer`.

5. **Task 9: Measurement Layer Zero**

   Is an apparent advantage causal, resource-matched, statistically defensible, and robust to sham
   ablations and protected-dimension checks?

6. **Task 10: E2 simulated alien-sense transfer**

   Can a system discover a consequential distinction absent from the declared baseline ontology,
   transfer it to a fresh recipient, and retain its advantage under hidden transformations? Only
   all passed gates may support `O4/G-S`: independently transferred, simulated evidence.

### Reproducibility and release -- Tasks 11--12

7. **Task 11: CLI and end-to-end verification**

   Can an external researcher run, inspect, reproduce, and reject invalid E1/E2 evidence without
   trusting internal implementation claims?

8. **Task 12: adversarial release review**

   Do the evidence claims survive hostile packets, covert-channel attempts, metric gaming, claim
   escalation, and independent review? The resulting evidence document must state both supported
   claims and unresolved threats.

## Path toward Q12D/QEC

The Q12D/QEC bridge is E5, not E2 and not part of v0.1 implementation. It should begin only after
E1 and E2 validate the transfer methodology. E5 would ask whether an AI-invented temporal syndrome
representation maintains a target logical error rate with fewer simultaneous ancillas without
hiding costs in qubit-rounds, elapsed time, latency, energy, memory, or bandwidth. Its initial claim
would remain simulator-level.

## Current next action

After publishing and verifying the Task 8 checkpoint, begin Task 9 Measurement Layer Zero under
[`GOAL_REMAINING_STEPS.md`](../GOAL_REMAINING_STEPS.md). E1 remains simulated protocol evidence and
must not be described as alien-sense, physical, QEC, superintelligence, or new-physics evidence.
