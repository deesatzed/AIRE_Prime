# AIRE Prime Next Tasks Group Goal

This goal covers Tasks 5--7 only. It completes the safe execution and evidence substrate required
before E1/E2 experimentation. It does not authorize Tasks 8--12.

```text
/goal
OUTCOME: Complete AIRE Prime implementation Tasks 5, 6, and 7 so that bounded Generative Reality
Objects can be realized through an allow-listed interpreter, every lifecycle/evidence event is
append-only and tamper-evident, and proposer/receiver/validator/adversary/authorizer roles exchange
typed packets through an isolated protocol. The resulting branch must remain deterministic,
sandboxed, offline, and ready for E1 implementation without beginning E1.

PROOF OF DONE:
1. Task 5 bounded realization:
   - `uv run pytest tests/exchange -v` exits 0.
   - The only executable primitives are identity, constant, select, affine, concat, normalize,
     threshold, and lookup.
   - Tests prove that source strings, callables, imports, paths, URLs, shell commands, pickle-like
     payloads, recursive references, undeclared dependencies, non-finite tensors, structural type
     mismatches, and oversized lookup tables cannot execute.
   - Operation-count, element-count, output-byte, and elapsed-time limits produce typed
     `ResourceInfeasible` evidence before an unsafe operation proceeds.
   - Successful and failed realizations both emit serializable receipts containing object,
     receiver, local realization, contract-test, resource, deviation, and failure fields.

2. Task 6 append-only registry:
   - `uv run pytest tests/registry -v` exits 0.
   - The explicit transition table accepts the documented lifecycle and rejects invalid terminal
     reversals such as Rejected -> Provisional.
   - Supersession creates a new object identity and retains the prior record and failure evidence.
   - Every JSONL event includes sequence, timestamp, actor role/ID, object ID, event type, previous
     event hash, payload content ID, and event content ID.
   - Corrupting any prior line, reordering events, breaking the hash chain, or reusing an object ID
     for different bytes makes verification fail.
   - The registry exposes append and verify operations only; it provides no update or delete path.

3. Task 7 isolated roles and protocol:
   - `uv run pytest tests/agents -v` exits 0.
   - A single identity cannot act as proposer, final validator, and authorizer for the same claim.
   - Validator requests cannot contain proposer-only or hidden-context fields.
   - Request/response JSONL accepts only declared message kinds and canonical object references.
   - The subprocess adapter uses an argument array, `shell=False`, a timeout, explicit working
     directory, minimal environment allowlist, bounded captured output, and JSONL stdin/stdout.
   - Timeout, malformed JSON, excess output, nonzero exit, role conflict, and undeclared file-access
     requests return typed evidence rather than unclassified exceptions.

4. Cross-task verification:
   - `uv run pytest -q` exits 0 with no weakened, skipped, or deleted pre-existing tests.
   - `uv run ruff check .` exits 0.
   - `uv run mypy` exits 0 under the existing strict configuration.
   - `uv run python scripts/export_schemas.py --check` exits 0.
   - `git diff --check` is clean.
   - `git status --short --branch` shows only intentional AIRE Prime Task 5--7 changes.
   - Each task has a specification-compliance review followed by a code-quality/security review;
     every Critical or Important finding is fixed and re-reviewed before the next task begins.

5. Evidence handoff:
   - Update `docs/AIRE_V0_1_STATUS_AND_ROADMAP.md` with verified Task 5--7 results, exact commands,
     test counts, commit IDs, remaining limitations, and the explicit statement that E1/E2 have not
     yet been demonstrated.
   - Provide a final changed-file and commit summary with evidence for every proof item.

SCOPE:
- Implement Task 5 only in:
  `aire_prime/grc/operations.py`, `aire_prime/grc/constructor.py`,
  `aire_prime/exchange/`, and `tests/exchange/`.
- Implement Task 6 only in `aire_prime/registry/` and `tests/registry/`.
- Implement Task 7 only in `aire_prime/agents/` and `tests/agents/`.
- Modify shared core/object/schema files only when a Task 5--7 proof cannot be satisfied otherwise;
  add a regression test and document the reason for every such modification.
- Read and obey `docs/plans/2026-08-03-aire-prime-design.md` and Tasks 5--7 in
  `docs/plans/2026-08-03-aire-prime-v0.1-implementation.md`.
- Do not modify or add the legacy `Q12D.md`, Angular `src/`, or
  `Quantum Maze Teaching Model Plan/` content.
- Do not begin `aire_prime/experiments/`, Measurement Layer Zero, E1, E2, CLI, or release work.

CONSTRAINTS:
- Follow test-driven development: observe the required focused test failure before implementation,
  then retain red/green evidence.
- Use canonical immutable packet models and tuple-based fields; do not weaken content identity,
  grounding, wire-ID, evidence, or role-independence checks from Tasks 1--4.
- Never execute packet-provided code or treat a packet string as a module, path, URL, command,
  pickle, callable, or environment request.
- No cloud providers, model credentials, network calls, unrestricted subprocesses, physical device
  control, production deployment, or autonomous external action.
- Do not add dependencies unless the standard library, NumPy, and existing Pydantic stack cannot
  satisfy a required proof; document and independently review any dependency addition first.
- Do not remove, relax, xfail, or skip a test to obtain a pass.
- Keep failures and `undetermined` outcomes visible; do not silently coerce them to success or zero.
- Preserve occurrence and grounding as separate categorical axes. Tasks 5--7 unlock no occurrence
  or physical-grounding claim.
- Make one focused commit per task using the implementation-plan commit subjects.

SAFETY / PROVENANCE:
- Treat every GRO and agent message as hostile input until schema, identity, permission, dependency,
  structural-type, validity, and resource checks pass.
- Receipts and registry events are evidence artifacts; preserve exact failure types, smallest known
  counterexamples, measured resources, actor identity, and lineage.
- The proposer must not control hidden validation, final evidence classification, or authorization.
- Do not describe a passing Task 5--7 test as alien-sense transfer, intelligence improvement,
  superintelligence, QEC improvement, physical validation, an Einstein 12D manifold, or new physics.
- Useful ideas outside this group must be recorded as deferred rather than partially implemented.

ITERATION:
- Before each task, inspect the current branch, relevant plan section, and nearest existing models.
- Execute strictly in order: Task 5 -> independent reviews -> Task 6 -> independent reviews ->
  Task 7 -> independent reviews -> full cross-task verification.
- Work in small test-first batches and run the nearest focused suite after each batch.
- On a failing check, identify the root cause, add or preserve a regression, and repair it before
  expanding scope.
- Preserve user changes and unrelated dirty files. Never clean or rewrite work outside the listed
  scope.
- Record exact commands, exit status, test counts, commits, accepted/rejected review findings, and
  remaining risks in the final evidence handoff.

STOP:
- Stop before Task 8 even if Tasks 5--7 finish early.
- Pause and report if credentials, network access, production deployment, physical access, or a new
  product/scientific decision becomes necessary.
- Stop if safe completion would require arbitrary packet code execution, weakened isolation,
  mutable evidence history, hidden resource accounting, or relaxed grounding boundaries.
- After three distinct failed repair approaches for the same blocker, preserve command/error
  evidence and report the blocker without claiming completion.
- Stop if the implementation root or branch no longer matches `feature/aire-v0.1`, or if completing
  the goal would require committing unrelated legacy files.

COMPLETE:
Mark this goal complete only when every Task 5--7 proof above passes using fresh command output,
all Critical and Important independent-review findings are resolved and re-reviewed, the status
roadmap contains the verified evidence handoff, and no Task 8--12 implementation has begun. Passing
this goal means only that AIRE has a bounded realization, append-only evidence, and isolated-role
substrate ready for E1; it does not mean that E1, E2, alien-sense transfer, QEC improvement,
superintelligence, or new physics has been demonstrated.
```

## Assumptions

- “Next tasks group” means Tasks 5--7 because they are the remaining substrate dependencies before
  the experimental Tasks 8--10.
- Work continues on `feature/aire-v0.1` or a dedicated worktree created from that branch.
- The current 45-test Tasks 1--4 baseline remains the non-regression floor.
