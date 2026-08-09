# AIRE Prime Decisions

## D-001: Preserve the original goal boundary

**Decision:** Do not relabel the current trusted-command adapter as an OS sandbox and do not weaken
the `GOAL_NEXT_TASKS_GROUP.md` completion contract.

**Reason:** Command attestation, resource limits, minimal environment, bounded pipes, and typed
packets do not prevent filesystem or network syscalls by the approved child.

**Consequence:** The Tasks 5--7 goal remains blocked and Task 8 must not start.

## D-002: Keep scored protocol bytes reference-only

**Decision:** Wire-level failure detail IDs are derived only from the typed failure code. Raw
messages and bounded counterexamples are retained in local `FailureDiagnostic` sidecars and never
serialized into scored response bytes.

**Reason:** Hashing child-controlled narratives into a wire content ID would retain a covert output
channel even though the narrative text was removed.

## D-003: Bind every absolute command artifact

**Decision:** Every absolute file argument must have exactly one attestation containing its
canonical resolved path, SHA-256 digest, device, inode, and size. Execution uses resolved paths.

**Reason:** Executable-only attestation allowed an absolute script to change after approval.

**Residual:** Verification still precedes execution; it is not FD-pinned against a concurrent
same-user path swap.

## D-004: Recovery before continuation

**Decision:** Push the four local-only commits before replaying crash-time patches and use a durable
linked worktree rather than `/private/tmp`.

**Reason:** The outage deleted the temporary checkout while Git refs and Codex transcript patches
survived.

## D-005: Use one gated remaining-steps master goal

**Decision:** Use `GOAL_REMAINING_STEPS.md` as the approved autonomous completion contract. It
preserves Q12D in a distinct repository, closes Task 7 before starting experiments, and then runs
Tasks 8--12 with commit-and-push checkpoints after every completed phase.

**Reason:** One durable state machine minimizes crash-time handoff loss while hard phase gates keep
Q12D, security remediation, simulated experiments, and release evidence from being conflated.

**Consequence:** D-001 remains binding until Task 7 has reviewed negative containment proof. The
master goal does not authorize merging, deployment, physical work, E3--E5, destructive cleanup, or
placing the legacy Q12D sources in AIRE history.

## D-006: Preserve Q12D in the existing Q12Dgates remote

**Decision:** Use the user-selected existing public repository
`https://github.com/deesatzed/Q12Dgates.git` as the distinct recovery remote for the Q12D baseline.

**Reason:** The repository existed with the requested ownership and visibility but contained no
branches or tags, so pushing the verified recovery root could not overwrite prior project history.

**Consequence:** Q12D remains independent from AIRE Prime. Its recovery baseline is commit
`cbd14aa8d08f1ea73469353a1cf4722b572df82c`; later Q12D work must use that repository and must not
be folded into the AIRE feature branch.

## D-007: Declare a narrow fail-closed containment platform

**Decision:** Task 7 production subprocess execution is supported only on macOS 27 arm64 when a
functional `/usr/bin/sandbox-exec` probe applies the reviewed profile. Every other host returns
typed `ContainmentUnavailable` evidence without executing the configured child.

**Reason:** Seatbelt and its private `system.sb` dependency are platform- and version-sensitive.
Existence and ownership checks alone do not prove that containment can be applied.

**Consequence:** The platform TCB includes the sealed system executables, the reviewed shell
resource launcher, Seatbelt, and imported standard system runtime/Mach authorities. The profile
explicitly re-denies sensitive password files, core writes, network operations, and forks.

## D-008: Make command artifacts immutable and literals explicit

**Decision:** Absolute artifacts execute from verified, read-only, unlinked snapshots. Every
nonabsolute argv token must be explicitly classified as a bounded opaque literal; path-shaped
literals are rejected. Secondary execution is limited to the reviewed shell launcher variants and
the attested executable.

**Reason:** Path/digest checks followed by normal path execution, relative arguments, embedded
option paths, writable snapshot descriptors, and unrestricted `process-exec` each left a way for
approved bytes to change or for the child to replace the approved command boundary.

## D-009: Scope pathname containment to a trusted parent

**Decision:** The Task 7 threat model protects against the approved hostile child after launch. It
does not claim protection from root, the kernel, a compromised parent/configuration, or a
concurrent same-UID host process racing pathname allowances before `Popen`.

**Reason:** macOS Seatbelt grants directory capabilities by pathname, not by an atomically pinned
directory descriptor. Artifact bytes can be snapshotted; directory-subtree authority cannot be
made equivalent with this backend.

**Consequence:** Allowance path/type/device/inode changes before preparation fail closed, and
artifact races are closed. Stronger same-UID concurrency protection and a native memory-limiting
launcher remain future hardening, not claims of this v0.1 boundary.

## D-010: Separate E1 capability transfer, task disclosure, and hidden validation

**Decision:** Freeze and content-address the E1 capability packet without downstream task labels or
hidden conformance details. Bind five byte-matched baseline packet commitments into the Evaluation
Contract before observation, then give the proposal and every baseline the same three separately
committed task requests through the Task 7 contained receiver. Treat GRC realization receipts as
kernel-smoke evidence, not as proof of the returned constructions.

**Reason:** A preprogrammed recipient, post-observation control selection, leaked validator details,
or unequal interaction/bandwidth schedules would make the simulated transfer classification
scientifically unsupported even if deterministic tests passed.

**Consequence:** E1 may report simulated capability transfer only when contained response artifact
IDs pass independent hidden validation and every matched alternative fails under identical declared
input-byte and interaction budgets. Failed gates downgrade the classification and remain in the
canonical evidence.

## D-011: Make Measurement Layer Zero contract-bound and fail-undetermined

**Decision:** A provisional improvement decision must bind candidate measurements to the exact
matched candidate arm, precommit the complete control-arm set, precommit protected dimensions and
floors, recompute every resource comparison from frozen arms, and retain the full deterministic
bootstrap distribution. Missing or inconsistent evidence yields `undetermined`, never zero or
implicit success.

**Reason:** Typed resource fields alone do not prevent comparison-status forgery, favorable-only
control selection, swapped proposal samples, omitted safety dimensions, or post-hoc adjustment of
resource mismatches.

**Consequence:** Callers must supply exact control and protected contracts plus content-addressed
candidate/control measurement evidence. Adjustments are bounded, structured, content-addressed,
and limited to resource dimensions; observation access and receiver priors remain hard matching
boundaries.
