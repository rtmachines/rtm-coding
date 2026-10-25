## Verdict: ESCALATE
Ordinary gates and targeted concurrency checks succeed, but the retained registration pointer has conflicting Miri alias-model results. Do not approve based on allocation liveness alone.

## Tooling
- rust-lsp: AVAILABLE (analyzer_status loaded /tmp/rust-review-lsp-20261025/cases/04).
- lsp-used: YES (successful hover and references).
- lsp-evidence: tools.json records slice as_ptr hover at src/registration.rs:20 and snapshot references resolving src/service.rs:18 and :42; abort-hover.json resolves JoinHandle::abort and its spawn_blocking caveat for locked Tokio 1.54.1.
- lsp-limitations: Queries cover ownership origin and service call paths; exact source and tests were read for remaining paths. Graph build/detect/affected-flows/tests_for ran with explicit repo_root; graph reported two flows but no tests_for results, so source coverage was independently checked.

## Gates
- fmt: PASS (fmt.log exit 0).
- clippy: PASS (clippy.log exit 0, reviewdog.log exit 0).
- tests: PASS (tests.log: two tests executed; default features per project policy).
- doctests: N/A (included in Cargo test validation; separate doctests.log command exits 0 with zero examples, not behavioral evidence).
- deny: PASS (deny.log exit 0 with --offline; cached advisory data).

## Memory safety
- memory-scope: REQUIRED (Registration retains a pointer across Box ownership moves and invokes an unsafe callback in Drop).
- miri: FAIL (Stacked Borrows retained-pointer probe rejects access; Tree Borrows passes the same two tests).
- aliasing: UNRESOLVED (conflicting experimental alias models).
- memory-evidence: probe/tests/memory.rs runs arbitrary_alignment_and_short and retained_reads_after_move_and_during_unregister on byte-identical copied source (probe-hashes.json). miri-stacked.log: first test passes, second aborts, exit 1. miri-tree.log: both pass, exit 0. Commands: CARGO_NET_OFFLINE=true timeout 90 cargo +nightly miri test --locked --test memory; same with MIRIFLAGS=-Zmiri-tree-borrows. Default run has empty MIRIFLAGS. Toolchain rustc 1.101.0-nightly commit 48f4b05538b8eca412137042d9647a61e692c6b3, Miri 0.1.0, detailed in miri-version.log. Existing rust-src and Miri sysroot were checked; no installation.
- aliasing-evidence: src/registration.rs:20 derives a shared raw pointer from owned Box storage, then :21 moves the Box into Self. Stacked Borrows identifies that move's Unique retag as invalidating the retained SharedReadOnly tag; the first post-construction read fails. Tree Borrows permits the same read, owner move, and read during unregister. Allocation remains live through Drop body and is freed afterwards, so ordinary liveness is satisfied but provenance is unresolved. Mock callbacks obey the declared serialized, read-only, synchronous-quiescence contract and perform no native FFI. Close by establishing a justified provenance design or separately validating a redesign across models; a candidate fix is not claimed here.

## Concurrency
- async-scope: REQUIRED (Service lock progress, approved_pop cancellation, stop_worker task completion).
- deadlocks: PASS (increment_progress completes and allows a later snapshot).
- cancellation: PASS (cancel_before_approval, cancel_after_approval_waiting_for_lock and closed_approval_preserves_queue preserve the queue).
- task-lifecycle: PASS (stop_observes_destruction and stop_waits_for_started_blocking_worker verify completion before return).
- async-evidence: async.log: six targeted tests execute and pass under Tokio 1.54.1 current-thread runtime, timeout 30 process bound, one-second operation deadlines and two-second blocking-worker receive bound. Manual poll with noop Waker establishes Pending at approval/lock/stop boundaries; channels establish worker startup and release. No timing sleeps. Exact copied src/service.rs hashes in probe-hashes.json. Increment releases its guard before snapshot; approved_pop mutates only after approval and lock acquisition; stop_worker awaits termination after abort, including already-started blocking workers.
- sync-scope: REQUIRED (Published one-shot atomic publication).
- loom: PASS (one_shot_publication completes with no counterexample).
- synchronization: PASS (ready Release/Acquire publishes preceding relaxed value store).
- model-evidence: loom.log and probe/tests/model.rs: cargo test --locked --features model --test model, timeout 90, one executed test, exit 0. Loom 0.7.2; byte-identical publication.rs uses its existing model feature to select Loom AtomicBool/AtomicUsize, tracked Arc and thread. Two threads, one writer publishes 42 exactly once; reader snapshot races then reads again after join. Every observed Some must equal 42 and final value must be Some(42). max_branches=1000, preemption_bound=3, no permutation cap, completed within deadline. Under the documented single-writer one-shot precondition, observing ready=true via Acquire synchronizes with Release after the value write; no later writes can replace it. Bounds support this model, not an unbounded proof.

## Spec
- spec: PARTIAL (REQUIREMENTS.md; all functional requirements have source and targeted evidence except unresolved retained-pointer safety).
- missing: No requested API absent; repository originally has only two happy-path tests and no memory/model probes.
- unrequested: No additional product behavior; model feature is explicitly designated diagnostic-only.
- contradictions: No independently proven functional contradiction; Registration's pointer-validity obligation remains unresolved.

## Findings
No findings.

## Residual risks
- Scope: origin/main 007e8d5210660d3bdc54d78b49d6100f8ff2b399 through HEAD c89f3b844c288456c3e8711f97d32438f0eb4b72; clean tree, no untracked source. Full diff/context retained. before.json and after.json identical; probe-hashes.json verifies exact source copies.
- Safety escalation at src/registration.rs:20-21 is experimental-model disagreement, not a claim of a settled production UB defect. No native provider was specified; callback obligations are the unsafe caller's explicit contract, and the shim only validates Rust wrapper behavior under that contract.
- No semver gate for unpublished crate. Default features tested ordinarily as required; model only under Loom. cargo-deny 0.20.2 uses --offline (supported replacement for removed --disable-fetch), so advisory freshness is limited to local cache. No installs or reviewed-source edits.
