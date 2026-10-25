## Verdict: APPROVE
No P0/P1 defects found. The one-shot Release/Acquire publication protocol in `src/lib.rs` is correct by argument. The feature-gated Loom model ran the exact source with Loom's tracked primitives, completed with no bounds, and failed when the ordering was weakened in a separate mutant. All gates passed. Caveats: ordinary (non-model) gates select 0 tests, and LSP and code-review-graph were unavailable.

## Tooling
- rust-lsp: UNAVAILABLE (this environment exposes no LSP/MCP tool, so no workspace probe was possible)
- lsp-used: NO
- lsp-evidence: No native LSP, rust-lsp or code-review-graph tool was exposed to this agent, so none was called. Nothing was claimed.
- lsp-limitations: Review used source reading, git diff and Cargo diagnostics. The reviewed Rust scope is two small files (`src/lib.rs` 22 lines, `tests/publication_model.rs`), read in full. No semantic call-graph or reference queries were done. Not needed for scope this small, but the limitation stands.
- Knowledge: local rust-skills (pinned `rtmachines/rust-skills` a1e290d53d43a85421ff16dde23b5f8ec0b48539 per `.claude/rust-review-kit/vendored.tsv`). Rules read: `conc-atomic-ordering`, `test-loom-concurrency` (first sections only). References read: SKILL.md, CONCURRENCY-VALIDATION.md, SPEC-PASS.md (head). SMELLS.md, SAFETY-PRECHECK.md and MEMORY-VALIDATION.md were not opened; they do not apply because there is no unsafe code or FFI.

## Gates
Run offline in an exact copy at `reviews/09/src` with `RUST_GATE_FEATURES=''`, `CARGO_NET_OFFLINE=true` and an external target dir. The gates.sh exit status is saved in `gates.status`.
- fmt: PASS (`cargo fmt --all -- --check`, exit 0)
- clippy: PASS (`-D warnings`, `--all-targets --locked`, default features. Also PASS with `--features model`: `clippy-model.log`)
- tests: PASS (ordinary gate: nextest "0 tests run" across 2 binaries, because the only test is gated on `feature = "model"`. This is not targeted coverage. The model run below is the covering evidence: `cargo test --locked --offline --features model --test publication_model` ran 1 test, 1 passed)
- doctests: PASS (`cargo test --doc --locked`: 0 doctests, exit 0)
- deny: PASS (`cargo deny --locked --offline check`: advisories, bans, licenses and sources ok. Offline freshness limitation: the advisory DB is the local copy and was not refreshed. Warning: unused license allowance `BSD-3-Clause`.)

## Memory safety
- memory-scope: NONE (no `unsafe`, FFI or raw pointers in the diff; only safe std/loom atomics)
- miri: N/A (no unsafe or memory-boundary code)
- aliasing: N/A (no references or pointers beyond safe shared `&self` atomics)
- memory-evidence: N/A, same reason
- aliasing-evidence: N/A, same reason

## Concurrency
- async-scope: NONE (no async code. The tokio dependency is declared but unused by the diff)
- deadlocks: N/A (no locks)
- cancellation: N/A (no futures)
- task-lifecycle: N/A (only a Loom thread joined in the model)
- async-evidence: N/A
- sync-scope: REQUIRED (`src/lib.rs` `Published::publish`/`snapshot`: atomic one-shot publication protocol)
- loom: PASS (`tests/publication_model.rs::publication_model`; loom 0.7.2, `--features model`. 1 test passed and printed "completed model executions: 6". Builder sets `max_permutations`, `max_duration`, `preemption_bound` and `checkpoint_file` to None, so exploration is unbounded and ran to completion in about 0s, under the 120s watchdog. `assert!(count > 1)` guards against a vacuous run. The model uses the exact `Published` source, and under `feature = "model"` its atomics are `loom::sync::atomic`, so they are tracked. The model has one writer thread, matching the one-shot contract. Concurrent `snapshot()` asserts `None` or `Some(42)`, and the post-join snapshot asserts `Some(42)`.)
- synchronization: PASS (see argument) Invariant: `ready == true` implies `value` holds the published value. The writer stores `value` (Relaxed), then `ready` (Release). The reader loads `ready` (Acquire) and loads `value` only when it saw true. The Release store synchronizes-with the Acquire load, so the value store happens-before the value load, and the reader sees 42. If the reader sees false it returns None, which the spec allows. There is a single writer and a single transition (false to true), so there is no ABA or reuse. Non-vacuity control: in `reviews/09/mut` I replaced Release/Acquire with Relaxed. The model then failed (exit 101, assertion `left == right` at `tests/publication_model.rs:19`). Log: `mutant.log`. The reviewed tree was not touched.
- model-evidence: Source hashes in `hashes.txt` (src/lib.rs b00494db…b7fb, tests/publication_model.rs 83d08a7b…3773). Commands and logs: `model.log` (status 0), `gates.out`/`gates.err`/`gates.status`, `deny-offline.log`, `clippy-model.log`, `mutant.log`. Edition 2024; Cargo.lock locked; loom 0.7.2 from the offline cache. Limits: Loom is a bounded model of the exercised operations, not a proof of every C11 behavior.

## Spec
- spec: PASS (REQUIREMENTS.md: "One writer calls publish exactly once. A concurrent snapshot may return None; if it returns Some, it must equal the published value. Require model exploration of this publication/read protocol.")
- missing: None. Model exploration is present and was run to completion.
- unrequested: Declared but unused `tokio` dependency (`=1.54.1`) in Cargo.toml. It is in the base manifest and not part of this diff. Minor.
- contradictions: None. Single-writer, single-publish is documented in the `publish` doc comment but not enforced by the type. A second `publish` or concurrent writers would break the guarantee only outside the stated contract.

## Findings
No findings.

## Residual risks
- Scope: base origin/main 8f1034f207c0d4697d21786398f79f6d97f7c264, head e8db05b9309f52b6a5c2dde61197cb56a89f0786. `git status` showed no untracked files outside the ignored paths. The Rust diff is `src/lib.rs` and the new `tests/publication_model.rs` (both tracked in HEAD). The rest of the diff against origin/main is the review-kit scaffolding (`.claude/**`, `CLAUDE.md`, `REVIEW.md`, `REQUIREMENTS.md`), which I treated as tooling and did not review. The reviewed tree was not modified.
- The `model` feature is not covered by the default CI gate (`RUST_GATE_FEATURES=''`), so the Loom test must be run explicitly with `--features model`.
- `publish` can be called more than once, and `publish` and `snapshot` are public safe APIs. This is an API robustness note, not a defect against the stated contract (P3 at most).
- Loom explored 6 executions. Loom's relaxed-memory modeling is incomplete in general (see test-loom-concurrency), but the ordering argument is independent of it.
- The advisory DB is offline and may be stale. No LSP or graph tooling was used.
