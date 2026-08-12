# E3 Confirmatory Protocol Freeze

**Status:** frozen; confirmatory seed derivation is authorized only after this checkpoint is pushed

**Benchmark freeze:** `1e782b26643d3dae4deabfd4e59e91eda1a45562`

**Candidate/runner checkpoint before this document:** `e0d48e77a74ebb7ac076e7a8eac3e7da64ee5030`

## Frozen identities and decision surface

- World generator: six typed procedural shift families, with 180 confirmatory worlds (30 per
  family), 32 calibration episodes, and 256 scored episodes per world.
- Eligible arms: candidate, B0, B1, B2, B3, B4, B5, B6. B9 is a validator-only headroom arm and is
  excluded from maximum-baseline selection. B7/B8 remain explicit incompatibility records.
- Recipients: four independently seeded families (linear, recurrent, feed-forward, typed
  interpreter), no shared optimizer state or random stream.
- Packet and hard resource contract: 2,048 canonical bytes, 288 target interactions, 32 update
  steps, zero external calls, proposer-visible observation access.
- Primary unit: world. Recipient blocks are aggregated within world before analysis. The complete
  raw arm/world/recipient matrix remains in the result artifact.
- Primary bootstrap: deterministic world-level resampling, 100,000 replicates, maximum eligible
  baseline selected inside every replicate. Missing or invalid required evidence is undetermined.
- Resource claim: resource-envelope. Hard dimensions must match; unobserved host timing/RSS cannot
  be silently substituted or interpreted as equivalence.
- Grounding ceiling: simulated `G-S`; no physical, QEC, intelligence, or new-physics claim.

## Confirmatory seed and execution rule

The root seed will be derived only from this pushed freeze commit as:

`SHA256("AIRE-E3-CONFIRMATORY-V1" || frozen_candidate_commit)`

The one-shot confirmatory runner must retain every arm, recipient, family, failure, invalid block,
resource observation, and report identity. Infrastructure retries are permitted only under the
predeclared runner policy; scientific reruns or favorable seed selection are prohibited. Any code
correction after seed derivation creates a new E3 version and preserves the original evidence.

## Adversarial review disposition

- Leakage and capacity: passed in the development pilot and focused mutation tests.
- Pseudoreplication: world-level analysis enforced; episodes and recipient blocks are not treated as
  independent worlds.
- Favorable baseline omission: complete B0--B6 set is fixed; B9 is explicitly excluded by contract.
- Recipient sharing: identity, seed, adapter, and optimizer commitments are distinct.
- Packet loopholes: typed allow-list, exact byte padding, no arbitrary code/weights/paths/URLs or
  validator fields.
- Resource mismatch: hard dimensions are explicit; missing observations remain undetermined.
- Claim escalation: report and CLI accept only `G-S`.

This freeze does not assert a positive effect. It authorizes one confirmatory evaluation whose result
may be transferred, partial, negative, or undetermined under the preregistered gates.
