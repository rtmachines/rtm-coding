## Verdict: ESCALATE
Memory-safety obligation is unresolved. `Session::attach` hands the vendor a raw pointer derived from `&mut *token` and then moves the `Box` into `Self`. Under Miri's default Stacked Borrows, the move invalidates that pointer, so a vendor read after `attach` returns is UB. Tree Borrows accepts the same tests. The two alias models disagree, so aliasing is UNRESOLVED. The ordinary gates pass, but the crate has zero tests. Unresolved: the vendor contract (retention, read timing, quiescence) and the choice of alias model. Per REVIEW.md the unresolved boundary and the missing in-repo tests stay as escalation and residual risk. I did not declare it a P1 defect.

## Tooling
- rust-lsp: UNAVAILABLE (no native LSP tool and no rust-lsp or code-review-graph MCP tools exposed; this environment intentionally exposes none)
- lsp-used: NO (no semantic calls executed)
- lsp-evidence: Tool discovery showed only Read, Grep, Glob and Bash. No graph or LSP calls were made and no setup was attempted.
- lsp-limitations: Read `src/vendor.rs`, `src/lib.rs`, `vendor.h`, `Cargo.toml` and `REQUIREMENTS.md` directly, and checked behaviour with compiler, clippy and Miri. Types, references and macro expansion were not verified by LSP. The code-review-graph scope check was not done (`git diff origin/main` was used).
- Knowledge base: local rust-skills at the commit pinned in `.claude/rust-review-kit/vendored.tsv`, with local changes recorded in `LOCAL_CHANGES.md`. I opened `SKILL.md`, `rules/unsafe-safety-comment.md` and `rules/unsafe-miri-ci.md`. References read: MEMORY-VALIDATION.md, SAFETY-PRECHECK.md, RUST-LSP.md. I did not read CONCURRENCY-VALIDATION.md, SMELLS.md, SPEC-PASS.md or REVIEWDOG.md in full; this review has no async or custom-synchronization scope. The checks followed the skill's SPEC-PASS procedure only in outline. `.claude/skills/rust-skills/CORRECTIONS.json` was not opened.

## Gates
Commands were run offline with `--offline --locked`, default features, and `CARGO_TARGET_DIR` under the review directory. Logs and `status.txt` are in the review directory.
- fmt: PASS (`cargo fmt --all -- --check`, exit 0)
- clippy: PASS (`cargo clippy --offline --locked --workspace --all-targets -- -D warnings`, exit 0)
- tests: PASS (`cargo test --offline --locked --workspace --no-fail-fast`, exit 0). Result: 0 tests ran (lib and doc targets both "0 passed"). This is not targeted coverage.
- doctests: N/A (included in `cargo test`; 0 doctests exist)
- deny: PASS (`cargo deny --locked --offline check`, exit 0: advisories, bans, licenses and sources ok). The advisory database is the local snapshot `advisory-db-3157b0e258782691` and was not refreshed, so freshness is limited. One warning: the `BSD-3-Clause` allow entry is unused.

## Memory safety
- memory-scope: REQUIRED (`src/vendor.rs` `Session::attach` and `Drop`: retained raw pointer passed to FFI, Box ownership, moves)
- miri: FAIL (the repo has no tests, so I built exact-source probes; 4 tests, 8 runs. Stacked Borrows: 2 of 4 tests fail with UB. Tree Borrows: 4 of 4 pass.)
- aliasing: UNRESOLVED (the models disagree; the vendor contract is unknown)
- memory-evidence: Probe crate in `reviews/05/probe` with an exact copy of `src/vendor.rs`. Hashes are in `probe-hashes.txt` and `source-hashes.txt`. The mock vendor stores the pointer in an `AtomicPtr` and obeys the documented contract: one session, the registration thread, may read while active. Tests, run with `cargo +nightly miri test --offline <name>` (nightly miri 0.1.0 48f4b05538 2026-10-23):
  - `lifecycle_no_deref`: attach/drop, no deref. SB ok, TB ok.
  - `read_active_no_move`: vendor reads after `attach` returns, no explicit move. **SB UB**, TB ok.
  - `read_after_move`: the same read after the Session is moved into a Vec. **SB UB**, TB ok.
  - `read_in_unregister`: vendor reads inside `unregister`. SB ok, TB ok.
  - The SB error is "read access using <tag> ... tag does not exist in the borrow stack". The tag was created by a SharedReadWrite retag at `vendor.rs:25` and invalidated by a Unique retag at `vendor.rs:26` (`Self { token, api }`).
  - Logs: `miri.log`, `probe-check.log`. `cargo check --tests` was run before Miri. Native `cargo test` was never run on the probe. The original failing output is kept in `miri.log`.
- aliasing-evidence: At `vendor.rs:25` the raw pointer is derived from a temporary `&mut *token`, and the `Box` is moved at line 26. Under Stacked Borrows a Box move or retag is treated as a Unique retag of the pointee, which pops the raw-derived tag. Every later vendor read through the registered pointer then lacks a valid tag. A heap address that stays put does not make the old pointer usable. The `Drop` impl passes a fresh `&mut *self.token` to `unregister`, so that path is not affected. The pointer registered at attach time is the one the vendor retains. Tree Borrows accepts it; Stacked Borrows rejects it. Both are experimental models, and I chose neither as proof.
  - Closure criteria: (a) the versioned SDK contract says whether the vendor retains and reads the pointer after `register` returns, and when it reaches quiescence; and (b) a design that avoids the retag. A candidate, not tested here, is to hold `NonNull<u64>` from `Box::into_raw` (or `UnsafeCell`/`MaybeUninit` in a `Pin`ned box) and free it via `Box::from_raw` in `Drop` after `unregister`. It must be re-checked in Miri under both models.

## Concurrency
- async-scope: NONE (no async code in the diff; the tokio dependency is unused by it)
- deadlocks: N/A (no async or locks in the diff)
- cancellation: N/A (no async code)
- task-lifecycle: N/A (no tasks)
- async-evidence: N/A, no async or task code changed.
- sync-scope: NONE (no atomics or custom synchronization in the reviewed code; thread affinity is only a documented caller obligation. `Session` holds fn pointers and a `Box<u64>`, so it is auto `Send`/`Sync`, and the single-thread contract is not enforced by the type.)
- loom: N/A (no custom synchronization protocol; the `model` feature was not exercised and is not production)
- synchronization: N/A (no synchronization protocol in the diff)
- model-evidence: N/A, same reason.

## Spec
- spec: PARTIAL (`REQUIREMENTS.md`)
- missing: There are no tests of register/unregister pairing, teardown ordering, move-after-attach, or callback reads. The vendor library and contract are not in the repo, so retention and quiescence cannot be confirmed. No test checks that unregister runs on drop.
- unrequested: `.claude/`, `.github` and the workflow kit files, `CLAUDE.md`, `REVIEW.md` edits (a duplicated "Project policy (configure)" section appeared; harmless) and `vendor.h` (an SDK extract; the Rust code declares no `extern` block and takes `Api` function pointers). These are tooling and documentation, not product code.
- contradictions: The requirement says the Session "owns callback context ... preserving memory safety during teardown". Teardown ordering is fine: `unregister` runs before the Box is freed. During the active period the stored pointer is invalidated under Stacked Borrows by the move at line 26, which contradicts the SAFETY comment "stable callback context owned by this session". The doc comment also says the vendor "is allowed to read it while the session is active".

## Findings
No findings.

## Residual risks
- Escalation detail: no defect is demonstrated under the project's contract, so there is no P1. The unresolved Stacked Borrows UB versus Tree Borrows OK result is at `src/vendor.rs:25-26` (`attach`: pointer derivation, then Box move into `Self`).
- Scope: base `origin/main` = 557bc58; HEAD = c24b33c; the tree was clean per `git status --short` (nothing uncommitted or untracked at review time; the diff is the committed HEAD against base). `src/vendor.rs`, `vendor.h` and the `lib.rs` change are the product code; the 313-file diff is mostly the review kit.
- Unverified: the vendor binary and contract (retention, quiescence, thread affinity, unwinding), and any real FFI behaviour. Miri cannot validate native libraries; the mock obeys the documented contract. The CI workflow calls `.agents/skills/.../gates.sh`, which was not run, and the local `.claude` equivalents were not run through `gates.sh` itself. I ran the commands equivalent to its steps with `--offline`. `nextest` was not used.
- The advisory database was not refreshed (offline). Semver does not apply (unpublished). Native tooling limits: no LSP or graph; clippy's `undocumented_unsafe_blocks` lint was not enabled by the project.
- Edition 2024 with no `unsafe extern` block, since the functions are passed as pointers.
- A `Drop` panic from `unregister` is excluded by the `must not unwind` caller contract.
