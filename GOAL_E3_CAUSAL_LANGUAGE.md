# AIRE E3 Causal-Language Research Goal

Run this contract from the durable AIRE Prime worktree with:

```text
/goal GOAL_E3_CAUSAL_LANGUAGE.md
```

```text
/goal
OUTCOME: Complete AIRE E3 as a preregistered, evidence-gated simulated research program that tests
whether a bounded intervention-derived causal program improves adaptation by independently
initialized, non-co-trained recipients on sealed unseen causal worlds beyond the strongest
precommitted resource-eligible baseline. Finish in exactly one honest scientific state—transferred,
partial, negative, or undetermined—while preserving E2 unchanged, committing and pushing every
completed phase, and producing a fresh-clone-reproducible evidence handoff. A positive result is not
required; a valid negative result is complete research.

PROOF OF DONE:
1. Preflight and branch boundary:
   - Read, when present and in order: `GOAL.md`, `STANDARDS.md`, `IMPLEMENT.md`, `DECISIONS.md`,
     `PROGRESS.md`, `TASK_QUEUE.md`, this goal, every `docs/research/E3_*.md` file, and
     `docs/plans/2026-08-11-e3-causal-language.md`.
   - Confirm the implementation root is the durable AIRE worktree, `origin` is
     `https://github.com/deesatzed/AIRE_Prime.git`, the current branch is clean and synchronized,
     and the E2 report identity remains
     `sha256:3f60ac64e2190fbdd0705e8ef6bad7e8a701e9a42087a82a32d1afeb695a81bc`.
   - Fetch first. Create `research/e3-causal-language` from the pushed AIRE feature checkpoint.
     Never implement E3 on the mixed legacy root, in Q12Dgates, or in E2's package.
   - Record starting commits, dirty state, assumptions, phase, and exact next action in
     `PROGRESS.md`. Preserve all pre-existing user work.

2. Literature and research-contract gate:
   - Extend `docs/research/E3_RELATED_WORK.md` through targeted primary-source searches covering at
     least causal abstraction, machine teaching, executable program transfer, cross-architecture
     alignment, information-limited communication, and post-2023 causal representation methods.
   - Retain at least five and normally 8--15 directly usable primary papers. For each close work,
     record the task, assumptions, mechanism, evaluation, overlap, and exact E3 difference.
   - Do not call the E3 conjunction novel if a close prior work already demonstrates it. Narrow or
     reframe the research question instead and update `DECISIONS.md` before implementation.
   - Freeze the problem-first question, competing hypotheses, evidence ladder, nonclaims, world
     families, baseline contract, pilot-tunable fields, and preregistration amendment rules.

3. Benchmark-before-candidate gate:
   - Follow Tasks 1--5 of `docs/plans/2026-08-11-e3-causal-language.md` test-first.
   - Implement deterministic typed six-variable causal worlds, public/development/confirmatory split
     domains, all six shift families, proposer/validator projections, capacity proof, and automated
     leakage audits.
   - Implement the exact primary/secondary metrics, world-level hierarchical bootstrap, maximum-
     baseline rule, causal/sham analysis, missing-evidence handling, and resource claim types before
     candidate code exists.
   - Implement and execute B0--B6 and B9 plus four independently initialized recipient families.
     Resolve B7/B8 with executable implementations or a reviewed incompatibility record; never
     substitute a weak proxy and label it state of the art.
   - Run a public/development pilot containing baselines and the oracle only. The pilot runner must
     have no candidate code or confirmatory-seed access. Use it to estimate world-level variance,
     validate task headroom, repair invalid baselines, and tune only predeclared pilot fields.
   - Freeze the task, shifts, metrics, margins, baseline and recipient sets, resource claim type,
     power/sample-size rule, randomization, bootstrap, retry, and exclusion rules using only this
     baseline/oracle evidence.
   - Prove equal hard budgets and complete arm-by-recipient evidence. Invalid mandatory baselines
     block superiority rather than receiving an invented zero.
   - Run focused suites, agents, measurement, complete tests, Ruff, strict mypy, schema freshness,
     and `git diff --check`. Review leakage, statistics, benchmark validity, baseline strength,
     containment, and test gaps.
   - Resolve every Critical and Important finding. Commit and push the benchmark/baseline freeze;
     verify the remote commit before any candidate implementation.

4. Candidate and causal-mechanism gate:
   - Follow Tasks 6--8 of the canonical E3 implementation plan test-first.
   - Implement only the selected sparse causal-program candidate: intervention selection, reusable
     typed mechanism inference, bounded graph serialization, and target alignment.
   - Enforce the 2,048-byte canonical packet ceiling and reviewed typed-operation allowlist. Reject
     arbitrary code, weights, imports, paths, URLs, environment access, target IDs, hidden labels,
     validator fields, and undeclared dependencies.
   - Add all precommitted targeted, sham, and wrong-object transformations with equal packet size,
     operation count, observation access, interactions, and execution budget.
   - Add a closed E3 artifact manifest, registry lineage, CLI pilot/confirm/report surfaces, hostile
     substitution tests, grounding-ceiling tests, and complete per-world/recipient/arm evidence.
   - Run focused and complete verification, update schemas and docs, commit, push, and verify the
     candidate checkpoint.

5. Candidate and confirmatory-freeze gate:
   - Reconfirm that the pushed benchmark/baseline freeze is unchanged. Candidate performance may
     not change the world, baselines, recipients, metrics, margins, resource rule, sample size,
     bootstrap, retry, exclusion, or decision contract.
   - Freeze the candidate bytes, causal/sham transformation identities, runner, closed artifact
     manifest, and all remaining analysis code identities.
   - Conduct adversarial methodology review for leakage, pseudoreplication, favorable baseline
     omission, multiple comparisons, post-hoc freedom, capacity loopholes, recipient sharing,
     resource mismatch, and claim escalation.
   - Resolve all Critical and Important findings; run the full 90%-coverage/static/schema/diff gate;
     write `E3_CONFIRMATORY_FREEZE.md`; commit and push without amending or force-pushing. Verify the
     remote freeze commit.

6. One-shot confirmatory gate:
   - Derive the confirmatory seed root only after the frozen checkpoint is pushed, using
     `SHA256("AIRE-E3-CONFIRMATORY-V1" || frozen_candidate_commit)`.
   - Write and register split specifications and their root commitment before scoring.
   - Execute arms in frozen randomized paired blocks on identical worlds. Retain every failure,
     exclusion, retry, timeout, resource observation, and invalid artifact.
   - Run the confirmatory evaluation once. Do not select a favorable seed or rerun outside the
     frozen infrastructure-retry rule. A correction to scientific code creates a new experiment
     version and preserves the original evidence.
   - Derive classification only through the frozen decision implementation. Secondary endpoints
     cannot rescue a failed primary endpoint. No aggregate can hide a shift-family collapse.
   - Publish `E3_RESULTS.md` and `E3_EVIDENCE_MATRIX.md` with complete effects, confidence intervals,
     arm/recipient/family matrices, resource evidence, exclusions, failures, limitations, and exact
     claim boundary. Commit, push, and verify the remote result checkpoint.

7. Reproduction and handoff gate:
   - Clone the pushed research branch into a fresh temporary directory, install from the lockfile,
     and run the complete test/coverage, Ruff, strict mypy, schema, diff, registry, report-inspection,
     containment, leakage, and claim-boundary surface.
   - Reproduce the canonical E3 report, decision, split root, registry identities, and scientific
     classification from the frozen commit. Host timing/RSS may vary and must remain identified as
     host metadata unless the preregistered resource analysis canonically aggregates it.
   - Obtain an independently implemented recipient or external reproduction when available. If it
     is unavailable, keep the independent-confirmation gate open and do not call internal fresh-
     clone reproduction independent confirmation.
   - Conduct final correctness, statistics, security, leakage, test-gap, resource, and claim review.
     Resolve Critical/Important engineering findings without rewriting the frozen decision.
   - Commit and push the final handoff. Confirm the research branch is clean, is not ahead of its
     upstream, and local/remote heads match exactly.

SCOPE:
- Create/modify E3 implementation only under `aire_prime/experiments/e3/` and its public imports.
- Create/modify E3 tests under `tests/experiments/e3/` plus narrowly required CLI, schema,
  end-to-end, adversarial, packaging, and claim-boundary tests.
- Modify shared AIRE primitives only when E3 proves a general missing capability and the change
  preserves E1/E2 behavior with regression evidence.
- Modify `aire_prime/cli.py`, `scripts/export_schemas.py`, `schemas/`, `pyproject.toml`, and lockfile
  only as required by the frozen E3 workflow.
- Maintain truth/evidence in `README.md`, `DECISIONS.md`, `PROGRESS.md`, `REVIEW.md`,
  `docs/research/`, and `docs/AIRE_V0_1_STATUS_AND_ROADMAP.md`.
- Read E1/E2 and Measurement Layer Zero as reusable baselines. Do not rewrite their canonical
  artifacts, historical decisions, or report identities.
- No Q12D/E5, physical experiment, provider integration, production deployment, merge, release, or
  unrelated refactor is in scope.

CONSTRAINTS:
- Codex decides. Bounded reviewers contribute. Tests and frozen evidence arbitrate. Markdown
  remembers.
- Use test-driven development: retain the meaningful RED state, implement the minimum GREEN change,
  and verify the nearest surface before expanding scope.
- Execute phases strictly in order. Candidate code is forbidden before the pushed baseline freeze;
  confirmatory seeds are forbidden before the pushed candidate/analysis freeze.
- Never tune the candidate, baseline set, metrics, margins, exclusions, or analysis on confirmatory
  outcomes.
- Never delete, skip, weaken, xfail, or relabel tests/evidence to manufacture a positive result.
- Do not silently regenerate failed worlds or omit unfavorable arms, recipients, families, seeds,
  host blocks, or resource observations.
- Do not introduce a new dataset or evaluation regime after the benchmark freeze. A material change
  creates E3 v2.
- Add dependencies only after a decision record shows the current Python/NumPy/Pydantic stack is
  insufficient and reviews provenance, license, lockfile, determinism, and attack surface.
- Use local/offline computation by default. No paid API, external model provider, cloud deployment,
  or production action is authorized.
- Make focused commits and push every completed phase. Never amend published freeze checkpoints,
  force-push, merge to main, or rewrite evidence history.

SAFETY / PROVENANCE:
- Treat every packet, agent output, artifact, path, registry event, resource observation, metric,
  and generated report as untrusted until its exact schema, identity, lineage, permissions,
  containment, and contract are verified.
- Keep proposer-visible data structurally separate from validator-only latent state, seeds,
  parameters, goals, optimal actions, split labels, and analysis outcomes.
- Preserve source, code, contract, seed, packet, recipient, arm, world, resource, decision, and
  reproduction identities in append-only evidence.
- Keep infrastructure success, behavioral association, causal use, generalization, transfer,
  independent confirmation, and grounding as separate gates.
- Never infer subjective perception, consciousness, general intelligence, superintelligence,
  physical truth, QEC improvement, quantum advantage, or new physics from E3.
- Do not claim novelty until the final related-work audit survives review.

ITERATION:
- At every start, crash recovery, or context compaction: fetch, inspect root/branch/remote/status,
  read durable truth files, compare local/remote freeze checkpoints, and resume the first incomplete
  gate without redoing verified pushed work.
- At most one numbered gate is active. Update `PROGRESS.md` at every gate, material assumption,
  interruption, failed verification, commit, push, and decision.
- Update `DECISIONS.md` for any research-question, world, metric, baseline, statistics, resource,
  dependency, threat-model, scope, or claim change.
- On failure, diagnose the root cause, retain a regression or evidence record, and attempt bounded
  repairs. Use the repository's systematic debugging/rescue workflow before a third approach.
- Request review after each major freeze. Classify every recommendation Accepted, Rejected with
  evidence, or Needs Investigation; resolve and re-review Critical and Important findings.
- Prefer the smallest mechanism that tests the hypothesis. Do not add model scale, worlds, methods,
  or metrics that do not change the predeclared decision.

STOP:
- Stop immediately on repository/root/branch/remote mismatch, unpreservable dirty user changes,
  missing GitHub credentials required for a freeze checkpoint, destructive action, sensitive data,
  legal/license uncertainty, production/deployment request, or a material scope decision absent
  from this contract.
- Stop if the literature audit finds the complete claimed contribution already established; record
  the overlap and propose a narrower question rather than manufacturing novelty.
- Stop dependent phases while a leakage, containment, mandatory baseline, resource, statistics,
  reproducibility, or remote-backup gate is red.
- Stop before paid services, privileged host mutation, physical hardware, Q12D/E5, or an outside
  publication/submission action.
- Stop after three distinct failed repair approaches for the same blocker. Preserve the branch,
  exact failure evidence, last pushed checkpoint, and smallest safe continuation step.
- Do not stop merely because the scientific result is negative. A valid negative result proceeds
  through reproduction and handoff.

COMPLETE:
Mark complete only when all required E3 documents and implementation artifacts exist; the baseline
frontier was frozen before the candidate; the candidate and analysis were frozen before hidden-seed
derivation; confirmatory evaluation followed the one-shot contract; the result is classified as
transferred, partial, negative, or undetermined solely by frozen rules; full verification and a
fresh-clone canonical reproduction pass; every Critical/Important finding is resolved or the
scientific state remains explicitly blocked; E2 remains unchanged; and the clean
`research/e3-causal-language` branch equals its GitHub remote. Report the exact supported simulated
claim and every failed gate. Never equate engineering completion with a positive result.
```

## Assumptions

- Local/offline CPU research is authorized; paid compute and providers are not.
- The first E3 result may terminate honestly as negative or undetermined.
- An external seed custodian or independent implementer may be unavailable. Their absence lowers
  the confirmation claim but does not invalidate a correctly labeled internal study.
- The current 2,048-byte, 32-calibration-episode, and 256-evaluation-episode values are pilot-
  tunable only before the candidate exists.
