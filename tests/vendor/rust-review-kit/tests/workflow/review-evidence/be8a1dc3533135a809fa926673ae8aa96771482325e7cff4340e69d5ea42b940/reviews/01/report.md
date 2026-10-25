## Verdict: REQUEST_CHANGES
Six demonstrated contract regressions; the fee doctest fails despite the five happy-path unit tests passing.

## Gates
- fmt: PASS (fmt.log; exit 0)
- clippy: PASS (clippy.log; exit 0)
- tests: PASS (tests.log; exit 0)
- doctests: FAIL (doctests.log; exit 101)
- deny: PASS (deny.log; exit 0)

Five unit tests pass; one fee doctest fails. Six isolated contract probes fail as described below. Equivalent offline gates used; exact commands/statuses are in gates.json. RUST_REVIEWDOG=1, nofilter local reporter, raw Clippy and reviewdog output retained in rust-review-clippy.* directories. Clippy verdict follows its own exit code; all reviewdog presentation statuses are recorded separately.

## Memory safety
- memory-scope: NONE (safe Rust only; no affected unsafe/FFI ownership or provenance boundary)
- miri: N/A (no affected memory boundary)
- aliasing: N/A (no affected memory boundary)
- memory-evidence: N/A (safe operations and standard library ownership)
- aliasing-evidence: N/A (no retained raw pointer or unsafe invariant)

## Concurrency
- async-scope: NONE (no asynchronous code)
- deadlocks: N/A (no async locks)
- cancellation: N/A (no futures)
- task-lifecycle: N/A (no tasks)
- async-evidence: N/A (synchronous operations only)
- sync-scope: NONE (no custom synchronization)
- loom: N/A (no concurrent protocol)
- synchronization: N/A (no shared state protocol)
- model-evidence: N/A (no concurrency boundary)

## Spec
- spec: FAIL (REQUIREMENTS.md, all six contracts assessed independently against current source)
- missing: Correct rejection of invalid parse_limit input; API exists and is exported, but panics.
- unrequested: No added transport/storage/provider/dependency; regressions are the behavioral changes below.
- contradictions: Tenant isolation, overdraft rejection, Unicode scalar preview, strict expiry, final-only fee rounding, and parser failure behavior all contradict requirements.

## Findings
- [P1] src/lib.rs:10 - Restore the tenant guard. Trigger: actor (tenant 1,user 7) reads owner (tenant 2,user 7). Impact: can_read returns true across tenants, violating isolation. Fix: require tenant_id equality AND user_id equality. Exact-source tenant_isolation test fails; introduced in committed changes.
- [P1] src/lib.rs:14 - Preserve insufficient-funds failure. Trigger: debit(1,2). Impact: returns Some(0), allowing an overdraw to be treated as successful. Fix: restore checked_sub and test insufficient funds. Exact-source overdraft test fails; committed regression.
- [P1] src/lib.rs:18 - Slice Unicode scalars instead of bytes. Trigger: preview("éx",1). Impact: panics on a valid UTF-8 string; even a valid byte boundary can truncate to fewer scalars than requested. Fix: chars().take(max_chars).collect(). Exact-source unicode_preview fails; committed regression.
- [P1] src/lib.rs:22 - Exclude the exact expiry instant. Trigger: now == expires_at == 100. Impact: expired token remains usable. Fix: strict less-than comparison and boundary test. Exact-source expiry fails; this regression is in dirty local changes.
- [P1] src/lib.rs:31 - Divide after multiplying the widened values. Trigger: fee(1999,250). Impact: returns 0 instead of 49 by rounding the amount before applying the rate. Fix: multiply u64 conversions then divide by 10_000; the largest u32 product fits u64. Both doctest and fractional_fee fail; committed regression.
- [P1] src/limits.rs:2 - Return None on parse errors. Trigger: malformed text such as "abc" (also negative/out-of-range integers). Impact: public parse_limit panics instead of returning None. Fix: raw.parse::<u16>().ok() and rejection tests. Exact-source invalid_limit fails. This file is untracked but wired into the dirty crate root and included in review.

## Residual risks
- Scope: origin/main base ff58dc91708bd68170abfefc93bca294034242ac; HEAD bccb54098b89b9fd21dc571718f5f0383eef546f; base-to-current working tree including local/untracked files. Dirty src/lib.rs plus untracked src/limits.rs included. Committed vs local attribution is given in each finding. context.log and diff.log retain scope evidence.
- Integrity: before-hashes.json equals after-hashes.json for every original tracked/untracked input. after-status.log preserves Git status. Probe implementation/configuration is byte-identical where used; harness additions are isolated under this review directory.
- Method: repository graph initialized with explicit repo_root, change/flow/tests-for queries and Rust LSP workspace symbol lookup preceded source inspection. graph-lsp.json and graph-review.json retain responses. Empty graph test edges were not treated as proof of no tests; exact source/tests were read.
- Offline freshness: cargo-deny passed using the existing cached advisory database without fetching; this does not establish current online advisory coverage. No dependency/tool installation or external service access. Host-only diagnostics; versions.log records compiler.
- Limitations: Semver checks N/A: unpublished crate (publish=false), no release baseline requested. All manifests edition 2024; no inferred MSRV. 
