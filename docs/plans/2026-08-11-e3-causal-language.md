# E3 Causal-Language Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Build and evaluate a preregistered simulated experiment testing whether a bounded
intervention-derived causal program improves adaptation by non-co-trained recipients on unseen
causal worlds beyond the strongest matched baseline.

**Architecture:** Add E3 as a new experiment package without modifying E2 identities or decisions.
First build the procedural world, leakage checks, recipients, metrics, and baselines; run a
baseline/oracle-only public pilot and freeze that complete evaluation before adding the sparse
causal-program candidate. Then freeze the candidate, derive fresh confirmatory seeds, and publish
the resulting positive, negative, or undetermined evidence.

**Tech Stack:** Python 3.12+, Pydantic frozen models, NumPy, standard-library `argparse`, pytest,
Hypothesis, Ruff, strict mypy, AIRE canonical objects/registry/containment/Measurement Layer Zero.

---

## Execution boundary

Run this plan only from a clean branch `research/e3-causal-language` created from the pushed
`feature/aire-v0.1` checkpoint. Do not edit `aire_prime/experiments/e2/` except for a regression
that proves its identities remain unchanged. E3 may reuse public AIRE primitives but owns its own
contracts, reports, manifests, seeds, and classification.

### Task 1: Add deterministic E3 world contracts

**Files:**

- Create: `aire_prime/experiments/e3/__init__.py`
- Create: `aire_prime/experiments/e3/world.py`
- Create: `tests/experiments/e3/__init__.py`
- Create: `tests/experiments/e3/test_world.py`
- Reference: `docs/research/E3_WORLD_SPEC.md`

**Step 1: Write failing determinism and separation tests**

```python
def test_same_world_spec_is_byte_identical() -> None:
    first = generate_world(WorldKey(family="surface", seed=301))
    second = generate_world(WorldKey(family="surface", seed=301))
    assert canonical_bytes(first) == canonical_bytes(second)


def test_distinct_split_domains_have_disjoint_episode_ids() -> None:
    source = generate_suite(root_seed=301, split="source")
    confirmatory = generate_suite(root_seed=301, split="confirmatory")
    assert episode_ids(source).isdisjoint(episode_ids(confirmatory))
```

Also test six ternary latent variables, four interventions plus no-op, 48-bit observations,
bounded noise, graph acyclicity, at most two parents, and exact shift-family membership.

**Step 2: Run the tests and retain RED**

Run:

```bash
uv run pytest -q tests/experiments/e3/test_world.py
```

Expected: collection fails because `aire_prime.experiments.e3.world` does not exist.

**Step 3: Implement minimal frozen contracts and generator**

Create frozen Pydantic models resembling:

```python
class WorldKey(FrozenModel):
    family: Literal["surface", "nuisance", "parameter", "composition", "topology", "sensor-loss"]
    seed: int


class E3World(FrozenModel):
    key: WorldKey
    public_spec: PublicWorldSpec
    validator_spec: ValidatorWorldSpec
    episodes: tuple[E3Episode, ...]
```

Use local `random.Random`/NumPy generators constructed only from explicit seeds. Never read global
random state, timestamps, paths, hostnames, or environment variables.

**Step 4: Run focused verification**

```bash
uv run pytest -q tests/experiments/e3/test_world.py
uv run ruff check aire_prime/experiments/e3 tests/experiments/e3
uv run mypy aire_prime
```

Expected: all pass.

**Step 5: Commit**

```bash
git add aire_prime/experiments/e3 tests/experiments/e3
git commit -m "feat: add deterministic E3 causal worlds"
```

### Task 2: Prove packet capacity and prevent validator leakage

**Files:**

- Create: `aire_prime/experiments/e3/leakage.py`
- Create: `tests/experiments/e3/test_leakage.py`
- Modify: `aire_prime/experiments/e3/world.py`

**Step 1: Write failing leak and capacity tests**

```python
@pytest.mark.parametrize(
    "forbidden",
    ("latent_state", "optimal_action", "validator_spec", "split_name", "root_seed"),
)
def test_proposer_wire_excludes_validator_fields(forbidden: str) -> None:
    wire = canonical_bytes(generate_world(WorldKey(family="surface", seed=301)).proposer_view())
    assert forbidden.encode() not in wire


def test_policy_table_lower_bound_exceeds_packet_budget() -> None:
    suite = generate_suite(root_seed=301, split="source")
    assert minimum_exact_policy_bytes(suite) > E3_PACKET_BYTES
```

Add mutation tests for filenames, episode order, padding, content IDs, nuisance-only predictors, and
metadata-only predictors.

**Step 2: Run and observe RED**

```bash
uv run pytest -q tests/experiments/e3/test_leakage.py
```

**Step 3: Implement explicit proposer/validator projections and audits**

`proposer_view()` must construct a new typed object from an allowlist. It must not serialize the
full object and delete keys. Implement deterministic chance-envelope and packet-capacity reports as
content-addressed evidence.

**Step 4: Verify**

```bash
uv run pytest -q tests/experiments/e3/test_world.py tests/experiments/e3/test_leakage.py
uv run ruff check .
uv run mypy aire_prime
git diff --check
```

**Step 5: Commit**

```bash
git add aire_prime/experiments/e3 tests/experiments/e3
git commit -m "test: enforce E3 capacity and leakage boundaries"
```

### Task 3: Add adaptation metrics and confirmatory analysis

**Files:**

- Create: `aire_prime/experiments/e3/metrics.py`
- Create: `aire_prime/experiments/e3/analysis.py`
- Create: `tests/experiments/e3/test_metrics.py`
- Reference: `docs/research/E3_PREREGISTRATION.md`

**Step 1: Write failing unit tests**

Cover:

- exact trapezoidal adaptation AUC;
- normalization against no-transfer and oracle;
- worlds, not episodes, as independent bootstrap units;
- maximum baseline selected inside each bootstrap replicate;
- deterministic 100,000-replicate distribution;
- per-family noninferiority;
- targeted-minus-maximum-sham effect;
- Holm correction;
- missing/invalid arms produce `undetermined`.

```python
def test_bootstrap_resamples_worlds_not_episodes() -> None:
    result = analyze_confirmatory(fixture_blocks(), seed=991)
    assert result.resampling_unit == "world"
    assert len(result.primary.bootstrap_distribution) == 100_000
```

**Step 2: Observe RED**

```bash
uv run pytest -q tests/experiments/e3/test_metrics.py
```

**Step 3: Implement the frozen formulas**

Use NumPy only. Validate finite values, disjoint/exhaustive buckets, exact arm/world/recipient
matrices, and complete distribution retention. Do not add scientific-computing dependencies unless
the decision record proves NumPy insufficient.

**Step 4: Verify and commit**

```bash
uv run pytest -q tests/experiments/e3/test_metrics.py
uv run ruff check .
uv run mypy aire_prime
git diff --check
git add aire_prime/experiments/e3 tests/experiments/e3
git commit -m "feat: add preregistered E3 adaptation analysis"
```

### Task 4: Implement recipient families and mandatory baselines

**Files:**

- Create: `aire_prime/experiments/e3/recipient.py`
- Create: `aire_prime/experiments/e3/baselines.py`
- Create: `aire_prime/experiments/e3/contracts.py`
- Create: `tests/experiments/e3/test_recipients.py`
- Create: `tests/experiments/e3/test_baselines.py`
- Modify: `schemas/` through `scripts/export_schemas.py`
- Reference: `docs/research/E3_BASELINE_CONTRACT.md`

**Step 1: Write failing recipient-independence tests**

Test that every recipient has a distinct identity and seed, receives no shared weights/optimizer
state, executes through the reviewed adapter, accepts only the typed packet language, and gets the
same calibration schedule.

**Step 2: Write failing baseline contract tests**

Implement expected tests for B0 through B6 and B9 first. Tests must prove exact packet bytes,
identical observation access, identical target interactions, frozen deterministic fitting, complete
failure evidence, and exclusion of the oracle from maximum-baseline selection.

```python
def test_every_eligible_arm_has_identical_hard_budget() -> None:
    contract = build_baseline_contract()
    assert len({arm.hard_budget for arm in contract.eligible_arms}) == 1
    assert contract.oracle_arm not in contract.eligible_arms
```

**Step 3: Observe RED**

```bash
uv run pytest -q tests/experiments/e3/test_recipients.py tests/experiments/e3/test_baselines.py
```

**Step 4: Implement minimal deterministic recipients and baselines**

Use fixed algorithms and explicit operation counters. B7 and B8 require a separate compatibility
decision after the related-work extension; do not silently substitute weaker methods.

**Step 5: Run adversarial verification**

Add tests rejecting oversized packets, extra calibration, hidden observation access, invalid
recipients, shared random streams, malformed typed programs, unregistered responses, and missing
resource evidence.

**Step 6: Verify and commit**

```bash
uv run pytest -q tests/experiments/e3 tests/agents tests/measurement
uv run python scripts/export_schemas.py
uv run python scripts/export_schemas.py --check
uv run ruff check .
uv run mypy aire_prime
git diff --check
git add aire_prime tests schemas DECISIONS.md docs/research/E3_RELATED_WORK.md
git commit -m "feat: freeze E3 recipients and baseline frontier"
git push -u origin research/e3-causal-language
```

This commit is a baseline implementation checkpoint, not the benchmark freeze. Candidate work
remains blocked until the baseline/oracle-only pilot and Task 5 freeze are complete.

### Task 5: Run baseline-only pilot and freeze the benchmark

**Files:**

- Create: `aire_prime/experiments/e3/pilot.py`
- Create: `tests/experiments/e3/test_pilot.py`
- Create: `docs/research/E3_PILOT_REPORT.md`
- Create: `docs/research/E3_BENCHMARK_FREEZE.md`
- Modify: `docs/research/E3_PREREGISTRATION.md`
- Modify: `DECISIONS.md`
- Modify: `PROGRESS.md`

**Step 1: Write failing pilot-boundary tests**

Prove the pilot runner contains only baselines and the oracle, cannot import or name a candidate,
cannot construct confirmatory seeds, and produces world-level variance and capacity/leakage reports.

```python
def test_pilot_has_no_candidate_or_confirmatory_access() -> None:
    manifest = build_pilot_manifest(root_seed=301)
    assert "candidate" not in manifest.arm_ids
    assert manifest.split == "development"
```

**Step 2: Implement and run the baseline/oracle-only pilot**

```bash
uv run pytest -q tests/experiments/e3/test_pilot.py
uv run python -m aire_prime.experiments.e3.pilot \
  --seed 301 --output /private/tmp/aire-e3-pilot-301
```

The pilot may estimate between-world variance, reject an impossible benchmark, repair invalid
baselines, and tune only fields explicitly marked pilot-tunable. It may not measure a candidate or
derive confirmatory seeds.

**Step 3: Freeze the evaluation**

Use only baseline/oracle pilot evidence to freeze the task scale, primary formula, effect and
noninferiority margins, causal margin, arm/recipient/shift sets, resource claim type, sample-size
rule, randomization, bootstrap seed/count, retry policy, and exclusion rules. Record the pilot and
power analysis in the two new documents.

**Step 4: Review and verify**

Review for capacity failure, task impossibility, baseline weakness, leakage, pseudoreplication,
multiple comparisons, post-hoc freedom, and resource mismatch. Resolve all Critical and Important
findings, then run:

```bash
uv run pytest -q tests/experiments/e3 tests/agents tests/measurement
uv run ruff check .
uv run mypy aire_prime
uv run python scripts/export_schemas.py --check
git diff --check
```

**Step 5: Commit, push, and record the irreversible benchmark freeze**

```bash
git add aire_prime/experiments/e3 tests/experiments/e3 docs/research DECISIONS.md PROGRESS.md
git commit -m "docs: freeze E3 benchmark and baseline frontier"
git push -u origin research/e3-causal-language
git ls-remote --heads origin research/e3-causal-language
```

Candidate implementation is prohibited until local and remote heads equal this green freeze.

### Task 6: Implement the sparse causal-program candidate

**Files:**

- Create: `aire_prime/experiments/e3/candidate.py`
- Create: `tests/experiments/e3/test_candidate.py`
- Modify: `aire_prime/experiments/e3/contracts.py`

**Step 1: Write failing contract tests**

Test that candidate input is exactly the declared source interaction evidence; output is no more
than 2,048 canonical bytes; operators come from the existing reviewed allowlist; and output contains
no weights, unrestricted code, paths, imports, target IDs, or validator fields.

**Step 2: Write failing mechanism tests**

Use public worlds to test recovery of a small known mechanism composition, reuse on a distinct
surface encoding, and failure when intervention evidence is insufficient.

**Step 3: Observe RED**

```bash
uv run pytest -q tests/experiments/e3/test_candidate.py
```

**Step 4: Implement the minimum candidate**

Implement intervention selection, sparse mechanism fitting, typed graph serialization, and bounded
recipient alignment. Do not tune against confirmatory worlds or add a second candidate family.

**Step 5: Verify and commit**

```bash
uv run pytest -q tests/experiments/e3/test_candidate.py tests/experiments/e3/test_recipients.py
uv run ruff check .
uv run mypy aire_prime
git diff --check
git add aire_prime/experiments/e3 tests/experiments/e3
git commit -m "feat: add E3 sparse causal-program transfer"
```

### Task 7: Add causal, sham, and wrong-object transformations

**Files:**

- Create: `aire_prime/experiments/e3/ablations.py`
- Create: `tests/experiments/e3/test_ablations.py`

**Step 1: Write failing tests for exact transformation families**

Prove targeted and sham packets have identical byte size, operator count, and execution budget;
target selection is frozen from public/pilot evidence; the wrong-object packet comes from a
different committed family; and every transformation changes its content ID.

**Step 2: Observe RED**

```bash
uv run pytest -q tests/experiments/e3/test_ablations.py
```

**Step 3: Implement transformations without using confirmatory outcomes**

Follow the six transformations in `E3_PREREGISTRATION.md`. Persist exact changed component IDs and
retain failed executions.

**Step 4: Verify and commit**

```bash
uv run pytest -q tests/experiments/e3/test_ablations.py tests/experiments/e3/test_candidate.py
uv run ruff check .
uv run mypy aire_prime
git diff --check
git add aire_prime/experiments/e3 tests/experiments/e3
git commit -m "test: add E3 causal transfer ablations"
```

### Task 8: Add the E3 runner, evidence packet, and CLI inspection

**Files:**

- Create: `aire_prime/experiments/e3/run.py`
- Create: `tests/experiments/e3/test_run.py`
- Modify: `aire_prime/cli.py`
- Modify: `tests/test_end_to_end.py`
- Modify: `README.md`
- Modify: `scripts/export_schemas.py`
- Modify: `schemas/`

**Step 1: Write failing end-to-end tests**

Test `aire-prime e3 pilot`, `aire-prime e3 confirm`, and `aire-prime report show`. The inspector must
reject missing artifacts, manifest additions, substituted contracts, seed-domain mismatch,
post-freeze code identity mismatch, incomplete arm matrices, leakage failures, and grounding above
`G-S`.

**Step 2: Observe RED**

```bash
uv run pytest -q tests/experiments/e3/test_run.py tests/test_end_to_end.py
```

**Step 3: Implement a closed E3 manifest**

Persist canonical world/split commitments, research/evaluation/resource contracts, arm packets,
requests/responses, per-world observations, resource sidecars, leakage report, complete bootstrap
distribution, occurrence/improvement reports, and final E3 report. Host metadata remains clearly
separate from canonical scientific identity where required.

**Step 4: Verify and commit**

```bash
uv run pytest -q tests/experiments/e3/test_run.py tests/test_end_to_end.py
uv run python scripts/export_schemas.py
uv run python scripts/export_schemas.py --check
uv run ruff check .
uv run mypy aire_prime
git diff --check
git add aire_prime tests scripts schemas README.md
git commit -m "feat: expose auditable E3 experiment workflow"
```

### Task 9: Freeze the candidate and confirmatory contract

**Files:**

- Create: `docs/research/E3_CONFIRMATORY_FREEZE.md`
- Modify: `DECISIONS.md`
- Modify: `PROGRESS.md`

**Step 1: Confirm the benchmark freeze is unchanged**

Compare the current world, baseline, metric, analysis, threshold, and power-analysis identities to
`E3_BENCHMARK_FREEZE.md`. Any material difference requires a new experiment version, not an amended
E3-v1 confirmatory run.

**Step 2: Conduct adversarial preregistration review**

Review for leakage, favorable baseline omission, pseudoreplication, post-hoc degrees of freedom,
capacity loopholes, recipient sharing, metric gaming, and claim escalation. Resolve all Critical and
Important findings before seed derivation.

**Step 3: Run the full preconfirmatory gate**

```bash
uv run pytest --cov=aire_prime --cov-report=term-missing --cov-fail-under=90
uv run ruff check .
uv run mypy aire_prime
uv run python scripts/export_schemas.py --check
git diff --check
```

**Step 4: Freeze, commit, push, and record the remote commit**

```bash
git add aire_prime tests scripts schemas README.md docs/research DECISIONS.md PROGRESS.md
git commit -m "docs: freeze E3 confirmatory protocol"
git push origin research/e3-causal-language
git ls-remote --heads origin research/e3-causal-language
```

Do not amend or force-push this checkpoint.

### Task 10: Derive and run confirmatory evidence once

**Files:**

- Generated outside Git: confirmatory run directories
- Create: `docs/research/E3_RESULTS.md`
- Create: `docs/research/E3_EVIDENCE_MATRIX.md`
- Modify: `PROGRESS.md`
- Modify: `REVIEW.md`
- Modify: `docs/AIRE_V0_1_STATUS_AND_ROADMAP.md`

**Step 1: Derive seeds from the pushed frozen commit**

The CLI must derive the root seed using the exact domain in `E3_WORLD_SPEC.md` and write the split
commitments before scoring.

**Step 2: Run confirmatory evaluation once**

```bash
uv run aire-prime e3 confirm \
  --frozen-commit <PUSHED_FREEZE_COMMIT> \
  --output /private/tmp/aire-e3-confirmatory
uv run aire-prime report show --input /private/tmp/aire-e3-confirmatory
uv run aire-prime registry verify \
  --path /private/tmp/aire-e3-confirmatory/registry.jsonl
```

Do not rerun to select a favorable seed. An infrastructure failure follows only the frozen retry
policy and remains in evidence.

**Step 3: Publish the supported classification**

Write results as transferred, partial, negative, or undetermined strictly from the frozen decision
object. Include all arms, recipients, shift families, exclusions, resource evidence, and failed
gates. Do not use secondary outcomes to rescue the primary claim.

**Step 4: Commit and push the results report**

```bash
git add docs/research PROGRESS.md REVIEW.md docs/AIRE_V0_1_STATUS_AND_ROADMAP.md
git commit -m "docs: publish frozen E3 research result"
git push origin research/e3-causal-language
```

Generated raw evidence is committed only if the repository's frozen artifact policy explicitly
requires it and size/privacy checks pass; otherwise publish hashes, manifests, and reproduction
commands.

### Task 11: Fresh-clone reproduction and final handoff

**Files:**

- Modify: `docs/research/E3_RESULTS.md`
- Modify: `docs/research/E3_EVIDENCE_MATRIX.md`
- Modify: `PROGRESS.md`
- Modify: `REVIEW.md`

**Step 1: Clone the pushed branch into a fresh temporary directory**

```bash
git clone --branch research/e3-causal-language --single-branch \
  https://github.com/deesatzed/AIRE_Prime.git /private/tmp/aire-e3-fresh
```

**Step 2: Reproduce the complete static and test surface**

```bash
uv sync --frozen
uv run pytest --cov=aire_prime --cov-report=term-missing --cov-fail-under=90
uv run ruff check .
uv run mypy aire_prime
uv run python scripts/export_schemas.py --check
git diff --check
```

**Step 3: Reproduce the canonical report**

Run the confirmatory command using the same frozen commit and verify canonical report ID, decision
ID, split root, registry evidence, and classifications. Host timing/RSS may differ and must remain
identified as host observations.

**Step 4: Final review**

Classify every correctness, statistics, security, leakage, resource, and claim-boundary finding.
Resolve all Critical and Important findings without altering the frozen scientific decision. A
scientific correction creates a new version and preserves the original result.

**Step 5: Commit and push handoff documentation**

```bash
git add docs/research PROGRESS.md REVIEW.md
git commit -m "docs: complete E3 evidence handoff"
git push origin research/e3-causal-language
git status --short --branch
git ls-remote --heads origin research/e3-causal-language
```

Expected: clean branch, local `HEAD` equals the remote branch, and the handoff states the exact
positive, negative, partial, or undetermined result without physical, QEC, intelligence, or novelty
overclaiming.
