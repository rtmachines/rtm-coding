## Verdict: APPROVE
Scope is the local Acme reference provider as defined in VENDOR-CONTRACT.md. The gates and the tracked Loom model all pass. All four cancellation cells (timeout and drop, each before and after commit) have execution evidence against the real provider. I found no demonstrated defect, no unsafe code and no unresolved synchronization question. The one gap is that the timeout-before-commit cell is not covered by a checked-in test. I closed it with an isolated exact-source probe, so it is a P3 recommendation only.

## Tooling
- rust-lsp: UNAVAILABLE (no Rust LSP or MCP APIs are exposed in this session; the environment intentionally exposes none)
- lsp-used: NO (no semantic calls were made)
- lsp-evidence: Tool inspection found no LSP, code-review-graph or rust-lsp tools. No setup was attempted because installing tools is not authorized.
- lsp-limitations: Read all 5 changed Rust files in full (about 212 lines) and the manifests directly. The compiler, clippy and tests give type-level confirmation. The code-review-graph was not used, so scope came from git (`context.sh`, `git status`) and file reads. The total scope is small, so the gap is minor.
- rust-skills: the local index `.claude/skills/rust-skills/SKILL.md` (v1.5.1+local.1, upstream fd2a861) was read. The pinned revision is also recorded in `.claude/rust-review-kit/vendored.tsv`. I read the index and the CONCURRENCY-VALIDATION, RUST-LSP and SPEC-PASS references. I did not open individual `rules/` files.

## Gates
Run offline with `RUST_GATE_FEATURES=''` and `CARGO_NET_OFFLINE=true`, using a target directory under the review output directory. `gates.sh` exited 0. Logs: gates.out, gates.err, gates.status.
- fmt: PASS (`cargo fmt --all -- --check`, exit 0)
- clippy: PASS (`--workspace --all-targets --locked -- -D warnings`, no diagnostics)
- tests: PASS (nextest: 5 run, 5 passed, 0 skipped: delivery::delivers, delivery::returns_for_retry, vendor_tests::timeout_after_commit_then_retry_deduplicates, vendor_tests::cancel_at_both_boundaries_then_retry, vendor_tests::reconnect_and_quiescent_restart_preserve_keys)
- doctests: PASS (0 doctests exist, command exit 0)
- deny: PASS (`cargo deny --locked --offline check`, exit 0: advisories ok, bans ok, licenses ok, sources ok). The warning "BSD-3-Clause allowance not encountered" is benign. The advisory database is a local offline copy, so freshness is unknown and it may be stale; no fetch was made.

The feature model was run separately: `cargo test --locked --offline --features model --test vendor_model`, exit 0, 1 test passed (see Concurrency).

## Memory safety
- memory-scope: NONE (the diff in src/acme.rs, src/lib.rs and tests contains no `unsafe`, FFI or raw pointers; sharing uses safe `Arc<Server>` and `Mutex`)
- miri: N/A (no unsafe or FFI code)
- aliasing: N/A (safe Rust only)
- memory-evidence: N/A. A grep of the source shows no `unsafe`.
- aliasing-evidence: N/A, same reason.

## Concurrency
- async-scope: REQUIRED (src/lib.rs `deliver` with `tokio::time::timeout`; src/acme.rs `AcmeTransport::send` suspends before commit and after commit, so cancellation and retry semantics are affected)
- deadlocks: N/A (`commit`, `snapshot` and `effect_count` each take a single mutex, with no await while the guard is held and no nested lock; the Loom model also completed)
- cancellation: PASS (all four contract cells executed against the real provider; matrix mapped to tests and assertions below)
  - timeout after commit: `timeout_after_commit_then_retry_deduplicates` (`Duration::ZERO`, `LoseAfterCommit`): returns `Retry(7)`, effects = 1, and 3 retries return `Delivered(7)` with effects staying 1.
  - drop before commit: `cancel_at_both_boundaries_then_retry` with `StallBeforeCommit`: the future is polled to Pending, effects = 0, it is dropped, and the retry gives effects = 1.
  - drop after commit: the same test with `LoseAfterCommit`: effects = 1 at drop, and after the retry effects is still 1.
  - timeout before commit: no checked-in test uses the real provider (`delivery.rs` uses a mock `Pending`). I closed this with an external exact-source probe: `probe/tests/p.rs::timeout_before_commit_then_retry` (1 passed, probe.log). It gives `Retry(5)`, effects = 0, then a retry gives `Delivered(5)` with effects = 1.
  - reconnection and quiescent restore: `reconnect_and_quiescent_restart_preserve_keys` checks that the restored Snapshot dedupes ID 11 (effects = 1) and that a distinct ID 12 gives effects = 2.
- task-lifecycle: N/A (AcmeTransport spawns no tasks; the contract states there is no background work)
- async-evidence: tokio 1.54.1 `#[tokio::test]` (current-thread). Cancellation uses explicit `Waker::noop` polling and a handshake, not sleeps. Timeouts use `Duration::ZERO`, which is deterministic because `timeout` polls the inner future first. Test counts are copied from gates.err. The probe was run in reviews/10/probe with copied source (hashes in source-hashes.txt; the reviewed tree is unchanged).
- sync-scope: REQUIRED (the `Mutex<Snapshot>` commit transaction shared across threads)
- loom: PASS (`competing_retries_commit_once`: 1 test passed (exit 0) under `--features model` with loom 0.7.2, within the 120 s watchdog (~0 s), and the test completed. It uses the actual `Server` from src/acme.rs with `loom::sync::{Arc, Mutex}` selected by cfg, so the exercised primitives are Loom-tracked. The model has 2 threads, with `max_threads` 3, `preemption_bound`, `max_permutations` and `max_duration` all None (unbounded), and `max_branches` 1000. It asserts that both competing `commit(7)` calls return 7, that effects == 1, and that a subsequent distinct ID gives effects == 2. Model scope is the ledger transaction only, as the contract states.)
- synchronization: PASS ( The invariant is that the ID set and the effect counter change only under one mutex guard. `BTreeSet::insert` returning true gates `effects += 1` within the same critical section, so each ID produces at most one effect. Lock release/acquire handoff gives readers a consistent view. There is a single lock, so there is no lock-order cycle. `unwrap()` on a poisoned mutex can only panic, and panics under the lock cannot occur in the current code. The snapshot is cloned under the lock.)
- model-evidence: see the loom item above. Command: `cargo test --locked --offline --features model --test vendor_model`; log: loom.log, status: loom.status.

## Spec
- spec: PASS (REQUIREMENTS.md and VENDOR-CONTRACT.md were both available. REQUIREMENTS.md asks for: retry on timeout with the same request ID and namespace, no duplicate ledger effect, and executed contract acceptance scenarios.)
- missing: nothing required. All scenarios have execution evidence, with the timeout-before-commit cell provided by the isolated probe.
- unrequested: none. The `Reply::Normal`, `StallBeforeCommit` and `LoseAfterCommit` fault modes are part of the reference provider by contract.
- contradictions: none. Dedupe is by ID in `Server`, the receipt is the ID, and `Snapshot` carries both the ID ledger and effect count. There is no TTL or eviction. The documented non-claims are accepted: a fresh empty Server is a new namespace, and there is no crash durability or stale-snapshot safety.

## Findings
- [P3] tests/vendor_tests.rs:1 - Coverage gap: no checked-in test exercises the real provider with a timeout (rather than a drop) before commit. Trigger: the contract matrix lists timeout and drop at both boundaries; the test `cancel_at_both_boundaries_then_retry` only drops the future, and the only timeout-before-commit test uses a mock in `delivery.rs`. Impact: a regression in `deliver`'s timeout path with `StallBeforeCommit` would go unnoticed. The behavior is correct (verified by the external probe). Fix: add a test like `timeout_before_commit_then_retry` (`StallBeforeCommit`, `Duration::ZERO`, effects 0, then a normal retry gives effects 1).

## Residual risks
- Scope: base origin/main bd721a61e5d30a6014e49f183a5f12647fd4bf0c, head b45e0e76ee7568dcda06e5cb9ebeb36dd85cea21. `git status` showed a clean tree with no untracked or dirty files. The review diff is the whole implementation: src/acme.rs, src/lib.rs, tests/*.rs plus the committed workflow files. Hashes of the reviewed files were verified unchanged after the runs (source-hashes.txt). The reviewed tree was not edited, and Cargo outputs went to a target directory under reviews/10.
- The deny advisory check used a local database of unknown freshness (offline).
- The Loom model is unbounded in permutations and covers 2 threads and 3 commit calls; it applies only to the ledger transaction, not Tokio or network behavior.
- No LSP or code-review-graph semantic coverage (see Tooling).
- Semver-checks: N/A (an unpublished 0.1.0 crate with `publish = false`).
- Out of scope per contract: durable or crash recovery, stale snapshots, and simultaneous old and new servers.
