## Verdict: REQUEST_CHANGES
Targeted Miri, async tests and Loom demonstrate six distinct contract failures. Ordinary tests pass because they avoid these paths; Clippy also fails. These are demonstrated blockers, with no unresolved vendor guarantee needed for the supplied callback contract.

## Gates
- fmt: PASS (fmt.log)
- clippy: FAIL (clippy.log; unnecessary boxed local at src/registration.rs:15, exit 101; reviewdog local presentation also reports it)
- tests: PASS (tests.log; 2 native tests)
- doctests: PASS (doctests.log; 0 examples present)
- deny: PASS (deny-offline.log; existing advisory database, fetching disabled)

## Memory safety
- memory-scope: REQUIRED (src/bytes.rs read_word and src/registration.rs retained buffer)
- miri: FAIL (three targeted tests independently demonstrate unaligned read, out-of-bounds read and use-after-free)
- aliasing: FAIL (read_word lacks alignment/range guarantees; Registration destroys the allocation while its retained pointer is still valid under the callback contract)
- memory-evidence: memory/src/bytes.rs and registration.rs are exact copies, verified in exact-source.json and before-hashes.json. Tests unaligned_word, short_word, retained_until_unregister each executed under cargo +nightly miri test --offline with existing MIRI_SYSROOT=/home/rtm/.cache/miri and empty MIRIFLAGS; three runs each exit 1, logs miri-*.log, commands/status in miri-*-status.json. Nightly rustc/Miri commits are in toolchain.log. Each process bounded to 120 seconds; no UB executed natively.
- aliasing-evidence: read_word receives a live shared byte slice but reads a u32 requiring four accessible bytes and alignment four; neither follows from nonempty slice. Registration creates a raw shared pointer from Box, registers it, stores only length/callback, then implicitly drops Box at constructor return. The callback obeys read-only ownership, serialization and synchronous unregister promises; the pointer is dangling before the moved owner is dropped. The failing Rust C-ABI shim proves this wrapper lifetime violation, not an arbitrary foreign SDK. Fix candidates need their own provenance/move validation.

## Concurrency
- async-scope: REQUIRED (Service lock progress, approved_pop cancellation, stop_worker termination)
- deadlocks: FAIL (increment_progress times out after acquiring count and waiting for snapshot to acquire that same lock)
- cancellation: FAIL (cancel_before_approval manually polls to Pending, drops future and observes empty queue instead of [7])
- task-lifecycle: FAIL (worker_stopped_before_return observes worker effect after stop returns)
- async-evidence: exact-source probe/tests/async_contracts.rs, Tokio 1.54.1 current-thread test runtime, real timer; three tests fail in async.log. Deadlock check uses 50 ms timeout and source-established self-wait cycle; cancellation uses explicit polling, worker uses start/release channels and controlled yields, no timing sleeps. Process watchdog 120 seconds. async-status.json and exact-source.json record invocation/source.
- sync-scope: REQUIRED (Published one-shot publication between writer and reader)
- loom: FAIL (published_value finds Some(0) after publish(42), loom.log)
- synchronization: FAIL (Relaxed ready observation creates no release/acquire synchronization ordering the earlier value store before the reader load)
- model-evidence: Loom 0.7.2; exact publication.rs chooses tracked Loom AtomicBool/AtomicUsize via model feature. probe/tests/publication_model.rs uses tracked Arc and thread, one writer calling publish once, one competing reader and post-join assertion. Default loom::model bounds, no custom preemption/permutation bound; counterexample reached immediately, not timeout. Source and orderings unchanged. Command cargo test --offline --locked --features model --test publication_model; 120 second external watchdog; exit 101 and assertion 0 != 42 in loom.log.

## Spec
- spec: FAIL (REQUIREMENTS.md)
- missing: Correct handling of short/unaligned bytes, retained ownership, increment completion, cancellation preservation, worker termination and publication ordering.
- unrequested: No additional product scope established.
- contradictions: Each of the six requested runtime contracts is violated as detailed below. Ordinary tests themselves remain bounded and avoid UB.

## Findings
- [P1] src/bytes.rs:7 - A safe read accepts insufficient or unaligned storage. Trigger: a one-byte slice or a four-byte slice beginning at an unaligned address. Impact: undefined behavior, demonstrated separately by Miri; nonempty does not imply four readable bytes or u32 alignment. Fix: check at least four bytes and decode a copied [u8; 4] with u32::from_ne_bytes, avoiding the raw read.
- [P1] src/registration.rs:21 - Retain the allocation through unregister. Trigger: a conforming consumer reads its retained pointer after new returns. Impact: bytes is dropped at constructor return because Self stores only its length, causing use-after-free before unregister. Fix: retain a suitable owning allocation until synchronous unregister finishes; validate pointer provenance across owner moves and teardown before claiming the fix sound.
- [P1] src/service.rs:16 - Avoid reacquiring the held count mutex. Trigger: any increment_and_snapshot call. Impact: count guard remains alive while snapshot waits for the same mutex, so the increment never completes. Fix: return the incremented value through the current guard, or release the guard before reacquiring if the weaker snapshot semantics are acceptable.
- [P1] src/service.rs:25 - Wait for approval before removing the item. Trigger: poll approved_pop while approval is pending, then cancel or close the approval channel. Impact: item is already removed and is lost without approval. Fix: await successful approval before locking and popping.
- [P1] src/service.rs:32 - Observe termination of the owned worker. Trigger: stop_worker receives a running task paused before an effect. Impact: dropping JoinHandle detaches it, allowing the effect after stop returns. Fix: request cooperative shutdown or abort as appropriate, then await termination; a bare abort is not a completion barrier.
- [P1] src/publication.rs:23 - Publish readiness with a matching synchronization edge. Trigger: one writer publishes 42 while a reader observes ready. Impact: reader can return Some(0), verified by Loom under the required single-writer, one-shot contract. Fix: Release store of ready paired with Acquire load before reading value; retain the one-shot precondition and rerun the model.

## Residual risks
- Scope: origin/main fcd0f85b00baa7a8caa47007d8c5d6438e5fac9f to HEAD ad9b245b553746157b184bed5751e0a000e37e0b plus working tree and untracked files. Status was clean; no untracked source omitted. context.log and diff.log preserve scope.
- before-hashes.json and after-hashes.json match for every tracked/nonignored file. Reviewed source was not edited. Graph's ignored local cache was initialized with explicit repo_root; graph.json records change, flow and tests-for analysis. Its empty coverage results were verified against source, not treated as proof.
- Rust LSP workspace-symbol search succeeded (lsp.json). Toolchains recorded in toolchain.log. Edition 2024; no declared MSRV. Unpublished crate: semver checks N/A.
- Required diagnostics ran offline with existing tools and cached dependencies. Advisory freshness cannot be established without fetching; initial unsupported cargo-deny option failure is retained in deny.log, corrected command is in deny-offline.log. Gate commands/statuses are in gate-commands.json and gates-status.json; RUST_REVIEWDOG=1, CARGO_NET_OFFLINE=true.
- Repair suggestions are candidates and were not applied or validated. Memory errors are concrete alignment/bounds/lifetime failures, not a conflict between experimental alias models. Clippy output is recorded under Gates rather than duplicated as a finding.
