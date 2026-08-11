# AIRE Prime v0.1 Final Evidence Matrix

**Verification date:** 2026-08-07

**Verified Task 12 checkpoint:** `fed1e3a68b342d9efec40097c8a969966645eb7f`

**Published Q12D recovery checkpoint:** `cbd14aa8d08f1ea73469353a1cf4722b572df82c`

## Outcome summary

The remaining-steps implementation goal is complete: Q12D is preserved in a distinct verified
remote, AIRE Tasks 7--12 are implemented and pushed, external reproduction works, and the evidence
and claim boundaries survive the release gate.

The stronger positive scientific acceptance condition is **not** met. E2 remains
`simulated-alien-sense-transfer-not-established`, O0/G-S. Missing peak-RSS and elapsed-time
observations leave resource matching and improvement undetermined. This matrix does not relabel
that red scientific gate as success.

## Master-goal proof matrix

| Goal criterion | Status | Evidence |
| --- | --- | --- |
| Repository/recovery preflight | Pass | `PROGRESS.md` records root, branch, remote, clean starting head, fetch/fsck/reflog findings, and source inventory. |
| Q12D copied, byte-verified, committed, and remotely distinct | Pass | Q12Dgates `main` at `cbd14aa8d08f1ea73469353a1cf4722b572df82c`; 26 files, 591,420 bytes, inventory stream SHA-256 `c48fbbce1885c88f293222421033a9885562207bc57ed283d6bfb97be1e3a5f5`; fresh-clone verification recorded in `PROGRESS.md`. |
| Task 7 fail-closed host containment | Pass within declared host | Commits `b19cfb3` and `a9b9961`; hostile filesystem, network, fork, descriptor, artifact-race, and resource tests; exact threat model and residual limits in `REVIEW.md` D-007--D-009. |
| Task 8 E1 capability reconstruction | Pass | Commits `4bd84a6` and `cdfbf68`; seed-101 report `sha256:b709fbf42e25d2a8db6e4244472b739503e2d4fb458967bcc2080ddbf3348813`; O4/G-S; five byte-matched baselines. |
| Task 9 Measurement Layer Zero | Pass | Commits `d0bd6c3` and `f8a1161`; matched arms, protected floors, ablations, deterministic bootstrap, and explicit undetermined measurements. |
| Task 10 E2 simulated experiment | Pass as honest negative/undetermined experiment | Commit `f949918`; seed-202 report `sha256:3f60ac64e2190fbdd0705e8ef6bad7e8a701e9a42087a82a32d1afeb695a81bc`; O0/G-S; failed gates `heldout-gain`, `matched-controls`. |
| Task 11 external CLI and inspection | Pass | Commit `664ed94`; exact CLI commands, wheel installation, schema resources, contract/registry/grounding tamper rejection, and complete evidence manifests. |
| Task 12 adversarial review/evidence publication | Pass | Commit `fed1e3a`; 45 adversarial tests across claim, gaming, and packet suites; three final independent Ready verdicts; `docs/AIRE_V0_1_EVIDENCE.md`. |
| Full clean-environment release gate | Pass | Fresh clone of `fed1e3a`: 296 tests passed, 92.29% coverage; Ruff, strict mypy (48 files), schema freshness, wheel install, real containment, and diff checks passed. |
| Clean, remotely synchronized feature branch | Pass at published checkpoint | Fresh clone clean on `feature/aire-v0.1`; local and `origin/feature/aire-v0.1` both resolved to `fed1e3a` before this final documentation commit. |

## Canonical design acceptance criteria

| Design criterion | Status | Evidence or unresolved limitation |
| --- | --- | --- |
| 1. Fresh recipient reconstructs a reusable capability from a bounded GRO | Met in E1 simulation | E1 seed-101 candidate passes contained transfer, composition, repair, and hidden validation. |
| 2. Realization adapts to hidden goals and changed local resources | Met in E1 simulation | Three separately committed tasks and changed-resource world; candidate passes while five equal-byte alternatives fail. |
| 3. Synthetic sense reaches O4/G-S | **Not met** | E2 is O0/G-S because matched-resource and improvement gates remain undetermined. |
| 4. Targeted ablation exceeds matched sham ablations | Met as an E2 subtest | Targeted causal-channel intervention exceeds three equal-size inert-channel shams. This does not override failed gates. |
| 5. Sense outperforms declared baselines under matched resources | **Not met** | Behavioral scores exceed controls, but peak RSS and elapsed time are undetermined; matched-resource comparison does not pass. |
| 6. Independent validation reproduces the result | Met for bounded deterministic subtests | Distinct-seed contained discovery/recipient and fresh-clone canonical evidence reproduce; the positive E2 occurrence claim remains unestablished. |
| 7. Natural-language explanation is unnecessary for machine transfer | Met in E1/E2 protocols | Reference-only canonical packets and allow-listed constructors carry machine structure without a natural-language baseline. |
| 8. Failures, grounding, resources, and validity limits remain visible | Met | Reports retain failed gates; resource states render `undetermined`; append-only registries, evidence document, and review record preserve limitations. |
| 9. No result is described as superintelligence or new physics | Met | CLI classification allowlist, release Markdown scanner and mutations, README disclaimers, and `docs/AIRE_V0_1_EVIDENCE.md`. |

## Final verification checklist

| Check | Evidence |
| --- | --- |
| Pinned reports reproduce | Fresh clone produced the exact E1/E2 report IDs above. |
| Registries verify | E1: 62 events, head `sha256:f2ee52c431986a2761bfd7dea17df16e2c75c7ca132d7d5596b10eb5f8a912b5`; E2: 53 events, head `sha256:026454dd53f2fd1c6363b7ad4213f0fcf5a0ba2257aa73e9619aa68542d4c314`. |
| Canonical files reproduce | E1 report SHA-256 `729363194ec8023dd08d8631aca5feaea2b626b4543a6d399a24cb3703501f7a`; E1 registry `232a3de63f9e8e7608eada3e2a4102504478b2bd9a50e9b46aa03cb8388ae365`; E2 report `2eee8e09c21edf7a7e3d42badb0e62288e45ddb80e46ec8c2af45904e370bf44`; E2 registry `cd09e5ea5381be7621dd3b26bcb3a034a38c644f4f291679e7be72a672072b2f`. |
| Validator isolation | Typed independent identities, hidden-context exclusions, frozen contracts, and request/response lineage tests pass. |
| No arbitrary packet execution | Allow-listed realizer, reference-only protocol, executable pickle sentinel, audited ingress, and contained hostile-child tests pass. |
| Occurrence/grounding separation | Object invariants, report inspection, and claim-boundary tests pass; E1 O4/G-S and E2 O0/G-S remain distinct. |
| Resource accounting honest | Six E2 dimensions observed; peak RSS and elapsed time explicitly undetermined, never zero. |
| Failure evidence retained | Typed ingress/realization failures and failed scientific gates resolve through tamper-evident registries. |
| Repository scope clean | Q12D originals are absent from AIRE history; caches, virtual environments, and temporary runs are ignored and uncommitted. |
| Deployment boundary | No merge, release, deployment, provider integration, physical experiment, E3--E5 implementation, or autonomous external action occurred. |

## Exact reproduction commands

```bash
git clone --branch feature/aire-v0.1 --single-branch https://github.com/deesatzed/AIRE_Prime.git AIRE_Prime
cd AIRE_Prime
uv sync --frozen
uv run ruff check .
uv run mypy
uv run python scripts/export_schemas.py --check
uv run pytest --cov=aire_prime --cov-report=term-missing --cov-fail-under=90
uv run aire-prime e1 run --seed 101 --output /tmp/aire-prime-e1
uv run aire-prime e2 run --seed 202 --output /tmp/aire-prime-e2
uv run aire-prime registry verify /tmp/aire-prime-e1/registry.jsonl
uv run aire-prime registry verify /tmp/aire-prime-e2/registry.jsonl
uv run aire-prime report show /tmp/aire-prime-e1
uv run aire-prime report show /tmp/aire-prime-e2
git diff --check
git status --short --branch
```

The branch is review-ready, not deployed. Scientific follow-up must first resolve the explicit E2
resource-evidence gap; it may not promote the present O0/G-S result by wording alone.
