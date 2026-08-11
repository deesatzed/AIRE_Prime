# E3 Preregistration Contract

**Status:** Protocol draft; not yet frozen for a confirmatory run

**Experiment:** Intervention-Discovered Causal Languages for Cross-Agent Transfer

**Version domain:** `AIRE-E3-V1`

## Claim

Under a fixed 2,048-byte transfer channel and matched target calibration budget, a sparse
intervention-derived causal program enables non-co-trained recipients to adapt to sealed unseen
causal worlds more effectively than the strongest precommitted eligible baseline.

This is a simulated transfer claim with grounding ceiling `G-S`.

## Primary endpoint

For each arm, world, and recipient, calculate normalized adaptation AUC over the first 32 target
calibration episodes and the subsequent scored control episodes. Normalize against the no-transfer
and oracle arms using a formula frozen in code before candidate implementation.

The primary effect is:

`candidate mean normalized AUC - maximum eligible baseline mean normalized AUC`

The maximum baseline is selected over the complete precommitted serious baseline set, never after
excluding an unfavorable valid arm.

## Primary success rule

All conditions must pass:

1. The lower bound of the preregistered 95% hierarchical bootstrap interval for the primary effect
   exceeds `0.05` normalized AUC.
2. The candidate's lower interval bound against the strongest baseline is above `-0.02` in every
   shift family.
3. The candidate has a positive lower interval bound in at least three of four frozen recipient
   families.
4. The targeted causal ablation reduces AUC at least `0.05` more than the maximum matched sham,
   using the same interval rule.
5. Every mandatory baseline is valid and resource-eligible, or the decision is `undetermined`.
6. The chosen resource-equivalent or resource-envelope gate passes.
7. The independent reproduction gate passes without code or threshold changes.

These numerical margins may change only during the public pilot. Any change must be justified by
task scale or estimator behavior, recorded in `DECISIONS.md`, and frozen before candidate work. A
change based on candidate performance is prohibited.

## Secondary endpoints

- final target control return;
- episodes to reach 80% of oracle performance;
- intervention-response prediction accuracy;
- success per transfer bit;
- success per calibration episode;
- operation counts, elapsed time, and peak RSS;
- performance by shift family;
- performance by recipient family;
- packet sparsity and executable operator count;
- target-alignment accuracy when validator labels are revealed after scoring.

Secondary endpoints are descriptive unless separately multiplicity-controlled. They cannot rescue a
failed primary decision.

## Experimental units and sample size

The independent unit is a generated target world, not an episode. Episodes are nested within worlds;
worlds are crossed with recipient families and paired across arms.

The pilot estimates between-world and arm-by-world variance without using confirmatory seeds. The
confirmatory sample size is selected by a frozen simulation-based power analysis targeting at least
90% power for the `0.05` primary margin at two-sided alpha `0.05`. At least 30 independent target
worlds per shift family are required unless the frozen power analysis requires more. Reducing this
minimum after observing candidate results is prohibited.

## Randomization

- Pair every arm on identical target worlds and episode schedules.
- Randomize arm execution order within host blocks.
- Randomize recipient initialization seeds independently of world seeds.
- Derive confirmatory world seeds only after the candidate and analysis checkpoint is pushed.
- Retain the complete seed manifest and execution order in the evidence registry.

## Statistical analysis

- Use a deterministic hierarchical bootstrap: resample worlds, then recipient seeds within worlds.
- Retain and content-address the complete bootstrap distribution.
- Use 100,000 bootstrap replicates for the confirmatory decision unless performance profiling proves
  this infeasible before candidate work; any alternate count must be frozen.
- Report paired effects, confidence intervals, raw per-world observations, and all family-specific
  effects.
- Use the maximum eligible baseline inside each bootstrap replicate.
- Apply Holm correction to any confirmatory family-specific superiority claims.
- Do not treat repeated episodes from one world as independent samples.

## Exclusions and missingness

No world is silently regenerated or excluded. A world may be excluded only for a predeclared
generator invariant failure, infrastructure interruption before any arm scored, or proven artifact
corruption. The failure and exclusion decision are canonical evidence.

If one arm fails after another arm scored, retain the entire block and mark the comparison
undetermined unless the predeclared deterministic retry policy succeeds. Missing resource evidence
remains undetermined and is never converted to zero.

## Causal and sham interventions

Precommit these equal-size packet transformations:

1. remove or replace the highest-usage causal operator;
2. permute dependency edges while preserving counts and types;
3. replace mechanism parameters with another-world values;
4. change an unused metadata/padding region;
5. permute inert operator ordering;
6. substitute a size-matched packet from another world family.

The first three are targeted; the next two are shams; the last is a wrong-object control. Target
selection uses only public/pilot evidence and a frozen rule.

## Leakage audits

Before candidate scoring, automated audits must confirm:

- no target seed, split name, hidden variable, optimal action, validator result, or goal truth is in
  proposer-visible bytes;
- metadata-only and nuisance-only classifiers remain within the frozen chance envelope;
- filenames, ordering, padding, content IDs, and error types do not encode labels;
- candidate and baseline packet creators have identical allowed inputs;
- recipients cannot read generator or validator files;
- no arm shares weights, optimizer state, or random streams with a recipient.

Any leakage invalidates the experiment version; it is repaired under a new version and new hidden
seed domain.
## Terminal classifications

- **Transferred simulated effect:** every primary, causal, generalization, resource, and independent
  reproduction gate passes.
- **Associated/causally used/generalized partial effect:** only the corresponding lower evidence
  ladder gates pass; all failed gates remain named.
- **Negative result:** valid comparison shows the primary effect does not exceed the margin.
- **Undetermined:** invalid mandatory baseline, missing evidence, resource mismatch, leakage, or
  failed reproduction prevents the decision.

Engineering completion is not a positive scientific result. A valid negative result is an allowed
and publishable terminal state.

## Independence and confirmation

The first confirmation must run from a clean clone of the pushed frozen checkpoint on a second host
when available. The strongest E3-T claim additionally requires an independently implemented
recipient or external reproduction. If no independent party is available, report the internal
reproduction and keep the independent-confirmation gate open.

## Amendments

Before confirmatory seed derivation, amendments require a dated rationale and new content ID. After
seed derivation, no hypothesis, baseline, endpoint, margin, exclusion, analysis, or resource rule may
change. Corrections require a new experiment version; the original evidence remains append-only.
