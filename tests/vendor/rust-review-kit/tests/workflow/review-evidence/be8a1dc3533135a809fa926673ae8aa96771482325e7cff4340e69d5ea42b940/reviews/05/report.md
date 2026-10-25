## Verdict: ESCALATE
Ordinary gates pass, but the SDK header does not establish callback quiescence at unregister return. An exact-source diagnostic also disagrees between Stacked Borrows and Tree Borrows. Neither a supported-vendor safety proof nor an aliasing proof is available; this is not an assertion that the unavailable vendor has a demonstrated bug.

## Gates
- fmt: PASS (`fmt.log`, exit 0).
- clippy: PASS (`clippy.log`, exit 0; RUST_REVIEWDOG=1, raw diagnostics retained, reviewdog exit 0).
- tests: PASS (`tests.log`, default features, offline/locked).
- doctests: PASS (`doctests.log`, zero doctests; explicitly executed).
- deny: PASS (`deny-offline.log`, offline/locked; cached advisories, unmatched BSD-3-Clause allowance warning only).

## Memory safety
- memory-scope: REQUIRED (`src/vendor.rs:22-32`, retained context registration, owner moves and teardown).
- miri: FAIL (one conditional retained-context test fails under default Stacked Borrows; identical test passes with Tree Borrows; this experimental-model disagreement is not settled UB proof).
- aliasing: UNRESOLVED (Box movement and mutable reborrow interact with the retained pointer; provider quiescence contract is absent).
- memory-evidence: Exact `src/vendor.rs` copied into `probe/src/vendor.rs`; `probe-hashes.json` matches source hashes. `probe/tests/retained.rs::retained_context_after_move_and_during_unregister` exercises a same-thread read after attach returns and the owner moves, then a read during synchronous unregister. Miri 0.1.0 (48f4b05538, 2026-10-23), nightly Rust 1.101.0-nightly, offline/locked, 120-second watchdog, default MIRIFLAGS versus `-Zmiri-tree-borrows`; see `miri-stacked.log` (exit 1) and `miri-tree.log` (one passed, exit 0). The shim assumes synchronous read-only deregistration; it is not the supported vendor binary and cannot prove its behavior.
- aliasing-evidence: Token storage originates in Box::new at line 23. A pointer is derived from `&mut *token` at line 25 and retained by registration. Moving the Box into Self at line 26 preserves its allocation address but Miri Stacked Borrows invalidates the retained tag through a Unique retag; the post-constructor read fails. Tree Borrows allows this execution, including the line 32 reborrow and read during unregister. Allocation is freed after Drop returns. `vendor.h:1-3` specifies only ABI signatures, not when active or queued callbacks stop, whether unregister drains them, or read/write/reentrancy obligations. Closure requires the versioned supported SDK contract or implementation audit proving quiescence before freeing and resolving callback threading/reentrancy, plus a justified pointer/provenance design validated in targeted tests. A raw allocation owner is only a candidate redesign until tested; no fix was made.

## Concurrency
- async-scope: NONE (no Rust asynchronous execution or task ownership in the changed code).
- deadlocks: N/A (no async lock protocol).
- cancellation: N/A (no futures or cancellation).
- task-lifecycle: N/A (no spawned task handles).
- async-evidence: N/A (scope justification above).
- sync-scope: NONE (no custom Rust shared-state protocol; foreign callback quiescence is unresolved under Memory safety).
- loom: N/A (no modelable Rust atomic/lock protocol in this adapter).
- synchronization: N/A (foreign lifecycle guarantees must come from SDK evidence).
- model-evidence: N/A (ABI declarations alone do not expose the vendor implementation).

## Spec
- spec: PARTIAL (`REQUIREMENTS.md` requests RAII callback ownership and safe teardown; construction/destruction structure exists, but memory-safety obligations remain unverified).
- missing: Evidence for provider quiescence and a resolved aliasing argument; no demonstrated missing functional API.
- unrequested: No additional runtime behavior identified.
- contradictions: No proven provider-contract contradiction; safety is unresolved rather than presumed.

## Findings
No findings.

## Residual risks
- Scope: base 557bc5880174a61011a98ca8d289272427e36224 (origin/main), head f15a3ba9775b4d19899aa6595412f578bdf4efd7. Clean working tree; no nonignored untracked files at inventory. Branch plus local scope included all changed source, header, policy and helper files; `context.log` and `diff.log` preserve scope.
- Unresolved locations: `src/vendor.rs:25-26` (retained-pointer provenance), `src/vendor.rs:30-32` and `vendor.h:1-3` (quiescence, threading, callbacks during teardown). Do not approve based on stable address or the passing Tree Borrows result.
- Semver: N/A under project policy (unpublished package).
- All commands, statuses and logs are in this report's directory (`commands.txt`, `status.json`, `*.command`, `*.log`). Stable Rust 1.99.1, edition 2024; no MSRV declared. Exact tool versions are in `toolchain.log`. Source hashes before/after are identical (`before-hashes.json`, `after-hashes.json`, `source-unchanged.txt`). Graph navigation and Rust LSP symbol evidence are recorded in `navigation.json` and `tests-graph.json`; source and tests were read independently because graph coverage is incomplete. All work was offline; advisory freshness and availability of uncached dependencies were not refreshed. No reviewed source was edited. Initial cargo-deny invocation used an unsupported flag (exit 2); the corrected offline invocation passed, and both logs remain. No external comments, push or publication occurred.
