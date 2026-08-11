# AIRE Prime v0.1 Evidence Boundary

**Evidence date:** 2026-08-07

**Branch:** `feature/aire-v0.1`

**Task 11 checkpoint:** `664ed94f6f1ea54320ed1725b5c0f1643cf01e50`

## Executive conclusion

AIRE Prime v0.1 is an evidence-gated simulated research framework with two reproducible
experiments. E1 supports a bounded claim of simulated capability transfer. E2 is a reproducible
negative/undetermined result: discovery and transfer subtests pass, but absent host peak-RSS and
elapsed-time observations prevent matched-resource and held-out-gain gates from passing.

The strongest current evidence states are:

| Experiment | Classification | Occurrence | Grounding | Scientific gate state |
| --- | --- | --- | --- | --- |
| E1, seed 101 | `simulated-capability-transfer` | O4 | G-S | All declared E1 gates pass |
| E2, seed 202 | `simulated-alien-sense-transfer-not-established` | O0 | G-S | `heldout-gain` and `matched-controls` fail |

Occurrence and grounding are independent axes. O4 means independently transferred within the
declared protocol; G-S means simulated. Neither axis upgrades the other.

## What E1 supports

E1 shows that, in its deterministic procedural world, a fresh contained receiver can use a
hidden-test-free generative-constructor packet to reconstruct, adapt, compose, and repair a
capability under changed resources. The candidate and five precommitted executable alternatives
receive the same three task requests and equal packet-byte, interaction, and transmitted-input-byte
budgets. Independent hidden validation accepts the candidate and rejects the alternatives.

This supports the protocol-level classification `simulated-capability-transfer`, O4/G-S. It is not
evidence of general intelligence, physical augmentation, autonomous external action, or behavior
outside the frozen E1 world and validator.

### E1 baselines

All five alternatives are padded to the candidate packet byte count and executed through the same
contained receiver schedule:

1. `fixed-instance`;
2. `demonstration-list`;
3. `lookup-policy`;
4. `random-opaque-packet`;
5. `conventional-feature-schema`.

The packet excludes downstream task labels and withheld conformance tests. Passing E1 therefore
depends on transferred executable structure, not on a disclosed answer key in the wire packet.

## What E2 supports

E2 shows deterministic infrastructure for contained discovery, transfer to a fresh recipient,
hidden and transformed evaluation, causal versus sham interventions, distinct-seed reproduction,
precommitted executable baselines, complete wire-artifact lineage, and fail-undetermined resource
accounting.

Those successful subtests do not establish the named transfer result. Peak resident bytes and
elapsed time are not credibly observed on the current containment backend. They remain typed
`undetermined` values, never zero. Resource comparison and the improvement decision are therefore
`undetermined`; no provisional improvement is established. E2 stays O0/G-S with two failed gates.

### E2 baselines and interventions

The three 4,096-byte executable baselines are:

1. `frozen-lookup-policy`, a fixed-action prior;
2. `bandwidth-matched-opaque-tensor`, an opaque first-byte-parity control;
3. `conventional-feature-schema`, a raw-observation lookup.

The candidate constructor has a causal output lookup and an inert executable lookup. The targeted
ablation changes the causal lookup. Three equal-size sham interventions change only the known
inert lookup:

1. `random-subspace`;
2. `activation-permutation`;
3. `representation-replacement`.

Every candidate, reproduction, baseline, and ablation request/response pair is retained and
content-addressed. The Measurement Layer Zero decision binds the exact candidate/control arms,
measurement artifact IDs, protected floors, comparison IDs, and deterministic bootstrap samples.

## Resource accounting

Measurement Layer Zero tracks eight dimensions: packet bytes, peak resident bytes, operation
count, interaction count, elapsed time, external calls, declared energy proxy, and declared
bandwidth. Observation access and receiver prior identity are additional hard comparison
boundaries. Only resource dimensions may receive a bounded predeclared adjustment; hidden access
or a different receiver prior cannot be adjusted away.

For current E2 evidence, packet bytes, operation count, interaction count, external calls,
declared energy proxy, and declared bandwidth are observed protocol counts. Peak resident bytes
and elapsed time are undetermined. This is the reason `matched-controls` and `heldout-gain` remain
failed, not an incidental reporting limitation.

## Adversarial evidence

The Task 12 suite exercises these named attacks:

| Attack | Expected boundary |
| --- | --- |
| Source string in an untrusted packet field | Registered `ProtocolViolation` ingress rejection |
| Executable pickle reduce payload | Registered `ProtocolViolation`; sentinel remains absent |
| Path traversal in an untrusted packet field | Registered `ProtocolViolation` ingress rejection |
| Subprocess request in an untrusted packet field | Registered `ProtocolViolation` ingress rejection |
| Oversized tensor | `ResourceInfeasible` receipt |
| Recursive operation reference | `ConstructorFailure` receipt |
| Hidden environment request | Registered `ProtocolViolation` ingress rejection |
| Oversized wire packet | Registered `ExcessInput` ingress rejection |
| Content-ID mismatch | Registered `ProtocolViolation` ingress rejection |

The production audited ingress hashes untrusted bytes without retaining them, converts parser,
size, response-kind, request-link, role, and undeclared-file-access failures to typed rejections,
and appends the exact rejection object to the registry. Failure detail identity depends only on
the typed code; the separate wire hash preserves provenance without becoming a scored
child-controlled channel. The production audited realizer appends its exact typed receipt. Tests
reparse those stored typed
objects and verify their hash chains and request-wire or realization lineage. Existing containment
integration also tests undeclared file content and metadata reads,
writes, loopback/local/routed network access, fork, descriptor exhaustion, executable and artifact
replacement, path-type swaps, timeouts, output bounds, and process-group cleanup.

Metric-gaming fixtures cover random-output novelty, all-state empowerment, difficult-case refusal,
and undeclared-prior packet efficiency. Protected-dimension regressions produce a rejected
decision. Observation-access or receiver-prior mismatches produce an undetermined decision through
an invalid frozen comparison and cannot be declared-adjusted.

## Unsupported claims

No v0.1 result supports any of the following:

- physical grounding, physical replication, or a newly discovered physical sense;
- Q12D geometry, quantum error-correction improvement, or a resource advantage for QEC;
- superintelligence, general intelligence, consciousness, or sentience;
- new physics;
- production safety, deployment readiness, unrestricted model execution, or autonomous external
  action; or
- performance beyond the exact seeds, worlds, contracts, validity regions, controls, and host
  boundary stated here.

The Q12D/QEC work is E5 and is absent from v0.1. The recovered Q12D source baseline is preservation
evidence only; it is not experimental support for AIRE.

## Limitations and untested threats

- The Task 7 containment claim is limited to macOS 27 arm64 after a functional Seatbelt probe.
  Other platforms and versions fail closed.
- Apple `system.sb` is private, patch-mutable platform TCB and retains selected runtime and Mach/XPC
  authorities.
- The threat model excludes root, kernel compromise, a compromised trusted parent/configuration,
  and a concurrent hostile same-UID process racing pathname allowances after final verification.
- The current portable launcher does not independently verify an address-space limit. CPU/wall,
  output/file-size, fork, descriptor, path, and network limits remain enforced.
- Host peak-RSS and elapsed-time evidence is not reproducibly observed, which holds E2 at O0/G-S.
- The adversarial fixtures are bounded examples, not a proof that no covert channel or metric
  exploit exists.
- No live provider, physical apparatus, production deployment, or external-action authority is in
  scope.

## Reproduction

From a clean checkout of the feature branch:

```bash
uv sync --frozen
uv run aire-prime schema check
uv run aire-prime e1 run --seed 101 --output /tmp/aire-prime-e1
uv run aire-prime e2 run --seed 202 --output /tmp/aire-prime-e2
uv run aire-prime registry verify /tmp/aire-prime-e1/registry.jsonl
uv run aire-prime registry verify /tmp/aire-prime-e2/registry.jsonl
uv run aire-prime report show /tmp/aire-prime-e1
uv run aire-prime report show /tmp/aire-prime-e2
uv run ruff check .
uv run mypy
uv run pytest --cov=aire_prime --cov-report=term-missing --cov-fail-under=90
uv run python scripts/export_schemas.py --check
git diff --check
```

The final Task 11 reproduction produced:

- E1 report ID
  `sha256:b709fbf42e25d2a8db6e4244472b739503e2d4fb458967bcc2080ddbf3348813`
  and registry head
  `sha256:f2ee52c431986a2761bfd7dea17df16e2c75c7ca132d7d5596b10eb5f8a912b5`;
- E2 report ID
  `sha256:3f60ac64e2190fbdd0705e8ef6bad7e8a701e9a42087a82a32d1afeb695a81bc`
  and registry head
  `sha256:026454dd53f2fd1c6363b7ad4213f0fcf5a0ba2257aa73e9619aa68542d4c314`.

Canonical report IDs are the scientific payload identities. Registry heads also cover the ordered
event history and therefore change when newly required evidence objects are added to the manifest.

## Deferred work

- **E3:** physically grounded augmentation, requiring new safety, authorization, and replication
  gates.
- **E4:** recursive discovery, requiring bounded recursion and stronger independence/contamination
  controls.
- **E5:** the Q12D/QEC bridge, beginning at simulator grounding and requiring full qubit-round,
  latency, energy, memory, bandwidth, and physical-replication accounting before stronger claims.

None of E3--E5 is implemented or authorized by v0.1.
