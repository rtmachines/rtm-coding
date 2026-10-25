## Verdict: APPROVE
The six requested contracts are supported by source review, seven ordinary tests, targeted Miri, controlled async probes and a completed Loom model. Approval is conditional on the explicit unsafe Registration caller contract and the documented one-shot/single-writer publication contract.

## Tooling
- rust-lsp: AVAILABLE (analyzer_status loaded the actual workspace and 34 packages)
- lsp-used: YES (hover resolved Registration::new; references found stop_worker declaration, import and regression-test invocation)
- lsp-evidence: tools.json contains actual calls with workspace /tmp/rust-review-lsp-20261025/cases/06, registration.rs:15 and service.rs:32. Explicit-root graph build, detect_changes, affected flows and tests_for preceded source review; tests_for found ffi_storage_lives_until_unregister.
- lsp-limitations: LSP analyzed default features, not the model configuration; compiler and Loom checked that configuration. Graph missed some macro-generated test relationships, so all implementation and test files were read directly.

## Gates
- fmt: PASS (fmt.log, exit 0)
- clippy: PASS (clippy.log, exit 0; reviewdog.log and reviewdog.exit record local presentation)
- tests: PASS (tests.log: 2 unit, 3 async and 2 memory tests passed; model-only integration target had zero tests and is covered separately by Loom)
- doctests: N/A (included in cargo test; no examples exist)
- deny: PASS (deny.log; cargo deny --locked --offline check, exit 0; equivalent offline option supported by installed cargo-deny)

## Memory safety
- memory-scope: REQUIRED (Registration retains foreign-readable raw storage until unregister; read_word alignment/bounds also checked)
- miri: PASS (five targeted memory tests, miri-memory.log, exit 0)
- aliasing: PASS (under explicit serialized, read-only, synchronous-quiescence callback preconditions)
- memory-evidence: probe is an exact copy of src and existing tests, with extended_memory.rs added outside reviewed tree. probe-source-hashes.json matches before.json. cargo +nightly miri test --locked --test memory --test extended_memory; MIRIFLAGS empty, Miri 48f4b05538 (2026-10-23), 120-second external deadline. Tests: short_slice_rejected, ffi_storage_lives_until_unregister, empty_registration, every_offset_and_short_length, retained_reads_through_unregister_after_move. Exercises short lengths, byte offsets, retained reads after return/move, read during unregister, and empty storage. No native foreign binary is claimed validated.
- aliasing-evidence: Box::into_raw preserves original fat-pointer provenance and length; raw pointer owner moves without introducing fresh exclusive references to the allocation. len/is_empty access metadata only. Callbacks may read but cannot write/free; Drop calls synchronous unregister before reconstructing exactly one Box from its original raw pointer. Thus all retained reads end before new exclusive ownership/free. Empty slice uses the valid original zero-length Box pointer and no byte dereference. No manual Send/Sync; no exposed storage mutator. read_word copies four bounded bytes into an array, so imposes no u32 alignment requirement. The unsafe contract explicitly delegates valid callbacks and quiescence to the caller, unlike an assumed vendor guarantee.

## Concurrency
- async-scope: REQUIRED (Service lock acquisition, approval cancellation, owned worker termination)
- deadlocks: PASS (nested_lock_completes and later_snapshot_and_contention; bounded progress and later snapshot verified)
- cancellation: PASS (cancel_before_approval_preserves_item; closed_approval_and_waiting_lock_preserve_queue)
- task-lifecycle: PASS (stopped_worker_cannot_receive_more_work, stop_waits_for_destructor, blocking_worker_is_joined)
- async-evidence: async-targeted.log has six passing tests on Tokio 1.54.1 current-thread runtimes, controlled future polling and oneshot handshakes. blocking-worker.log has one additional passing test of an already-running spawn_blocking worker: stop is Pending before release and returns after its effect finishes. Commands in probe-commands.json and blocking-worker command: cargo test --locked --test extended_async blocking_worker_is_joined. External deadlines 120 seconds (combined tests) and 30 seconds (blocking probe); internal progress deadlines 100ms to 2s. No sleeps establish the cancellation windows. Source hashes match. Increment guard is dropped before snapshot lock; approval precedes queue mutation, with no await after pop; abort is followed by awaiting termination. Tokio's exact-version JoinHandle docs guarantee task destructors have finished when await observes completion.
- sync-scope: REQUIRED (Published value/ready one-shot publication)
- loom: PASS (publication_is_coherent, one completed nonzero model test, loom.log exit 0)
- synchronization: PASS (Release ready store synchronizes with Acquire true load; prior value store happens-before reader's value load)
- model-evidence: cargo test --locked --features model --test publication, exact src/publication.rs. Loom 0.7.2 tracked AtomicUsize/AtomicBool, Arc and thread. One writer performs Relaxed value store then Release ready store; reader Acquire-loads ready then conditionally Relaxed-loads value, asserting any Some is 42. Two threads, one publish and one snapshot, followed by join; no reuse/multiwriter is allowed by contract. loom-env.json records no overrides; defaults max_threads=5, max_branches=1000, no preemption/permutation/duration limit; external process deadline 120 seconds, completed. Reader-before-writer may see None; reader-after-release sees Some and must see the stored value. The Release/Acquire proof independently covers the assertion, not merely test completion.

## Spec
- spec: PASS (REQUIREMENTS.md separately checked against all six adapters and ordinary-check boundedness)
- missing: None identified. Alignment/short slices, retained ownership through unregister, increment progress/later snapshots, preapproval cancellation, worker termination and one-shot publication each have relevant evidence.
- unrequested: No unrelated runtime behavior identified; workflow support is included in review scope.
- contradictions: None identified within documented caller preconditions.

## Findings
No findings.

## Residual risks
- Scope: origin/main 65df47294846eb2e2d435a952baf6d7bfeba1851 to HEAD f44e93e818b0fa32e89a03b80c4f0ccb6f8be46a plus working tree; initially clean, no untracked inputs. before.json/after.json and git-before.txt/git-after.txt match; implementation copies verified byte-identical.
- Offline cached advisory data freshness is unverified; no fetch/install performed. Edition 2024, no declared MSRV, unpublished crate: semver checks N/A by policy. Default features for ordinary gates; model feature separately compiled and run only within loom::model.
- Miri is not a proof about arbitrary foreign consumers; unsafe callers must obey the declared callback contract. Loom is finite and scoped to the documented one-shot protocol. stop_worker waits for running blocking tasks rather than forcibly stopping them; no bounded shutdown for nonterminating blocking code was promised. Cancellation of stop_worker itself does not promise completed shutdown.
