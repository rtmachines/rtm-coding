# Targeted async and synchronization validation

Required when the reviewed change affects lock acquisition/progress, cancellation,
queue/permit ownership, task termination or a shared-state synchronization protocol.
Determine scope from affected callers and invariants, not just new async/atomic tokens.
Routine async syntax or unchanged runtime internals do not themselves require a Loom
model. Assess async execution and custom synchronization separately in the report.

## Async behavior: exercise the transitions

Map the affected paths to locks held, await points, ownership of queued items/permits,
spawned tasks, and externally visible effects. Establish the contract before testing:
what must complete, what cancellation may discard, and what must have stopped on return.

For applicable behaviors require named targeted tests:

- **Deadlocks/progress:** exercise nested/reentrant acquisition, competing lock order
  and callbacks while guards are live. Use channels/barriers or controlled polling to
  reach the contested state. Bound the test and the process. An executor timer cannot
  rescue a thread blocked by a synchronous lock: use an external watchdog for that case.
  A slow or killed test alone does not prove deadlock. Show the reached state and wait
  cycle; distinguish setup/time-limit failures from a demonstrated progress violation.
- **Cancellation:** suspend at relevant await/select boundaries before and after state
  mutation; drop/abort the future and inspect queue contents, permits, resources and
  partial effects. Exercise channel closure and partial I/O where the contract requires
  it. Happy-path completion is not cancellation evidence. Do not rely on arbitrary sleeps
  to make the cancellation window occur; explicit polling/handshakes are preferable.
- **Task lifecycle:** distinguish dropping a handle, requesting abort and observing
  termination. Verify the absence of prohibited effects after stop/shutdown returns,
  including destructor completion when required. Use a worker held at a known boundary
  and a controlled subsequent signal/effect. Account for running spawn_blocking jobs
  and cooperative shutdown: abort alone is not a completion barrier.

Run on the runtime/configuration relevant to the contract. State current-thread vs
multi-thread, clock configuration, scheduling controls, deadlines, commands, test
names/counts, logs and source hashes. Test only applicable behaviors; N/A needs a reason.
Missing or unrelated tests are NOT RUN, never PASS for these checks.

## Synchronization: require Loom and a separate argument

For a changed custom shared-state synchronization protocol (atomic publication,
lock-free algorithms, or inter-thread lock/notification protocols), require a targeted
Loom model and an independent ordering/invariant argument. Tokio task scheduling and
cancellation tests above do not substitute for Loom; Loom does not model all Tokio or
OS behavior either. Pure task lifecycle code without a custom inter-thread protocol
may mark sync-scope NONE, while still requiring async tests.

Prefer the exact reviewed implementation with cfg-selected Loom primitives. Confirm
that the exercised types really are Loom's tracked atomics/locks/Arc/thread; a model
that still uses std atomics for the relevant state cannot validate the protocol.
When direct instrumentation is unavailable, an isolated adaptation may substitute only
concurrency primitives and scheduling hooks. Preserve operations, ordering modes,
control flow and assertions; record the diff/mapping and source hashes. A separately
rewritten similar algorithm is not evidence. If the mapping cannot preserve the relevant
behavior, report the gap and ESCALATE rather than weakening the claim or the model.

Model meaningful competing actions and assert the actual contract, not merely that
threads finish. Include relevant publication/read, notification/wakeup, failed CAS,
reuse or reclamation paths as applicable. Respect documented caller preconditions;
do not invent multiple writers when the contract is explicitly one-shot/single-writer.
A passing model must be non-vacuous: identify operations/interleavings it explores.

Record Loom and dependency versions, cfg/features, thread/operation counts, preemption
bounds, branch/permutation/time limits, completion and logs. A bounded completed model
supports only its stated bounds and assumptions; it is not a proof of all executions.
A truncated, timed-out, unsupported or zero-test model is NOT RUN for approval. Provide
a synchronization argument identifying the invariant, atomic modification/orderings,
release/acquire or lock handoff, linearization/progress obligations where relevant.
Do not report Relaxed as inherently wrong: independent telemetry may need atomicity
only. A model counterexample must obey the real API contract and correspond to source.

## Isolated probes, verdicts and limits

Use existing adequate tests/models first. When execution is authorized and coverage
is absent, create bounded probes outside the reviewed repository using exact source
copies/imports. Do not repair the implementation or alter Git/source/configuration.
Record harness changes and verify source hashes. Do not install tools or dependencies
outside session authorization. Use exact-version dependency contracts when needed.

Missing applicable async evidence, unavailable/incomplete Loom or an unresolved
synchronization argument requires ESCALATE, not APPROVE or a fabricated P1. A verified
counterexample is FAIL and supports REQUEST_CHANGES. If both proved blockers and
unresolved risks remain, use ESCALATE and list the proved defects too. NONE/N/A needs
a scope-based explanation. Existing memory-validation obligations still apply whenever
the concurrent code changes unsafe/FFI invariants; Loom does not replace Miri.

Proposed concurrency fixes remain candidates until tested. Where practical, use a
known-good control or check that the regression fails before and passes after a fix,
without changing the reviewed tree. Do not count an invalid harness or resource timeout
as successful defect detection. Report scope limitations explicitly.

References: [Loom](https://docs.rs/loom/),
[Tokio task cancellation](https://docs.rs/tokio/latest/tokio/task/index.html#cancellation),
[atomic ordering](https://doc.rust-lang.org/std/sync/atomic/enum.Ordering.html).
