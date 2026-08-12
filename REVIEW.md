# AIRE Prime Task 7 Containment Review

## Scope and judgment

This review covers the Task 7 agent boundary on `feature/aire-v0.1` against
`GOAL_REMAINING_STEPS.md`. Specification/code-quality, security, and test-gap reviewers examined
the implementation in three rounds. Their early Critical and Important findings were either
implemented and re-tested or adjudicated below with explicit threat-model evidence.

Reviewed implementation commit: `b19cfb3`.

**Judgment: Task 7 is ready to close on its deliberately narrow supported host: macOS 27 on
arm64, only when the functional Seatbelt probe passes.** Every other platform, architecture,
version, or unavailable launcher returns typed `ContainmentUnavailable` evidence without starting
the configured child.

This is a contained trusted-command boundary, not safe execution of packet-provided code and not
protection from a compromised parent, root, kernel, or concurrent same-UID process acting before
launch.

## Accepted and resolved findings

| Severity | Finding | Disposition and evidence |
| --- | --- | --- |
| Critical | Filesystem and network syscalls were unrestricted. | **Accepted / resolved.** The version-gated macOS Seatbelt profile denies undeclared file contents and metadata, write paths, loopback TCP, non-loopback local TCP, routed nonlocal UDP, and `network*`. Positive tests retain declared read/write and canonical JSONL behavior. |
| Critical | Relative or option-embedded paths bypassed attestation. | **Accepted / resolved.** Every nonabsolute argument now requires an explicit literal index and bounded opaque-token grammar. Path-shaped relative and `--option=path` strings are rejected. Absolute artifacts remain exact and complete. |
| Critical | Unrestricted `process-exec` let the child replace itself with arbitrary tools. | **Accepted / resolved.** Seatbelt permits only the reviewed `/bin/sh`/`/bin/bash` resource launcher variants and the attested executable. A hostile Perl fixture cannot exec `/usr/bin/true`. |
| Important | Path verification followed ordinary mutable path execution. | **Accepted / resolved.** Each artifact is copied only after digest/device/inode/size verification, reopened read-only, unlinked, and supplied through an inherited descriptor. Tests cover truncate-in-place/path replacement and child attempts to rewrite the snapshot. |
| Important | Allowlist file-to-directory replacement widened a literal to a subtree rule. | **Accepted / resolved.** Allowances bind resolved path, file type, device, and inode at configuration, re-verify before profile creation, and retain the originally attested literal/subpath rule. |
| Important | `preexec_fn` was unsafe and resource limits disappeared when it was removed. | **Accepted / resolved.** No `preexec_fn` remains. A fixed reviewed shell launcher applies zero core/process limits, 30 seconds CPU, a 1 MiB file-size ceiling, and 256 open files before `exec`. Wall time, input, aggregate output, artifact count, argv count/bytes, and process-group cleanup remain bounded. Fork and descriptor-exhaustion fixtures observe the enforced limits. |
| Important | Backend availability was inferred from the launcher file and denial tests could pass when the launcher never started the fixture. | **Accepted / resolved.** Availability now includes OS/architecture checks and a functional sandbox application probe. Network/fork fixtures emit valid JSONL only after seeing the expected syscall denial; launcher refusal instead produces `ContainmentUnavailable`. |
| Important | Imported `system.sb` allowed sensitive system files and ambient mutable policy. | **Accepted / bounded.** `/private/etc/passwd`, `/private/etc/master.passwd`, `/cores`, all network operations, and forks are explicitly re-denied. Explicit runtime roots and devices are narrowed. The Apple-private profile remains platform TCB, so support is restricted to tested macOS major version 27, arm64, plus a per-instance functional probe. Patch-level policy drift and the imported profile's named Mach/XPC services are documented residual authorities. |
| Important | Literal tokens and the total argv were not actually bounded. | **Accepted / resolved.** Literal tokens are capped at 64 characters, commands at 64 arguments and 8,192 UTF-8 bytes, with boundary tests. |

## Rejected or explicitly scoped findings

- **Concurrent same-UID allowlist replacement after final verification:** rejected as a Task 7
  blocker. Seatbelt is pathname-based and cannot atomically bind a directory subtree by descriptor.
  The supported threat model starts with a trusted parent/configuration and protects against the
  approved hostile child after launch. A concurrent compromised same-UID host process is outside
  this boundary. Pre-run file/type/inode replacement is tested and rejected; command artifacts,
  which are executable inputs, are immutable snapshots.
- **The reviewed shell variants are “undeclared executable escapes”:** rejected as a capability
  escalation. They are part of the fixed resource launcher TCB and inherit the same Seatbelt and
  hard resource policy. A regression proves re-executing `/bin/bash` cannot read an undeclared
  sentinel, while an unrelated executable is denied. The approved child is already arbitrary code
  within the same sandbox, so the launcher adds no filesystem, network, fork, or resource authority.
- **Host path allowances must equal wire `declared_inputs`:** rejected as a protocol requirement.
  Host capabilities are supplied only by trusted adapter construction, never by packet fields.
  An adapter instance represents one fixed authority profile; callers must construct a different
  adapter for a different path authority.
- **A public Internet endpoint is required for external-network proof:** rejected. A routed
  nonlocal UDP address (`192.0.2.1`) deterministically proves address-independent outbound denial
  without depending on a third party, alongside loopback and non-loopback interface TCP controls.

## Residual limitations

- `system.sb` is an Apple-private, patch-mutable platform dependency and retains selected standard
  Mach/XPC and system-runtime authorities. The functional probe proves profile application, not
  semantic immutability of every imported rule.
- Seatbelt and the portable shell launcher do not provide a separately verified address-space
  limit on this host. CPU/wall time, output/file size, process count, descriptor count, and allowed
  paths constrain the tested denial surface, but memory-pressure attacks remain a declared threat
  for later native-launcher hardening.
- Only macOS 27 arm64 is declared supported. Non-Darwin, other architectures, and unreviewed macOS
  major versions fail closed.
- The system-runtime read roots are trusted runtime dependencies, not user-declared research data.
  File metadata outside those roots and explicit allowances is denied in integration tests.

## Verification evidence

The final verification commands and exact results are recorded in `PROGRESS.md`. The focused suite
contains 63 tests, including real hostile-child integration for undeclared content/metadata reads,
write denial, loopback/local-interface/routed-nonlocal network denial, fork denial, descriptor
inheritance and exhaustion, executable replacement, artifact swapping, snapshot mutability,
allowlist type swaps, JSONL exchange, deterministic environment, timeout, and bounded I/O.

No Task 8 experiment, provider, physical action, deployment, or claim escalation is part of this
review.

## Task 10 E2 adversarial review

Four read-only review rounds challenged the E2 implementation. Findings were classified and
resolved as follows:

- **Accepted:** fail-open gate classification, discovery-label leakage, parent-only discovery,
  raw-mapping transfer, hard-coded controls and ablations, aggregate-as-sample measurement,
  same-world reproduction, unconditional positive narratives, incomplete resource accounting,
  post-outcome contract binding, incomplete constructor validation, and unresolved wire lineage.
- **Accepted:** invented RSS and elapsed values were removed. Their absence now remains explicitly
  `undetermined`, which prevents the matched-control and provisional-improvement gates from passing.
- **Accepted:** control measurement provenance now survives into `ImprovementDecision`, and every
  baseline, ablation, and reproduction request/response resolves through the append-only registry.
- **Rejected:** no reviewer recommendation was rejected on convenience grounds. The requested
  `O4/G-S`-eligible path was deliberately not preserved when its resource evidence could not be
  supported.
- **Needs investigation:** reproducible host RSS and elapsed-resource evidence remains future work;
  it is not a hidden completion claim or a reason to reinterpret the present `O0/G-S` result.

**Final verdict: Ready.** No Critical or Important findings remain. Task 10 is ready as an honest,
deterministic, simulated negative/undetermined result—not established alien-sense transfer and not
physical, QEC, superintelligence, or new-physics evidence.

## Task 11 CLI and evidence-inspection review

Independent read-only review challenged the packaged CLI, exact E1/E2 manifests, installed-wheel
behavior, and fail-closed evidence inspection.

- **Accepted / resolved:** E1 now persists and canonically registers its procedural world; E2
  persists and canonically registers its measurement decision; both report identities resolve to
  the exact canonical bytes stored in the registry.
- **Accepted / resolved:** inspection validates typed scientific objects and contracts, linked
  request/response identities, response success, complete receipt coverage, exact manifest counts,
  grounding ceilings, and registry resolution rather than trusting summary fields.
- **Accepted / resolved:** root schemas are force-included in the built wheel and loaded through
  package resources. The install test proves the console entry point and schema check work from a
  temporary environment outside the repository.
- **Accepted / resolved:** negative tests cover missing responses and receipts, substituted
  decisions and scientific objects, malformed metric and contract evidence, unregistered or
  mislinked responses, physical-grounding escalation, and contained resource failures.

**Final verdict: Ready.** No Critical or Important findings remain. Task 11 is suitable to commit
and proceed to the Task 12 adversarial release review.

## Task 12 adversarial release review

Three independent read-only review streams covered correctness/architecture, security and
loopholes, and missing tests. Findings were classified and resolved through repeated review:

- **Accepted / resolved:** source-literal and exact-phrase scans were replaced with actual
  CLI-rendered classification/grounding checks plus proposition-scoped mutation testing.
- **Accepted / resolved:** test-manufactured rejection records were replaced by production audited
  ingress and realization boundaries that store their exact typed results.
- **Accepted / resolved:** malformed and noncanonical wire, wrong envelope kind, wrong request link,
  role conflict, and file-access output are all registered by the real adapter path when auditing is
  configured. Failure detail identity is code-derived; a separate wire hash retains provenance.
- **Accepted / resolved:** inert pickle data was replaced with an executable reduce sentinel whose
  absence proves no deserialization side effect.
- **Accepted / resolved:** label-only metric fixtures were replaced by four bounded gaming agents
  whose behavior generates the samples, protected outcomes, access declarations, and priors sent
  through frozen Measurement Layer Zero adjudication.
- **Accepted / resolved:** file-descriptor capture made the suite order-dependent; the lightweight
  claim test now uses stream capture, and the exact reproducer passes before contained E1/E2.
- **Needs investigation at review time / subsequently resolved:** fresh-clone verification was the
  next release gate, not an implementation-review defect; the final handoff gate below records its
  successful completion.

**Final verdict: Ready.** No Critical or Important findings remain. The latest host gate passes 296
tests at 92.29% coverage with Ruff, strict mypy, schema freshness, and diff checks green. Task 12 is
ready to commit and publish for fresh-clone reproduction, which subsequently passed below.

## Final handoff review

The pushed Task 12 checkpoint `fed1e3a` passed the full gate again from a fresh single-branch clone.
Pinned E1/E2 report IDs, registry heads, and canonical file hashes match the development-worktree
references. The clone is clean, and the published branch is review-ready.

**Release-boundary judgment: Ready for code review, not deployment.** The implementation goal is
complete, but the positive design criteria requiring E2 O4/G-S and matched-resource superiority
remain unmet. That scientific red state is explicit in the final evidence matrix and is not a
software-release failure or a positive result.

## Option B resource-instrumentation follow-up

- **Accepted:** elapsed time is measured by the trusted parent monotonic clock; peak RSS uses per-child
  POSIX `wait4` usage when available.
- **Accepted:** measurements are kept in a separate noncanonical `resource_observations.json` sidecar
  and do not alter response wire identities or canonical E2 report IDs.
- **Needs investigation:** a preregistered aggregation/tolerance rule is still required before these
  host observations can adjudicate matched-resource superiority. The reviewed elevated Seatbelt
  probe now passes and two real seed-202 runs produced complete sidecars, but no scientific claim was
  advanced from post-hoc host measurements.

**Follow-up verdict: Instrumentation and production observation are ready; scientific gate remains
open.** The focused gate is green and the containment rerun is reproducible. A subsequent experiment
version must freeze resource aggregation/tolerance before these observations can affect scoring.

## E3 research-package review

- **Accepted / resolved:** E2's binary world and two-row lookup are an infrastructure-quality
  scientific baseline, not a sufficient breakthrough task. E3 is versioned separately and cannot
  reinterpret E2.
- **Accepted / resolved:** the initial E3 draft placed a public pilot after candidate implementation,
  allowing candidate behavior to influence thresholds. The final sequence makes the pilot
  baseline/oracle-only and freezes the benchmark, margins, sample-size rule, and analysis before
  candidate code exists.
- **Accepted / resolved:** the goal allows transferred, partial, negative, and undetermined terminal
  states and separates engineering completion from scientific success.
- **Needs investigation:** the B7 causal-representation and B8 symmetry/alignment baselines require
  an extended compatibility audit before the baseline freeze.
- **Needs investigation:** an outside seed custodian and independently implemented recipient are not
  currently available. Their absence must keep the strongest independent-confirmation gate open.

**Planning verdict: Ready to publish as a research contract, not an E3 result.** The complete 300-test
suite, Ruff, strict mypy, schema freshness, and diff checks pass; no E2 implementation or test file
is changed. Candidate implementation remains blocked until the baseline/oracle pilot and pushed
benchmark freeze are complete.
# E3 Confirmatory Review

## Disposition

The E3 v1 one-shot confirmatory run is reviewable as a negative behavioral result with an
undetermined overall superiority claim. The benchmark and confirmatory protocol were frozen and
pushed before candidate seed derivation. The raw result retains the complete arm/world/recipient
matrix and the report is constrained to simulated `G-S` grounding.

## Findings

- **Primary statistics:** candidate did not exceed the strongest eligible baseline; accepted as
  negative under the frozen rule.
- **Causal ablation:** targeted-minus-sham margin failed; no causal-use claim is supported.
- **Leakage/capacity:** development audits passed; no validator-only field appeared in proposer
  bytes and exact policy capacity exceeded the packet ceiling.
- **Resources:** hard dimensions are recorded, but host RSS/timing are absent, so an overall
  superiority claim remains undetermined rather than resource-equivalent.
- **Independent confirmation:** unavailable; the internal run is not called independent
  confirmation.
- **Claim boundary:** no physical, QEC, intelligence, consciousness, or new-physics inference.

All findings are retained in `E3_RESULTS.md` and `E3_EVIDENCE_MATRIX.md`; no frozen scientific
decision was rewritten.
