# E3 Benchmark and Baseline Freeze

**Status:** frozen before candidate implementation

**Freeze basis:** baseline/oracle-only development pilot `sha256:9d13a8a2748279fcc762474699ee36a5b5846d86c5b504b952cf830491ac0d58`

**Code checkpoint:** `09d48e3` (recipient and baseline contracts); this document is committed in
the following benchmark-freeze checkpoint.

## Frozen benchmark contract

- Six deterministic procedural shift families: surface, nuisance, parameter, composition,
  topology, and sensor-loss.
- Six ternary causal variables, 48-bit proposer observations, four interventions plus no-op, and
  288 episodes per world.
- 32 target calibration episodes followed by 256 scored episodes.
- 2,048 canonical transfer bytes, 288 target interactions, 32 recipient update steps, and zero
  external calls.
- Four fresh recipient families, with independently derived seeds and no shared optimizer or random
  state: linear/tabular, recurrent, feed-forward, and typed interpreter.
- Eligible baseline set: B0 no transfer, B1 random packet, B2 compressed trajectories, B3 nearest
  neighbor, B4 policy distillation, B5 conventional feature, and B6 noncausal world-model
  representation.
- B9 is a validator-only oracle upper bound and is excluded from maximum-baseline selection.
- Primary independent unit: generated world; bootstrap resampling remains world-level and the
  maximum eligible baseline is selected inside each replicate.
- Resource claim: resource-envelope, not numerical host-resource equivalence. Hard dimensions must
  match; host timing/RSS may remain undetermined and then block a superiority claim.
- Confirmatory evaluation must include every arm, recipient, and shift family with complete failure
  and missingness evidence.

## Baseline compatibility record

B7 (causal representation) is recorded as incompatible for E3 v1 because the available reviewed
methods require continuous latent-observation assumptions not supplied by the six-variable discrete
typed world. B8 (symmetry/alignment) is recorded as incompatible because E3 v1 does not declare a
group action that would make a symmetry method well-defined. Neither arm is replaced by a weak proxy
or included in the maximum baseline. The incompatibility is a limitation and keeps the headline
claim narrower; a compatible implementation requires E3 v2 and a new freeze.

## Gate status

Capacity and proposer-leakage audits passed. The pilot produced 192 valid blocks and positive oracle
headroom. No candidate file exists at this checkpoint. Candidate implementation is authorized only
after this freeze document, the pilot report, decision/progress records, and the complete focused
verification surface are committed and pushed together.

This is a benchmark freeze, not a positive scientific result. It does not derive confirmatory seeds.
