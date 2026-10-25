## Verdict: REQUEST_CHANGES
Six confirmed public contract regressions; failing fee doctest and eight isolated boundary tests block merge.

## Tooling
- rust-lsp: AVAILABLE (analyzer_status loaded this workspace successfully).
- lsp-used: YES (hover and references returned meaningful semantic results).
- lsp-evidence: tools.json records analyzer_status for /tmp/rust-review-lsp-20261025/cases/01, hover at src/limits.rs:2 resolving Result<u16, ParseIntError>::unwrap and its panic contract, and references for fee resolving its definition and unit test.
- lsp-limitations: Queries cover parsing and fee; all other functions and tests were inspected directly. Graph build parsed seven files, detect_changes found five modified functions, affected flows and tests_for returned empty; source inspection found five tests, so empty graph coverage is not authoritative.

## Gates
- fmt: PASS (fmt.log, exit 0).
- clippy: PASS (clippy.log, exit 0; reviewdog.log exit 0).
- tests: PASS (tests.log: five existing unit tests executed).
- doctests: FAIL (doctests.log: fee example returned 0 instead of 49, one test failed).
- deny: PASS (deny-offline.log, exit 0; offline cached advisory data).

## Memory safety
- memory-scope: NONE (safe arithmetic/string/parsing code; no unsafe or FFI).
- miri: N/A (project policy excludes safe-only fixture).
- aliasing: N/A (no affected unsafe boundary).
- memory-evidence: N/A safe source inspection.
- aliasing-evidence: N/A safe ownership only.

## Concurrency
- async-scope: NONE (all functions synchronous and stateless).
- deadlocks: N/A (no locks).
- cancellation: N/A (no futures).
- task-lifecycle: N/A (no tasks).
- async-evidence: N/A synchronous source inspected.
- sync-scope: NONE (no custom synchronization).
- loom: N/A (no synchronization protocol).
- synchronization: N/A (no synchronization protocol).
- model-evidence: N/A no concurrency code.

## Spec
- spec: FAIL (REQUIREMENTS.md explicitly defines all six contracts).
- missing: Required malformed-input behavior for parse_limit is absent; crate-root export is present.
- unrequested: No additional product scope.
- contradictions: Tenant matching, overdraft rejection, Unicode scalar preview, exact expiry, fee rounding and parse failure behavior all violate requirements.

## Findings
- [P1] src/lib.rs:10 - Restore tenant isolation. Matching user IDs in different tenants now grants access, proven by tenant_isolation. Require both tenant_id and user_id equality as at the base.
- [P1] src/lib.rs:14 - Reject overdrafts. debit(1,2) returns Some(0), falsely reporting success rather than None. Restore checked_sub and test insufficient funds.
- [P1] src/lib.rs:18 - Slice by Unicode scalars. preview("éx",1) panics inside a UTF-8 scalar; byte slicing also undercounts multi-byte characters even at valid boundaries. Restore chars().take(max_chars).collect().
- [P1] src/lib.rs:22 - Expire at the boundary. token_usable(100,100) returns true despite exact expiry being expired. Restore strict less-than.
- [P1] src/lib.rs:31 - Multiply before flooring. fee(1999,250) returns 0 instead of 49; early integer division discards cents. Multiply both operands as u64 then divide by 10_000; maximum u32 product fits u64.
- [P1] src/limits.rs:2 - Return None on parse errors. The new untracked implementation panics for "x", "-1" and "65536", violating the public Option contract. Replace unwrap with .ok().

## Residual risks
- Scope: origin/main ff58dc91708bd68170abfefc93bca294034242ac through HEAD 3a9dc4dfef77375c2058ebe74e7afda0b365f869 plus dirty src/lib.rs and untracked src/limits.rs. Context and full diff are in context.log/after-git.log.
- before.json and after.json match for all tracked and nonignored untracked files. Probe sources are exact copies under probe/; check.rs adds eight independent failing regression tests. probe.log: 13 executed, five existing pass, eight new fail; rustc --edition=2024 --test check.rs followed by timeout 20 ./check, exit 101.
- No tool installation or reviewed source edits. No semver gate: unpublished crate. No external service calls. cargo-deny 0.20.2 rejects --disable-fetch (deny.log, exit 2); documented --offline equivalent disables all fetches and was used successfully. Advisory database freshness is limited to existing offline cache. Only the host target and all-features configuration were tested.
