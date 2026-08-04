# AIRE v0.1 Status and Roadmap

**Status date:** 2026-08-04

**Implementation branch:** `feature/aire-v0.1`

**Reviewed implementation baseline:** `9498c4c`

## Evidence boundary

Tasks 1--4 provide a deterministic, typed, content-addressed substrate for representing and
evaluating AI-native reality objects. The verified baseline is 45 passing tests plus Ruff, strict
mypy, deterministic JSON Schema export, and clean diff checks.

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

## Remaining task groups and the question each answers

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

### Experimental proof -- Tasks 8--10

4. **Task 8: E1 capability reconstruction**

   Does a bounded GRO let a fresh recipient reconstruct, adapt, compose, and repair a capability
   under changed resources better than bandwidth-matched frozen alternatives? Passing supports
   only the claim that the object-transfer protocol works.

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

Execute the bounded Tasks 5--7 completion contract in
[`GOAL_NEXT_TASKS_GROUP.md`](../GOAL_NEXT_TASKS_GROUP.md). Do not begin E1 or E2 until all three
substrate tasks pass their own specification, security, and code-quality reviews.
