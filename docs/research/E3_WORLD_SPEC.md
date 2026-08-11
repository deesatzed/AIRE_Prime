# E3 Procedural Causal-World Specification

**Status:** Design contract; implementation not started

## Purpose

The E3 world family must make lookup transfer infeasible, expose controlled causal interventions,
support deterministic hidden evaluation, and remain inexpensive enough for repeated local
experiments. It is a simulator benchmark, not a physical model.

## World family

Each world is generated from a content-addressed specification containing:

- six ternary causal state variables `z0` through `z5`;
- a directed acyclic dependency graph with at most two parents per variable;
- four intervention actions plus one no-op;
- a seeded library of modular transition mechanisms;
- six binary nuisance variables;
- a 48-bit surface observation produced by a seeded permutation and nonlinear mixing of causal and
  nuisance variables;
- a bounded stochastic bit-flip/noise parameter;
- a goal predicate over two or three causal variables;
- a surface action-label permutation;
- an episode horizon and intervention cost.

The latent state and generator parameters are validator-only. Discoverers and recipients receive
only declared observations, actions, rewards, and intervention outcomes.

## Shared mechanism library

Source and target worlds draw from the same finite library of mechanism templates but use different
graphs, parameters, surface encodings, and compositions. The library includes:

1. modular increment/decrement;
2. parent-gated transition;
3. equality/inequality gate;
4. parity-conditioned transition;
5. saturating transition;
6. delayed two-step transition.

The discoverer must learn reusable mechanism descriptions rather than receive these names. Human
names are documentation only and never appear in scored packets.

## Observation construction

The validator derives the 48-bit observation from:

- a permuted one-hot encoding of the six ternary causal variables;
- parity and equality mixtures over seeded variable pairs;
- nuisance variables whose correlations differ by split;
- optional masked causal channels;
- seeded bounded observation noise.

The encoder is injective only in the easiest development family. Harder families may require active
intervention or temporal evidence to disambiguate state.

## Interaction surfaces

### Discoverer phase

- May interact with committed source worlds.
- Receives no latent labels, mechanism names, target-world seeds, validator code, or future tasks.
- May choose interventions under a fixed total episode and step budget.
- Emits one canonical packet no larger than 2,048 bytes.
- Packet operations must come from the reviewed typed constructor allowlist; arbitrary code,
  imports, file paths, or network references are forbidden.

### Recipient calibration phase

- Recipient is freshly initialized and was never co-trained with the discoverer.
- Receives the packet once.
- Receives at most 32 calibration episodes per target world.
- Uses the same calibration schedule and observations as every eligible baseline.
- May bind abstract packet variables to target sensors/actions but may not alter the packet.

### Evaluation phase

- Uses 256 scored episodes per world by default.
- No parameter updates unless the frozen recipient contract explicitly allows online adaptation for
  every arm.
- Records per-episode return, success, steps, interventions, failures, and resource observations.

Pilot results may change these numeric defaults only before the confirmatory preregistration
checkpoint. Every change requires a decision record and regenerated commitments.

## Shift families

The confirmatory set contains all of the following separately reported families:

1. **Surface:** unseen sensor and action permutations.
2. **Nuisance:** reversal or removal of source-world nuisance correlations.
3. **Parameter:** unseen coefficients/noise within the declared mechanism library.
4. **Composition:** unseen combinations of known mechanisms and goal predicates.
5. **Topology:** held-out causal graph motifs within the declared six-variable family.
6. **Sensor loss:** masked or noisier channels requiring active disambiguation.

No aggregate positive decision may hide a material collapse in one family.

## Split and sealing protocol

- **Public source split:** generator seeds and specifications are visible and may be used for
  development.
- **Development split:** fixed visible seeds used only for pilot variance and debugging.
- **Confirmatory split:** derived only after the benchmark, baselines, candidate, metrics, and
  analysis code are frozen at a pushed commit.
- The confirmatory root seed is derived as
  `SHA256("AIRE-E3-CONFIRMATORY-V1" || frozen_candidate_commit)`.
- Split specifications and their Merkle root are written before scoring begins.
- Any code change after seed derivation invalidates the confirmatory run and requires a new version,
  new preregistration, and new seed domain.

This protocol is auditably sequential, not cryptographically blinded from the investigator. An
outside seed custodian remains required for the strongest independent-confirmation claim.

## Capacity and shortcut constraints

- The source-to-target mapping family must exceed the 2,048-byte packet capacity by construction.
- Target observations must not contain world seed, latent labels, goal truth, optimal actions, split
  name, or generator parameter IDs.
- Episode order, content IDs, filenames, timestamps, and padding must be independent of latent
  class and optimal action.
- Surface permutations must be balanced so a fixed action prior cannot win.
- Nuisance correlations must reverse or disappear in hidden families.
- A validator-side mutual-information and classifier audit must test all declared metadata fields
  for shortcut leakage.
- A reference lookup using only the packet must fail the held-out composition family by design.

## Required invariant tests

1. Identical specification and seed produce byte-identical worlds.
2. Distinct split domains produce disjoint content IDs and episode IDs.
3. Confirmatory specifications cannot be constructed before a frozen commit is supplied.
4. Proposer-visible serialization contains none of the validator-only fields.
5. Every action has balanced marginal reward in the public source distribution.
6. Nuisance-only and metadata-only classifiers remain at the preregistered chance envelope.
7. The full target policy table cannot fit within the packet budget.
8. Each shift family changes exactly its declared dimensions.
9. Failed or invalid generation is retained as typed evidence and never silently resampled.

## Deferred grounding bridge

After a confirmed simulated E3 result, the same packet and recipient contracts may be evaluated in
CausalWorld or another established intervention-rich environment. Physical hardware, sim-to-real,
Q12D, and QEC work remain outside E3.
