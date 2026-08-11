# E3 Implementation Plan Router

The canonical task-by-task implementation plan is:

`docs/plans/2026-08-11-e3-causal-language.md`

The autonomous completion contract is:

`GOAL_E3_CAUSAL_LANGUAGE.md`

## Required execution order

1. Freeze research question and literature/overlap audit.
2. Implement deterministic world contracts and leakage tests.
3. Implement metrics, resource policy, recipients, and serious baselines.
4. Run a baseline/oracle-only public pilot; freeze and push the benchmark, baselines, analysis,
   thresholds, and sample-size rule before candidate implementation.
5. Implement the sparse causal-program candidate and causal/sham transformations.
6. Freeze and push the candidate and complete confirmatory contract without changing the benchmark
   or decision rules.
7. Derive new confirmatory seeds and run once under the frozen checkpoint.
8. Reproduce from a clean clone and, when available, obtain an independent recipient/reproduction.
9. Publish positive, negative, or undetermined evidence without changing the claim ceiling.

Candidate implementation is prohibited before Step 4 is pushed. Confirmatory scoring is prohibited
before Step 6 is pushed. E2 evidence and report identities are immutable historical inputs and must
not be rewritten.

## Invocation

After reviewing the package, execute from the durable AIRE worktree with:

```text
/goal GOAL_E3_CAUSAL_LANGUAGE.md
```

The goal creates and publishes a distinct research branch. It does not merge, deploy, perform
physical experiments, begin Q12D/E5, or guarantee a positive finding.
