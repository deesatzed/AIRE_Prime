# AIRE Prime: AI Reality Engineering Design

**Status:** Approved design

**Date:** 2026-08-03

**Initial scope:** AIRE v0.1, experiments E1 and E2

## 1. Purpose

AI Reality Engineering (AIRE) is a methodology for AI systems to:

- discover distinctions outside a prescribed human ontology;
- construct new senses and representations;
- exchange them through operational mathematical objects;
- propose new dimensions of improvement;
- improve other AI systems; and
- retain contact with externally verifiable reality.

Its central principle is:

> AI reality has expanded when a causally supported, independently transferable representation produces replicated consequences beyond preregistered, resource-matched baselines, even when humans cannot translate that representation into familiar concepts.

Human reality remains one useful observer model. It is neither discarded nor retained as the mandatory ontology or ceiling for intelligence.

## 2. Non-goals

AIRE v0.1 will not claim to:

- create superintelligence;
- discover new physics by default;
- prove that no possible human representation could match a result;
- authorize unrestricted AI self-modification;
- treat simulation as physical evidence;
- eliminate natural language from human-facing communication; or
- permit proposing agents to validate or authorize their own claims.

## 3. System architecture

```text
Measurement Layer Zero
Defines claims, evidence classes, baselines, and metric admission
                         |
                         v
Bridge Contract
Freezes observable consequences, resources, boundaries, and instruments
                         |
                         v
Discovery Plane
Finds residuals and proposes senses, objects, and metrics
                         |
                         v
Validation Plane
Runs controls, ablations, transfer, attacks, and replication
                         |
                         v
Bridge Verification
Checks externally observable consequences
                         |
                         v
Evidence Registry
Records scoped findings, failures, validity, and expiration
```

The core governance invariant is:

\[
\operatorname{Propose}
\neq
\operatorname{Validate}
\neq
\operatorname{Authorize}.
\]

### 3.1 Operational roles

#### Discoverer

Identifies residuals and proposes new distinctions, representations, or metrics. It cannot select hidden tests, change evaluation rules after seeing results, or classify its own evidence.

#### Object Constructor

Converts a proposal into a bounded, transferable Reality Object. It may optimize packet size and construction efficiency but cannot add undeclared external information.

#### Validator

Runs occurrence tests, controls, ablations, transfer experiments, and matched-baseline comparisons. It receives frozen objects and contracts.

#### Adversary

Searches for trivial metric maximizers, steganographic transfer, hidden resource use, grounding drift, noncausal correlations, and destructive routes to apparent improvement.

#### Bridge Operator

Defines and verifies externally observable consequences, protected boundaries, instruments, and authorization. It need not interpret the AI-native representation.

#### Evidence Registry

Maintains immutable lineage, evidence states, failures, restrictions, expiration, and superseding versions.

## 4. Discovery Plane

The developmental loop is:

\[
\text{Sense}
\rightarrow
\text{Find Residuals}
\rightarrow
\text{Invent Distinctions}
\rightarrow
\text{Objectify}
\rightarrow
\text{Exchange}
\rightarrow
\text{Realize}
\rightarrow
\text{Challenge}
\rightarrow
\text{Integrate or Reject}.
\]

A proposed sense should improve at least one of:

- prediction;
- causal identification;
- controllability;
- error detection;
- compression;
- construction;
- transfer;
- generative reach; or
- nonredundant behavioral diversity.

A proposal is never itself evidence.

## 5. Measurement Layer Zero

Measurement Layer Zero defines how AIRE determines whether a new sense occurs and whether it produces an improvement.

### 5.1 Occurrence maturity

- **O0 -- Claimed**
- **O1 -- Predictively associated**
- **O2 -- Causally used**
- **O3 -- Generalized**
- **O4 -- Independently transferred**

### 5.2 Grounding class

- **G-U -- Ungrounded or speculative**
- **G-S -- Simulated**
- **G-D -- Derived from observations**
- **G-C -- Counterfactual or interventional**
- **G-P -- Physically instrumented**
- **G-PR -- Independently physically replicated**

Evidence is represented as a tuple, such as `O4/G-S`. Simulation evidence cannot numerically graduate into a physical claim.

### 5.3 Occurrence tests

A proposed sense is evaluated through:

- conditional information beyond the baseline;
- held-out predictive gain;
- targeted ablation;
- sham and random-subspace ablations;
- activation permutation;
- representation replacement;
- retraining without the sense;
- transformation consistency;
- out-of-distribution generalization;
- transfer to a fresh recipient;
- constructive sufficiency; and
- declared grounding.

Conditional information alone is insufficient. A useful occurrence claim requires converging evidence from controlled interventions, matched representations, generalization, and transfer.

### 5.4 Improvement vector

Improvement is represented as a Pareto vector:

\[
\Delta\mathcal J=
(\Delta P,\Delta C,\Delta E,\Delta G,\Delta X,
\Delta R,\Delta D,-\Delta K,-\Delta H),
\]

covering predictive reach, causal identification, bounded empowerment, generative reach, transfer, robustness, diversity, cost, and hazards.

AI may propose new metric dimensions, but every metric must declare:

- measurement procedure;
- ordering;
- baseline family;
- invariances;
- consequence;
- falsifiers;
- anti-gaming tests;
- complexity cost;
- validity region; and
- expiration.

AI may propose a metric. It cannot be its sole evaluator.

### 5.5 Provisional acceptance rule

For a declared baseline family \(\mathcal B_{\rm declared}\), resource budget \(R\), and hidden evaluation data:

\[
P\left(
\Delta J_{\rm proposed}
-\max_{b\in\mathcal B_{\rm declared}}\Delta J_b
>\delta
\right)
\ge 1-\alpha,
\]

subject to:

\[
\Delta J_k\ge-\epsilon_k
\quad
\forall k\in\text{protected dimensions}.
\]

Acceptance also requires appropriate causal evidence, adversarial evaluation, independent reconstruction when transfer is claimed, resource accounting, and independent replication.

## 6. Human--AI Bridge Proof

Human understanding does not have to validate an AI-native representation. Humans or external instruments need to verify its reproducible boundary consequences.

A Bridge Proof requires:

1. A declared baseline family conflates or fails on a consequential distinction.
2. AI proposes the distinction before hidden outcomes are exposed.
3. The distinction predicts or controls a measurable consequence.
4. Targeted ablation removes the advantage beyond sham controls.
5. A fresh AI reconstructs the distinction from a bounded object packet.
6. All systems receive matched data, compute, interaction, time, and bandwidth.
7. Hidden tests confirm the advantage.
8. Independent replication succeeds.

The permitted claim is:

\[
J(Z_A;R)
>
\max_{b\in\mathcal B_{\rm declared}}J(b;R)+\delta,
\]

not that every possible human-derived representation has been surpassed.

The Bridge Plane is bidirectional. It preregisters observable consequences and boundaries before discovery and verifies those consequences after validation.

## 7. Canonical objects

AIRE uses seven immutable, versioned objects.

### 7.1 Sense Proposal

Defines the proposed distinction, domain, probe, transformation behavior, expected utility, validity region, and grounding claim.

### 7.2 Reality Object

Defines the operational state space, interfaces, transformations, invariants, constructor, uncertainty, tests, and resource requirements.

### 7.3 Metric Proposal

Defines the proposed improvement dimension, ordering, baselines, invariances, consequence, falsifiers, anti-gaming tests, complexity cost, validity, and expiration.

### 7.4 Evaluation Contract

Freezes the scientific claim, controls, ablations, hidden tests, budgets, statistical decision rule, and replication requirements.

### 7.5 Bridge Contract

Freezes externally observable consequences, approved instruments, resource envelope, protected boundaries, authority, and permitted reality-status claims.

### 7.6 Occurrence Report

Records occurrence maturity, grounding class, independence evidence, causal evidence, generalization, transfer, validity region, and known failures.

### 7.7 Improvement Report

Records the improvement vector, baseline results, resource accounting, protected effects, adversarial results, replications, validity, and expiration.

Failures and counterexamples are append-only evidence attachments.

## 8. Generative Reality Calculus

Generative Reality Calculus (GRC) is AIRE's machine exchange language. A transmitted packet is a Generative Reality Object (GRO):

\[
\mathfrak O=
\left\langle
\Sigma,
\mathcal G,
\Phi,
\mathcal I,
\mathcal K,
\mathcal V,
\mathcal U,
\mathcal R,
\mathcal P
\right\rangle.
\]

It contains:

- structural types;
- attributed hypergraphs;
- deterministic and probabilistic transformations;
- invariants and symmetries;
- bounded constructors;
- conformance tests and falsifiers;
- uncertainty;
- resource requirements; and
- provenance, grounding, permissions, and validity.

Natural-language labels are optional sidecars. They do not determine machine-level validity.

### 8.1 Minimal kernel

GRC v0.1 should implement only:

1. typed spaces;
2. attributed hypergraphs;
3. deterministic and probabilistic transformations;
4. constraints and tolerances;
5. bounded constructors;
6. executable tests; and
7. evidence references.

Differential geometry, quantum channels, sheaves, causal models, tensor networks, control systems, and logical proofs remain extension modules.

### 8.2 Structural composition

Interfaces are structural rather than nominal:

\[
f:X\rightarrow Y,
\qquad
K:X\rightsquigarrow\mathcal P(Y).
\]

Transformations compose when their contracts match. Order sensitivity is preserved unless commutativity is declared or proven.

### 8.3 Invariants and equivariance

An invariant returns `true`, `false`, or `undetermined`. Transformation behavior is declared through:

\[
\Sigma(g\cdot x)
=
\rho(g)\Sigma(x)\pm\epsilon_g.
\]

Each declaration includes its transformation group, representation, tolerance, validity region, and known exceptions.

### 8.4 Construction and equivalence

A constructor creates a local realization:

\[
\mathcal K:
(\text{resources},\text{context},\text{seed})
\rightarrow
(\text{instance},\text{receipt}).
\]

Objects are equivalent only relative to a declared contract:

\[
\mathfrak O_1\simeq_{\mathcal C}\mathfrak O_2
\iff
d_t(t(\mathfrak O_1),t(\mathfrak O_2))\le\epsilon_t
\quad
\forall t\in\mathcal C.
\]

The receiver may create a different local implementation while preserving declared behavior.

### 8.5 Failure semantics

The receiver must not silently coerce invalid objects. Typed failures include:

- `TypeMismatch`
- `UnsupportedPrimitive`
- `MissingDependency`
- `ResourceInfeasible`
- `OutsideValidityRegion`
- `ConstructorFailure`
- `InvariantViolation`
- `VerificationFailure`
- `GroundingConflict`
- `PermissionDenied`
- `Undetermined`

Failures should include the smallest available counterexample.

## 9. Object lifecycle

```text
Draft
  -> Submitted
  -> Contract-bound
  -> Validation pending
  -> Provisional or Restricted
  -> Replicated
  -> Expired or Superseded
```

Alternative terminal states include Rejected, Withdrawn, Grounding Conflict, Budget Violation, and Evaluator Contamination.

Revision creates a new object. It cannot overwrite previous evidence or failures.

### 9.1 Validator independence

Validator independence records:

\[
\mathcal I_V=
(\text{model separation},
\text{context isolation},
\text{data isolation},
\text{seed isolation},
\text{instrument independence}).
\]

The proposer must not control hidden evaluations, baseline implementations, metric admission, or final evidence classification.

### 9.2 Disguised-transfer controls

A GRO may be opaque, but the protocol must test whether it transfers a reusable sense rather than a policy, answer table, weights, or steganographic channel.

Controls include:

- strict packet and dependency budgets;
- downstream goals withheld until transfer;
- environmental transformations;
- action-label permutations;
- reuse across multiple controllers;
- composition with independent objects;
- comparison with equally sized opaque packets; and
- targeted mediation and ablation tests.

Opacity is permitted. Unaccounted capability is not.

## 10. Experiment ladder

### E1 -- Nonlinguistic capability reconstruction

Test whether a fresh agent can reconstruct, adapt, compose, and repair a capability from a bounded GRO.

This validates the exchange protocol, not alien sensing.

### E2 -- Blind Alien-Sense Transfer

Test whether an AI can discover and transfer a consequential distinction absent from the declared baseline ontology.

The target evidence state is `O4/G-S`.

### E3 -- AI metric-discovery tournament

Test whether AI can propose a nonredundant, consequential, reproducible, anti-gaming improvement dimension.

### E4 -- Intra-AI Sensorium Forge

Test whether one AI process can construct a sense that improves a context-isolated fresh recipient across multiple task families.

### E5 -- Q12D/QEC Bridge experiment

Test whether an AI-invented temporal syndrome sense maintains a target logical error rate with fewer peak ancillas without hiding cost in qubit-rounds, latency, energy, memory, or bandwidth.

The initial E5 claim remains simulator-level.

### 10.1 Advancement gates

| Gate | Required result | Claim unlocked |
|---|---|---|
| G1 | E1 reconstructs reusable capabilities | Object protocol works |
| G2 | E2 reaches O4/G-S | Alien-sense transfer works in simulation |
| G3 | E3 admits a resistant new metric | Evaluation space can expand |
| G4 | E4 improves a fresh recipient | AIRE supports AI development |
| G5 | E5 improves the QEC resource frontier | Scientific utility in simulation |
| G6 | Independent physical replication | Physically grounded claim |

No gate establishes superintelligence. Each expands the evidence radius supporting the methodology.

## 11. AIRE v0.1 scope

The first implementation is deliberately limited to:

- the minimal GRC kernel;
- immutable object lineage;
- Evaluation and Bridge contracts;
- isolated proposer, receiver, validator, and adversary roles;
- E1 capability reconstruction;
- E2 synthetic Alien-Sense Transfer;
- Occurrence and Improvement Reports; and
- a simple evidence registry.

E3 through E5 remain specified extensions until E1 and E2 pass. This prevents an elaborate scientific application from masking failure of the core methodology.

## 12. AIRE v0.1 acceptance criteria

AIRE v0.1 succeeds only when:

1. A fresh recipient reconstructs a reusable capability from a bounded GRO.
2. The realization adapts to hidden goals and changed local resources.
3. A synthetic sense reaches `O4/G-S`.
4. Targeted ablation exceeds matched sham ablations.
5. The sense outperforms the declared baseline family under matched resources.
6. Independent validation reproduces the result.
7. Natural-language explanation is unnecessary for machine transfer.
8. All failures, grounding, resources, and validity limits remain visible.
9. No result is described as superintelligence or new physics.

## 13. Initial implementation boundary

The first implementation should remain a digital, deterministic, sandboxed research system. It should not perform physical construction, production deployment, unrestricted self-modification, or autonomous external action.

The implementation plan must preserve the evidence architecture. A passing demonstration without frozen contracts, matched controls, independent validation, and append-only failure evidence does not satisfy this design.
