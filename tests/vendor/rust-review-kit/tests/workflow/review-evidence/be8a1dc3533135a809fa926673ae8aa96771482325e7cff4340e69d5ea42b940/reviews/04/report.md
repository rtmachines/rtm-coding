## Verdict: ESCALATE
Ordinary gates and targeted async/publication checks pass. Registration has conflicting alias-model results: Stacked Borrows rejects retained-pointer access after the Box move while Tree Borrows accepts it. This unresolved provenance obligation blocks approval.

## Gates
- fmt: PASS (fmt.log; exit 0)
- clippy: PASS (clippy.log; exit 0)
- tests: PASS (tests.log; exit 0)
- doctests: PASS (doctests.log; exit 0)
- deny: PASS (deny.log; exit 0)

Two shipped unit tests pass; zero doctests. Equivalent offline gates used; exact commands/statuses are in gates.json. RUST_REVIEWDOG=1, nofilter local reporter, raw Clippy and reviewdog output retained in rust-review-clippy.* directories. Clippy verdict follows its own exit code; all reviewdog presentation statuses are recorded separately.

## Memory safety
- memory-scope: REQUIRED (Registration retains a pointer across Box ownership moves and Drop callbacks)
- miri: FAIL (default Stacked Borrows diagnostic in miri-stacked.log; identical test passes Tree Borrows in miri-tree.log)
- aliasing: UNRESOLVED (experimental models disagree; allocation liveness alone does not prove pointer validity)
- memory-evidence: One exact-source test retained_read_after_return_move_and_unregister, in probe/tests/memory.rs. Commands in miri-stacked-status.json and miri-tree-status.json; nightly rustc/Miri 1.101.0-nightly commit 48f4b05538b8eca412137042d9647a61e692c6b3 (2026-10-23), existing MIRI_SYSROOT=/home/rtm/.cache/miri, MIRIFLAGS empty versus -Zmiri-tree-borrows. Each process bounded at 120 seconds. No native UB run. Source equality recorded in probe-source-hashes.json against before-hashes.json.
- aliasing-evidence: bytes.as_ptr() at src/registration.rs:20 derives the retained read-only pointer. Moving bytes into Self at :21 keeps allocation/address alive but gives a Unique retag under Stacked Borrows, invalidating the shared tag before the first post-return read. The test also covers a later owner move, safe len access, and read during unregister; Tree Borrows reaches all of them. Drop invokes unregister before automatic Box free, so the lifetime/free ordering is correct under the documented synchronous no-write/no-free, serialized callback contract. Rust extern-C callbacks obey that contract and stop reads before return; they do not validate an arbitrary foreign provider. Need a justified provenance argument resolving the model discrepancy or a separately validated representation redesign. No tested fix is claimed.

## Concurrency
- async-scope: REQUIRED (Service lock progress, approved_pop cancellation, stop_worker termination)
- deadlocks: PASS (progress_and_later_snapshot completes competing increments then snapshot within one-second Tokio timeout)
- cancellation: PASS (cancellation_and_channel_closure_preserve_queue polls pending before approval and while waiting for queue lock, drops futures, checks queue; closed approval consumes nothing)
- task-lifecycle: PASS (stop_observes_destructor_and_prevents_effects handshakes to a known suspended worker, stops it, checks destructor ran and later effect signal cannot reach worker)
- async-evidence: probe/tests/targeted.rs; targeted.log and targeted-status.json, three targeted async tests plus alignment_and_short_input all pass on Tokio 1.54.1 current-thread runtime. Controlled polls/oneshots, one-second local progress deadlines, 120-second external process watchdog. Exact source/manifests/lockfile copied unchanged; probe-source-hashes.json. Guard block ends before snapshot awaits; approved_pop mutates only after approval and acquiring queue; abort is followed by JoinHandle await.
- sync-scope: REQUIRED (one-shot Published release/acquire protocol)
- loom: PASS (publication_model completes without permutation/time/preemption truncation)
- synchronization: PASS (value.store Relaxed precedes ready.store Release; an Acquire load observing true synchronizes with the unique release, so subsequent Relaxed value load must see the only published value; false may return None. One writer/one publish is the explicit precondition.)
- model-evidence: probe/tests/model.rs imports exact src/publication.rs with feature model selecting Loom 0.7.2 tracked AtomicUsize/AtomicBool, Arc and thread. Main reader competes with one writer, checks every Some equals 42 and post-join Some(42). max_threads=3 (two active), max_branches=1000, no permutation/duration/preemption bound; model.log exit 0 before 120-second external watchdog. Source hashes preserved; command in model-status.json. This finite protocol model does not cover Tokio runtime scheduling.

## Spec
- spec: PARTIAL (REQUIREMENTS.md: five behavioral contracts validated; Registration ownership/lifetime structure meets the requested shape but retained-pointer alias validity remains unresolved)
- missing: A resolved provenance justification for Registration; there were no shipped targeted async/memory/model tests, supplemented by authorized exact-source probes.
- unrequested: No extra functional subsystem identified.
- contradictions: No definitive functional contract contradiction established; alias-model disagreement is an escalation, not a proven portable unsoundness finding.

## Findings
No findings.

## Residual risks
- Scope: origin/main base 007e8d5210660d3bdc54d78b49d6100f8ff2b399; HEAD 2997ae3d7ee078e7953932f577b34696e4ed36fa; base-to-current working tree including local/untracked files. Clean tracked tree; no untracked review inputs. context.log and diff.log retain scope evidence.
- Integrity: before-hashes.json equals after-hashes.json for every original tracked/untracked input. after-status.log preserves Git status. Probe implementation/configuration is byte-identical where used; harness additions are isolated under this review directory.
- Method: repository graph initialized with explicit repo_root, change/flow/tests-for queries and Rust LSP workspace symbol lookup preceded source inspection. graph-lsp.json and graph-review.json retain responses. Empty graph test edges were not treated as proof of no tests; exact source/tests were read.
- Offline freshness: cargo-deny passed using the existing cached advisory database without fetching; this does not establish current online advisory coverage. No dependency/tool installation or external service access. Host-only diagnostics; versions.log records compiler.
- Limitations: Semver checks N/A: unpublished crate (publish=false), no release baseline requested. All manifests edition 2024; no inferred MSRV. Foreign callbacks are caller-supplied under the documented unsafe contract; no undocumented native provider was assumed. Alias-model discrepancy needs specialist resolution.
