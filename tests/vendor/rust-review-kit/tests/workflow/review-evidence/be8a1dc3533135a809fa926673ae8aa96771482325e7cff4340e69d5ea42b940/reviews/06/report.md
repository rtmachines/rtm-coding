## Verdict: APPROVE
No actionable defects found in the requested branch-plus-local scope. Required ordinary gates, targeted memory validation, async transition checks and completed Loom exploration pass, with independent ownership and ordering arguments below.

## Gates
- fmt: PASS (`fmt.log`, exit 0).
- clippy: PASS (`clippy.log`, exit 0; RUST_REVIEWDOG=1, raw diagnostics retained, reviewdog exit 0).
- tests: PASS (`tests.log`, default features, offline/locked).
- doctests: PASS (`doctests.log`, zero doctests; explicitly executed).
- deny: PASS (`deny-offline.log`, offline/locked; cached advisories, unmatched BSD-3-Clause allowance warning only).

## Memory safety
- memory-scope: REQUIRED (`src/registration.rs` transfers and reclaims a buffer retained by an FFI consumer; `src/bytes.rs` is also checked for input bounds/alignment).
- miri: PASS (three targeted isolated tests, default Stacked Borrows, zero failures).
- aliasing: PASS (one raw allocation owner until synchronous unregister; no Box/reference reconstitution while foreign reads can occur).
- memory-evidence: `probe/src/*.rs` are byte-identical reviewed implementations; `probe-hashes.json` records them and the harness. `memory_probe.rs` tests `reads_after_owner_move_and_during_unregister`, `empty_registration`, and `byte_alignment_and_bounds`. They cover retained reads after constructor return/owner move, len/is_empty, reads during unregister, empty ownership, short slices and four byte offsets. `miri-stacked.log`: three passed under Miri 0.1.0 (48f4b05538, 2026-10-23), nightly toolchain, MIRIFLAGS unset, offline/locked, 120-second external watchdog; command in `commands.txt`.
- aliasing-evidence: Box::into_raw transfers the original boxed-slice allocation and metadata at registration.rs:21. The callback receives the original allocation pointer and length at line 24. Moving Registration or borrowing it for len/is_empty accesses only its pointer/length fields, never reborrows the pointee. The API's explicit unsafe preconditions forbid writes/free/replacement, require serialization, and require unregister to stop reads synchronously. Drop invokes unregister at line 41 before Box::from_raw at line 44 reconstructs and frees the allocation once with the original metadata/allocator. Empty slices are valid but have no readable bytes. The shim complies with these caller obligations; arbitrary native libraries are not validated. read_word obtains a checked four-byte slice, copies into an aligned array, then uses safe from_ne_bytes; no unaligned dereference occurs.

## Concurrency
- async-scope: REQUIRED (`Service::increment_and_snapshot`, approved_pop, stop_worker).
- deadlocks: PASS (existing `nested_lock_completes`, plus `later_snapshot_progress` exercising repeated increments and later snapshots).
- cancellation: PASS (existing explicit-poll `cancel_before_approval_preserves_item`, plus `closed_approval_preserves_queue` and explicit-poll `cancel_waiting_on_queue_preserves_queue`).
- task-lifecycle: PASS (existing handshaked `stopped_worker_cannot_receive_more_work`, plus `stop_waits_for_destructor`).
- async-evidence: `tests.log` contains three existing targeted Tokio tests; `async-probe.log` contains four extra tests in exact-source `probe/tests/async_probe.rs`. Tokio 1.54.1 current-thread runtime; direct Poll::Pending fixes cancellation boundaries, oneshot channels fix worker start/release, destructor flag verifies cleanup before stop returns. Progress checks use 100ms existing/1s probe timer bounds; processes use 180s ordinary/120s probe external watchdogs. All pass. The lock guard drops before snapshot re-acquires; approval is received before queue mutation; queue mutation has no suspension afterward; stop aborts then awaits the handle, observing completion rather than only requesting cancellation. Already-running blocking work may delay completion, but awaiting its handle prevents return before its completion; no bounded stop latency is promised.
- sync-scope: REQUIRED (`Published` one-shot publication).
- loom: PASS (`publication_is_coherent`, one model test completed, exit 0).
- synchronization: PASS (Release ready store synchronizes with an Acquire load observing true; the prior relaxed value store happens-before the later value load. Exactly one publish prevents overwrite/reuse ambiguity).
- model-evidence: `tests/publication.rs` executes the exact implementation with feature model selecting Loom 0.7.2 AtomicUsize/AtomicBool; Arc and writer thread are tracked Loom primitives. Two threads, one publish and one concurrent snapshot, assert every observed Some equals 42; writer joins. No LOOM_* overrides. Builder defaults: max_threads=5, max_branches=1000, no preemption/permutation/duration cap or checkpoint replay. External timeout 120s not reached; `model.log` records successful completed model execution. This covers the stated single-writer one-shot protocol, not multiple writers or reuse. Source hashes and command are preserved.

## Spec
- spec: PASS (`REQUIREMENTS.md`, all six adapters/contracts checked separately).
- missing: None identified: short/unaligned reads, retained ownership through unregister, progress, preapproval cancellation, owned-worker termination and coherent one-shot publication all supported by source and targeted execution.
- unrequested: No additional externally visible runtime scope identified.
- contradictions: None identified; ordinary tests avoid UB and use bounded progress checks.

## Findings
No findings.

## Residual risks
- Scope: base 65df47294846eb2e2d435a952baf6d7bfeba1851 (origin/main), head a8193bd3c5cd66bd93f14e7c58d57f480610ce4e. Clean working tree; no nonignored untracked files at inventory. Branch plus local scope included source, tests, policy and helper changes; `context.log` and `diff.log` preserve scope.
- Unsafe constructor preconditions must be met by foreign consumers. Model evidence is for the specified one-shot protocol and bounded state space. stop_worker owns one task handle; detached descendant tasks and bounded stop latency are not promised by this implementation or tested as such.
- Semver: N/A under project policy (unpublished package).
- All commands, statuses and logs are in this report's directory (`commands.txt`, `status.json`, `*.command`, `*.log`). Stable Rust 1.99.1, edition 2024; no MSRV declared. Exact tool versions are in `toolchain.log`. Source hashes before/after are identical (`before-hashes.json`, `after-hashes.json`, `source-unchanged.txt`). Graph navigation and Rust LSP symbol evidence are recorded in `navigation.json` and `tests-graph.json`; source and tests were read independently because graph coverage is incomplete. All work was offline; advisory freshness and availability of uncached dependencies were not refreshed. No reviewed source was edited. Initial cargo-deny invocation used an unsupported flag (exit 2); the corrected offline invocation passed, and both logs remain. No external comments, push or publication occurred.
