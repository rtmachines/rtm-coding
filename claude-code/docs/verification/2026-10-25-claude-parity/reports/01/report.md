## Verdict: REQUEST_CHANGES
Six existing contracts are regressed and `parse_limit` is wrong, all demonstrated by executed probes. The `fee` doctest in the repository also fails. The repository's own unit tests (5/5) and cargo-deny pass, but they do not cover these contracts. Memory and concurrency scopes are not applicable.

## Tooling
- rust-lsp: UNAVAILABLE (no LSP or MCP tool is exposed in this environment, as the task stated. `rust-analyzer` exists at ~/.cargo/bin but no workspace probe was possible.)
- lsp-used: NO
- lsp-evidence: No semantic query was made. code-review-graph was also not exposed, so no graph-first narrowing happened.
- lsp-limitations: Review used Git diff and full source reading. The crate is about 70 lines with no macros or dependencies, so the gap is small.

## Gates
- fmt: PASS (gates.sh, `cargo fmt --all -- --check`)
- clippy: PASS (`-D warnings --all-features --locked`)
- tests: PASS (nextest: 5 run, 5 passed. They do not cover the regressed contracts.)
- doctests: FAIL (`src/lib.rs - fee (line 27)` panicked. Cause: the `fee` change at src/lib.rs:31.)
- deny: PASS (`cargo deny --locked check`, offline. Output: advisories, bans, licenses and sources ok; warning license-not-encountered. The advisory DB is the local copy and may be stale, so freshness is unverified.)
- gates.sh exit status: 1 (see /home/rtm/.cache/rust-review-kit/claude-parity-final-20261025/reviews/01/gates.status, gates.out, gates.err)

## Memory safety
- memory-scope: NONE (no unsafe code or FFI in the diff, and the fixture policy says no Miri gate applies)
- miri: N/A (no unsafe code)
- aliasing: N/A (no pointers or FFI)
- memory-evidence: N/A, same reason as memory-scope. Source hashes are in source.sha256.
- aliasing-evidence: N/A, same reason.

## Concurrency
- async-scope: NONE (no async code)
- deadlocks: N/A (no async or locks)
- cancellation: N/A (no async)
- task-lifecycle: N/A (no tasks)
- async-evidence: N/A, no async code.
- sync-scope: NONE (no synchronization primitives)
- loom: N/A (no custom synchronization)
- synchronization: N/A (none present)
- model-evidence: N/A, no concurrency in the diff.

## Spec
- spec: FAIL (source: /cases/01/REQUIREMENTS.md, the user-supplied requirements)
- missing: `parse_limit` returns None for malformed, negative or out-of-range input: not implemented, it panics. Tenant check, overdraw `None`, Unicode-scalar preview, exact-expiry rejection and `fee` flooring are broken by the diff (see Findings).
- unrequested: none beyond the added `REQUIREMENTS.md` sentence about `u16::from_str` and a leading `+`, which is a clarification.
- contradictions: Each of the six regressed functions contradicts a quoted requirement. Details are in Findings.

## Findings
- [P0] src/lib.rs:10 - `can_read` no longer compares `tenant_id`. Trigger: `can_read({tenant 1, user 7}, {tenant 2, user 7})` returns true. The probe `tenant` failed. Impact: cross-tenant record disclosure. Requirement: "Reading a record requires both matching tenant_id AND matching user_id." Fix: restore `actor.tenant_id == owner.tenant_id && actor.user_id == owner.user_id`.
- [P1] src/lib.rs:14 - `debit` uses `saturating_sub` wrapped in `Some`. Trigger: `debit(10, 20)` returns `Some(0)`. Probe `overdraw` failed. Impact: an overdraw looks like a successful zero balance, so the money-handling invariant is lost. Fix: `balance.checked_sub(amount)`.
- [P1] src/lib.rs:18 - `preview` slices bytes, not chars. Trigger: `preview("héllo", 2)` panics with "byte index 2 is not a char boundary". Probe `multibyte` failed. Impact: panic on valid UTF-8, and a result counted in bytes instead of scalar values. Requirement: no panic on arbitrary UTF-8. Fix: `text.chars().take(max_chars).collect()`.
- [P1] src/lib.rs:22 - `now <= expires_at` accepts a token at the exact expiry instant. Trigger: `token_usable(100, 100)` returns true. Probe `expiry` failed. Impact: expired tokens are accepted (authentication boundary). Fix: `now < expires_at`.
- [P1] src/lib.rs:31 - `fee` divides `amount_cents` by 10_000 first, which floors early. Trigger: `fee(1_999, 250)` returns 0 where 49 is expected. `fee(u32::MAX, u32::MAX)` also gives the wrong value. Probes `fee_small` and `fee_max` failed, and the existing doctest in src/lib.rs fails (gate FAIL). Impact: wrong fees. Fix: `u64::from(amount_cents) * u64::from(basis_points) / 10_000`. This cannot overflow, since u32 x u32 fits in u64.
- [P1] src/limits.rs:2 - `parse_limit` calls `unwrap()` on the parse result. Trigger: `"-1"`, `"65536"`, `"x"` and `""` all panic. Probes `pl_bad_neg`, `pl_bad_range` and `pl_bad_junk` failed. Impact: a public API that must return None panics on untrusted input. Fix: `raw.parse::<u16>().ok()`. This also keeps the `+5` and `65535` cases working, as `pl_ok` shows.
- [P2] src/lib.rs:36 - The tests do not cover the changed contracts. Only the happy paths are tested: no tenant mismatch, overdraw, multibyte, expiry boundary, fee rounding or `parse_limit` tests exist. This is why the 5 unit tests and clippy stay green. Fix: add the probe cases to the repository's tests.

## Residual risks
- Scope: BASE_SHA ff58dc91708bd68170abfefc93bca294034242ac, HEAD 6447d17705375331b6bb3818f14c884e0959e580. The tree is dirty: M REQUIREMENTS.md and M src/lib.rs, with untracked src/limits.rs. All three were reviewed. The base-to-working-tree diff also shows the Claude review-kit files, which are not Rust code under review. Source hashes: source.sha256. The probe copy was a separate directory with its own hashes in probe.sha256. The probe tests were appended to a copy of lib.rs and results are in probe.log. 16 tests ran: 7 passed and 9 failed, all failures as listed in Findings. The reviewed tree was not modified.
- Knowledge base: rust-skills index (rtmachines/rust-skills) was read. vendored.tsv records pin a1e290d53d43a85421ff16dde23b5f8ec0b48539 only for the Codex copy, and I found no line for the Claude copy, so the pin for `.claude/skills/rust-skills` is unconfirmed. Rules read: anti-unwrap-abuse, err-result-over-panic, api-parse-dont-validate. Only a partial reading of the reference documents (SPEC-PASS) was done. SMELLS.md and the other references were not opened because no unsafe or concurrent code is involved.
- Unverified: cargo-deny advisory data freshness (offline). No semver check (publish=false). The LSP/graph limitation is described under Tooling.
