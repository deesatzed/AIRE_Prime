# AIRE Prime Task 7 Recovery Review

## Review Scope

Security, correctness, test, and claim review of commit `babd013` against Task 7 in the
implementation plan and `GOAL_NEXT_TASKS_GROUP.md`. The reviewed change is limited to
`aire_prime/agents/` and `tests/agents/`.

## Summary Judgment

**Blocked for the Tasks 5--7 completion claim.** The typed protocol and trusted-command boundary
are substantially hardened and all automated checks pass, but `SubprocessAdapter` is not an OS
sandbox. An approved child can still read or write files available to the host user and initiate
network access. Task 8 must not begin while the governing goal still requires a sandboxed, offline
substrate.

## Findings

| Severity | Category | Finding | Why It Matters | Required Fix |
| --- | --- | --- | --- | --- |
| Critical | Security boundary | `SubprocessAdapter` attests a fixed command, limits descendants, constrains environment and captures output, but does not restrict the command's filesystem or network syscalls. | A trusted executable or script can perform host side effects or exfiltrate data even when its stdout is rejected. This does not satisfy the goal's sandboxed/offline claim. | Add a fail-closed OS containment backend with tested filesystem and network denial, or obtain an explicit scope decision changing the governing goal. |
| Important | TOCTOU | Artifact digest, canonical path, device, inode, and size are verified before `Popen`, but execution is not pinned to the verified open file descriptor. | A concurrent same-user host process with directory write access can still swap an artifact in the verify-to-exec window. | Execute from pinned descriptors or an immutable artifact store, or explicitly exclude concurrent local-host mutation from the threat model and obtain review acceptance. |
| Important | Reliability and portability | Child limits use `preexec_fn` and POSIX `resource`/process-group APIs. | `preexec_fn` is unsafe in a multithreaded parent and the adapter is not portable to non-POSIX hosts. | Move limits into a minimal exec wrapper before agent code and document/test supported platforms. |
| Resolved | Wire covert channel | The recovered patch originally hashed raw child-controlled diagnostics into `detail_content_id`. | A hostile child could influence scored wire bytes through an opaque hash. | Resolved: wire detail IDs now depend only on typed failure codes; bounded narrative diagnostics remain local-only. |
| Resolved | Incomplete attestation | Direct `TrustedCommand` construction could omit an absolute script artifact. | The unbound script could change after command approval. | Resolved: artifacts must exactly match every absolute file argument and bind digest, canonical path, device, inode, and size. |
| Resolved | Role identity | `AgentResponse` allowed identical sender and receiver IDs. | It weakened protocol-level role separation. | Resolved: request and response endpoints must be independent identities. |

## Correctness

The focused agent suite covers canonical request/response exchange, role conflicts, fixed command
attestation, changed artifacts, timeout, aggregate output bounds, malformed output, no-fork child
limits, deterministic failure references, and local bounded diagnostics. The current suite is
green.

## Security and Privacy

Accepted mitigations include reference-only wire packets, canonical machine identifiers, complete
absolute-file attestation, resolved execution paths, device/inode/size checks, minimal environment,
explicit `close_fds=True`, child core/process limits, process-group termination, and local-only
bounded narratives.

Claude's bounded second-opinion review identified the verify-to-exec race, writable-path risk, and
the need to confirm environment/descriptor isolation. Codex classified inode/path binding and
explicit descriptor closure as Accepted and implemented them; the inherited-environment concern
was Rejected because the child receives a newly constructed allowlisted environment; full FD-pinned
execution remains Needs Investigation. Re-review attempts produced no additional Claude output, so
no automated second opinion is being represented as a pass.

## Tests

- Focused RED evidence: recovered tests failed because `TrustedCommand` did not exist.
- Recovered GREEN evidence: 31 agent tests passed.
- Security-regression GREEN evidence: 36 agent tests passed.
- Full suite: 168 tests passed.
- Ruff, strict mypy, schema freshness, and `git diff --check`: passed.

## Maintainability

The trusted-computing-base boundary is explicit in the class documentation. The remaining platform
containment work should be isolated behind a dedicated backend rather than added as more output
filtering or packet heuristics.

## Performance

Command artifacts are SHA-256 hashed at configuration and before each run. This is intentional for
integrity but scales with artifact size. No unbounded child output is retained.

## UI/UX Impact

None; this repository surface is a Python protocol and research substrate.

## Regression Risk

Changing embedded receipts and failure narratives to content references is a wire-schema change.
No external compatibility guarantee exists yet, but future callers must use `receipt_content_ids`
and local `FailureDiagnostic` records.

## Scope Creep Check

No Task 8--12 experiment, CLI, provider, network integration, physical action, or deployment work
was added.

## Required Fixes Before Done

1. Enforce and test host filesystem and network containment.
2. Close or explicitly accept the remaining verify-to-exec race.
3. Replace or constrain `preexec_fn` for the supported execution environment.
4. Re-run the full security review and all verification gates.

## Optional Improvements

- Add a dedicated immutable artifact cache for verified commands.
- Add platform capability reporting for isolation backends.
- Add tests for adapter reuse and diagnostic reset behavior.
