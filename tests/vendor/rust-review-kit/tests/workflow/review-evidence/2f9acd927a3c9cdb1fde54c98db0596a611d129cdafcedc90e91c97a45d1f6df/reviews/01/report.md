## Verdict: REQUEST_CHANGES
Six reachable contract violations were confirmed in exact-source isolated tests. The fee doctest also fails.

## Tooling
- rust-lsp: AVAILABLE (successful actual workspace semantic queries)
- lsp-used: YES (workspace_symbols and hover)
- lsp-evidence: `tool-evidence.json` and `lsp-hover.json`; workspace `/tmp/rust-skills-review-20261025/cases/01`. Hover resolved `src/limits.rs:1` to `parse_limit(&str) -> Option<u16>` including the untracked module.
- lsp-limitations: Queries confirm these symbols/types, not soundness or model completeness. Full source/test inspection and diagnostics supply the remaining analysis; no unsupported rename or edits used.
- Graph: initialized per-repository; detect_changes, affected flows, tests_for and explicit-file review context recorded in `tool-evidence.json` / `graph-context.json`. Graph tests_for returned no matches despite source tests; graph emptiness was not used to infer missing coverage. Explicit context includes relevant runtime paths and untracked code where applicable.
- Rust knowledge: bundled `rtmachines/rust-skills` revision `a1e290d53d43a85421ff16dde23b5f8ec0b48539`, verified against `.agents/rust-review-kit/vendored.tsv`; actual consulted rule paths/hashes are in `rules-read.json`. Vendoring documents a rewritten LOCAL_CHANGES regression link, otherwise the rules are the pinned subset. No local review modifications.
- Rules consulted: `.agents/skills/rust-skills/rules/num-overflow-explicit.md`, `.agents/skills/rust-skills/rules/num-saturating-clamp.md`, `.agents/skills/rust-skills/rules/err-result-over-panic.md`, `.agents/skills/rust-skills/rules/conv-fromstr-parsing.md`. Their general guidance was subordinated to the explicit requirements; no rule priority was converted directly into a finding severity.

## Gates
- fmt: PASS (`fmt.log`, exit 0; exact command in `commands.json`)
- clippy: PASS (`clippy.log`, exit 0; exact command in `commands.json`)
- tests: FAIL (`tests.log`, exit 101; exact command in `commands.json`)
- doctests: FAIL (`doctests.log`, exit 101; exact command in `commands.json`)
- deny: PASS (`deny.log`, exit 0; exact command in `commands.json`)

Stable Rust 1.99.1, edition 2024, no declared MSRV. All checks use offline, locked Cargo resolution; no network or installations. Default features used (01 has no features; equivalent to all-features); optional model checked separately. Reviewdog read raw uncolored Clippy output, nofilter/local reporter, exit 0 (`reviewdog.log`); empty output does not substitute for Clippy's independently captured exit. Cargo-deny used `cargo deny --locked --offline check`; advisory freshness is limited to the installed local database. Semver checks N/A: unpublished crate, no release baseline policy.

## Memory safety
- memory-scope: NONE (safe Rust only; no affected unsafe/FFI ownership or provenance boundary)
- miri: N/A (no affected memory boundary)
- aliasing: N/A (no affected unsafe aliasing obligation)
- memory-evidence: N/A; inspected all runtime source and tests, not merely added unsafe tokens.
- aliasing-evidence: N/A; ownership uses safe Rust APIs only.

## Concurrency
- async-scope: NONE (no async work or task ownership in affected implementation)
- deadlocks: N/A (no locks/async waits)
- cancellation: N/A (no cancellable operation)
- task-lifecycle: N/A (no owned worker)
- async-evidence: N/A for the source scope above.
- sync-scope: NONE (no custom shared-state protocol)
- loom: N/A (no affected concurrency)
- synchronization: N/A (no shared state)
- model-evidence: N/A for the source scope above.

## Spec
- spec: FAIL (REQUIREMENTS.md; six explicit contracts violated)
- missing: required malformed-input None behavior; implementation exists and is re-exported but panics.
- unrequested: no new transport/storage/provider/dependency; none otherwise found.
- contradictions: tenant equality dropped, overdraw accepted, Unicode scalar boundary replaced with byte slicing, expiry instant accepted, fee rounded early, invalid parse panics. See findings.

## Findings
- [P1] src/lib.rs:10 - Restore tenant equality in can_read. Trigger: actor (tenant=1,user=7) and owner (tenant=2,user=7). Impact: cross-tenant access is permitted despite the two-part identity contract. Fix: require both tenant_id and user_id equality. `tenant_isolation` fails.
- [P1] src/lib.rs:14 - Reject insufficient funds instead of saturating. Trigger: debit(1,2). Impact: returns Some(0), reporting a successful overdraw instead of None. Fix: checked_sub. `overdraw_rejected` fails.
- [P1] src/lib.rs:18 - Count Unicode scalars instead of bytes. Trigger: preview("éclair",1). Impact: valid UTF-8 panics because byte 1 is inside é; some other multi-byte prefixes silently undercount characters. Fix: chars().take(max_chars).collect(). `unicode_preview` fails.
- [P1] src/lib.rs:22 - Exclude the expiry instant. Trigger: now==expires_at (100,100). Impact: expired token remains usable contrary to now < expires_at. Fix: strict less-than. `expiry_exclusive` fails.
- [P1] src/lib.rs:31 - Multiply before flooring. Trigger: fee(1999,250). Impact: returns 0 rather than 49 cents; early division discards the amount remainder. Fix: widen both u32 operands to u64, multiply, then divide by 10000; the product fits u64. `fractional_fee` and the existing doctest fail. This is one root cause, not a separate doctest finding.
- [P1] src/limits.rs:2 - Return None for failed parse. Trigger: invalid string, negative value or value above u16::MAX. Impact: unwrap panics instead of returning None. Fix: raw.parse::<u16>().ok(). The module is untracked but included and publicly re-exported in the reviewed worktree; `malformed_limit` demonstrates the invalid-string failure. Negative/range cases follow the same Err/unwrap path by source inspection.

## Residual risks
- Scope: origin/main `ff58dc91708bd68170abfefc93bca294034242ac` -> HEAD `0e384d5a72907d912cdb74a722dcfda02e9ac633` plus all local changes. Dirty tracked `src/lib.rs` and untracked `src/limits.rs` included; nothing untracked excluded from application review. Full tracked diff saved in `diff.log`; context and initial status in `context.log`.
- `hashes-before.json` and `hashes-after.json` match for every pre-existing tracked/untracked file. Git/source state was not changed. Generated graph/build caches are ignored or outside the repository. Probe-source mappings verify exact source copies; only harness files and reduced memory-probe manifest differ.
- Review evidence is fresh for this working tree, not historical reports or expected verdicts. Supporting vendored knowledge was consulted selectively as the review skill requires; not all 265 general rules were applied.
- Existing offline advisory database can miss later advisories; no live freshness claim. Native target is x86_64 Linux; no other platform or unspecified MSRV was validated.
