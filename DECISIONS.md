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
