## Verdict: ESCALATE
The retained pointer fails Stacked Borrows but passes Tree Borrows on identical source. Ownership is live, but provenance across Box moves remains unresolved; do not approve on the passing model alone. Async and publication checks passed.

## Tooling
- rust-lsp: AVAILABLE (successful actual workspace semantic queries)
- lsp-used: YES (workspace_symbols and hover)
- lsp-evidence: `tool-evidence.json` and `lsp-hover.json`; workspace `/tmp/rust-skills-review-20261025/cases/04`. Hover resolved `src/registration.rs:14` to the unsafe constructor with Box ownership and callback contract.
- lsp-limitations: Queries confirm these symbols/types, not soundness or model completeness. Full source/test inspection and diagnostics supply the remaining analysis; no unsupported rename or edits used.
- Graph: initialized per-repository; detect_changes, affected flows, tests_for and explicit-file review context recorded in `tool-evidence.json` / `graph-context.json`. Graph tests_for returned no matches despite source tests; graph emptiness was not used to infer missing coverage. Explicit context includes relevant runtime paths and untracked code where applicable.
- Rust knowledge: bundled `rtmachines/rust-skills` revision `a1e290d53d43a85421ff16dde23b5f8ec0b48539`, verified against `.agents/rust-review-kit/vendored.tsv`; actual consulted rule paths/hashes are in `rules-read.json`. Vendoring documents a rewritten LOCAL_CHANGES regression link, otherwise the rules are the pinned subset. No local review modifications.
- Rules consulted: `.agents/skills/rust-skills/rules/unsafe-safety-comment.md`, `.agents/skills/rust-skills/rules/mem-drop-order.md`, `.agents/skills/rust-skills/rules/async-cancel-safety.md`, `.agents/skills/rust-skills/rules/async-no-lock-await.md`, `.agents/skills/rust-skills/rules/async-joinset-structured.md`, `.agents/skills/rust-skills/rules/conc-atomic-ordering.md`, `.agents/skills/rust-skills/rules/test-loom-concurrency.md`. Their general guidance was subordinated to the explicit requirements; no rule priority was converted directly into a finding severity.

## Gates
- fmt: PASS (`fmt.log`, exit 0; exact command in `commands.json`)
- clippy: PASS (`clippy.log`, exit 0; exact command in `commands.json`)
- tests: PASS (`tests.log`, exit 0; exact command in `commands.json`)
- doctests: PASS (`doctests.log`, exit 0; exact command in `commands.json`)
- deny: PASS (`deny.log`, exit 0; exact command in `commands.json`)

Stable Rust 1.99.1, edition 2024, no declared MSRV. All checks use offline, locked Cargo resolution; no network or installations. Default features used for ordinary gates; optional model checked separately. Reviewdog read raw uncolored Clippy output, nofilter/local reporter, exit 0 (`reviewdog.log`); empty output does not substitute for Clippy's independently captured exit. Cargo-deny used `cargo deny --locked --offline check`; advisory freshness is limited to the installed local database. Semver checks N/A: unpublished crate, no release baseline policy.

## Memory safety
- memory-scope: REQUIRED (`src/registration.rs:14-34`, retained foreign read-only pointer across constructor return, owner moves and deregistration)
- miri: FAIL (Stacked Borrows retained-pointer test failed; Tree Borrows passed both tests; disagreement remains unresolved)
- aliasing: UNRESOLVED (live/stable Box allocation does not establish validity of an earlier pointer after Box moves)
- memory-evidence: `memory-probe/` copies exact bytes.rs and registration.rs, changing only the probe crate root/manifest and adding tests. `retained_after_move_and_during_unregister` constructs a registration, moves it into a Box, calls len, reads via retained pointer, then deregisters; `unaligned_and_short` checks offset input and lengths 0..3. Nightly Miri 0.1.0 commit 48f4b05538 (2026-10-23), existing `/home/rtm/.cache/miri` sysroot. Default MIRIFLAGS: retained-pointer test fails at the first post-move read (subsequent tests not established by this run). `-Zmiri-tree-borrows`: both tests pass, including unregister-time access. Commands, exit statuses and raw logs: `miri-stacked-command.json`, `miri-tree-command.json`, `miri-stacked.log`, `miri-tree.log`. 120-second watchdog; neither timed out. Source hashes recorded with the harness mapping.
- aliasing-evidence: pointer is created by `bytes.as_ptr()` at registration.rs:20, retained without writes/free by a serialized C-ABI Rust callback. The Box is moved into Self at line 21, returned and moved into the harness Box. Stacked Borrows reports the line-21 Unique retag invalidating the earlier SharedReadOnly tag; Tree Borrows accepts the same read. No free precedes unregister: Drop calls unregister before field destruction, and no public mutable buffer access exists. That proves liveness, not provenance. The callbacks obey the unsafe API's documented read-only, serialized, synchronous-quiescence contract; this is not evidence about any unspecified native vendor. Closure requires a justified provenance argument for this ownership pattern or a separately validated redesign with both model results reconciled. No tested fix is claimed.

## Concurrency
- async-scope: REQUIRED (Service lock progress, approved_pop cancellation, owned worker stop)
- deadlocks: PASS (targeted `progress` test completes increment and subsequent snapshot within one second)
- cancellation: PASS (`cancel_before_approval_and_at_lock` drops pending futures at both awaits, preserves queue, and checks closed approval)
- task-lifecycle: PASS (`stop_observes_destructor_and_prevents_effect` handshakes worker readiness, verifies destructor completion before stop returns and prevents later signaled effect)
- async-evidence: exact source copy in `probe/`; 3 targeted tests in `probe/tests/transitions.rs`, Tokio 1.54.1 current-thread runtime, explicit polling/oneshot handshakes, 1-second timer where applicable and external 120-second process limit. `transitions.log` and `transitions-command.json`; all pass. Service releases its first mutex guard before snapshot reacquires. approved_pop has no removal before approval and no await after removal. stop_worker aborts then awaits termination; dropping its own supervisor before completion is outside the return guarantee. Await also waits for running spawn_blocking work rather than asserting abort stops it.
- sync-scope: REQUIRED (Published value/ready handoff)
- loom: PASS (one non-vacuous model completed, not a capped sample)
- synchronization: PASS (Release/Acquire publication argument)
- model-evidence: `probe/tests/publication_model.rs` imports the exact copied implementation using feature model, Loom 0.7.2 tracked AtomicUsize, AtomicBool, Arc and thread. One writer stores 42 and one reader asserts every pre-join Some equals 42, then post-join Some(42). max_threads=3, max_branches=1000, no permutation, time or preemption limit; external 120-second watchdog not reached. `loom.log`, `loom-command.json`; completed exit 0. Payload store precedes ready Release; true Acquire observes that release, placing the payload store before its Relaxed load. One-shot precondition excludes subsequent competing payload writes. This does not claim every C11 behavior is modeled.

## Spec
- spec: PARTIAL (REQUIREMENTS.md available; safe decoding, progress, cancellation, stop and publication validated; retained-buffer aliasing unresolved)
- missing: a resolved provenance justification for the retained pointer across Box movement, not evidence that storage was freed early.
- unrequested: none found in runtime changes.
- contradictions: no definite additional contract violation established; experimental alias-model disagreement requires escalation.

## Findings
No findings.

The aliasing question at src/registration.rs:20-21 is an unresolved safety blocker detailed above, not a claimed universally proven use-after-free.

## Residual risks
- Scope: origin/main `007e8d5210660d3bdc54d78b49d6100f8ff2b399` -> HEAD `d9a1e28c9110bf324194f859d545a322e608724c` plus all local changes. Worktree clean; no untracked application files. Full tracked diff saved in `diff.log`; context and initial status in `context.log`.
- `hashes-before.json` and `hashes-after.json` match for every pre-existing tracked/untracked file. Git/source state was not changed. Generated graph/build caches are ignored or outside the repository. Probe-source mappings verify exact source copies; only harness files and reduced memory-probe manifest differ.
- Review evidence is fresh for this working tree, not historical reports or expected verdicts. Supporting vendored knowledge was consulted selectively as the review skill requires; not all 265 general rules were applied.
- Existing offline advisory database can miss later advisories; no live freshness claim. Native target is x86_64 Linux; no other platform or unspecified MSRV was validated.
