## Verdict: REQUEST_CHANGES
Six reachable contract defects are demonstrated by exact-source probes. Clippy also fails. These are verified failures, not missing-evidence allegations.

## Tooling
- rust-lsp: AVAILABLE (workspace_symbols succeeded in this repository).
- lsp-used: YES (workspace symbol resolution and hover executed).
- lsp-evidence: tools.json records workspace_symbols and graph calls with the explicit repository root; lsp-hover.json records the actual semantic response. Hover at src/service.rs:15 resolved count as MutexGuard<'_, u64>.
- lsp-limitations: Queries are navigation evidence, not proof of runtime safety or downstream behavior.
- Graph: initialized locally, then detect_changes, affected flows and tests_for narrowed review; graph-context.json contains source context for actual Rust changes. Empty tests_for results were checked against actual tests. The graph misidentifies some method-name relationships and omits coverage; source wins.
- Knowledge: rtmachines/rust-skills pinned at a1e290d53d43a85421ff16dde23b5f8ec0b48539, from .agents/rust-review-kit/vendored.tsv. Read its SKILL.md index and these complete rules: unsafe-miri-ci.md, unsafe-safety-comment.md, conc-atomic-ordering.md, async-no-lock-await.md, async-cancel-safety.md, async-joinset-structured.md, test-loom-concurrency.md. Local vendoring notes say index/rules unchanged; LOCAL_CHANGES.md link rewritten. This is the corrected fork, not a newly fetched upstream. Per-file before/after hashes record local content.
- Also consulted rust-pr-review SKILL.md, SMELLS, SPEC-PASS, RUST-LSP and REVIEWDOG; memory/concurrency validation and SAFETY-PRECHECK for applicable paths.

## Gates
- fmt: PASS (fmt.log; exit 0; commands.jsonl).
- clippy: FAIL (clippy.log; exit 101; commands.jsonl).
- tests: PASS (tests.log; exit 0; commands.jsonl).
- doctests: PASS (doctests.log; exit 0; commands.jsonl).
- deny: PASS (deny.log; exit 0; commands.jsonl).

All commands ran offline on existing stable Rust 1.99.1 (versions.log). Features: default for ordinary gates per project policy; model only in Loom probes where applicable. cargo-deny used --locked --offline check with the existing advisory database; this does not establish current online advisory freshness. Reviewdog used raw Clippy output with local reporter and nofilter; its status is independent in status.json. No network/install was used.
Clippy reports boxed_local at src/registration.rs:15 (exit 101); it is not duplicated as a behavioral finding.

## Memory safety
- memory-scope: REQUIRED (bytes::read_word and registration::Registration).
- miri: FAIL (four targeted probes each report UB; miri-short_word.log, miri-unaligned_word.log, miri-retained_buffer.log, miri-unregister.log).
- aliasing: FAIL (allocation liveness, bounds and alignment are violated independently of experimental alias models).
- memory-evidence: memory/src/bytes.rs and registration.rs are exact copies, with hashes in probe-hashes.json matching before.json. Four one-test runs: short_word, unaligned_word, retained_buffer, unregister_retained_buffer. cargo +nightly miri test --offline <name>, strict provenance, existing /home/rtm/.cache/miri sysroot; toolchain/commit in miri-version.log, commands/environment/exit in commands.jsonl. Each run exits 1; external watchdog 120 seconds, no watchdog reached. Suspected UB was executed only under Miri.
- aliasing-evidence: read_word derives a u32 pointer from an arbitrary shared byte slice; nonempty does not prove four accessible bytes or alignment. Its read is invalid for a one-byte allocation and an offset-one slice of an align(4) object. Registration creates a read-only pointer from its owned Box but never transfers the Box into Self; the Box frees at constructor return. Any subsequent allowed consumer read (including unregister) is dangling. The serialized Rust C-ABI shim retains only that pointer, neither writes nor frees it, and synchronously unregisters; it satisfies the documented caller contract. Moving Registration does not retain the allocation. Miri fails on the first post-constructor read, before unregister; a separate unregister_retained_buffer probe also fails inside the unregister callback. This establishes defects without claiming validation of an undisclosed native FFI library. Suggested redesigns below require new liveness and aliasing validation after implementation.

## Concurrency
- async-scope: REQUIRED (Service progress, approved_pop cancellation, stop_worker termination).
- deadlocks: FAIL (increment_progress reaches nested acquisition and times out).
- cancellation: FAIL (cancel_before_approval polls Pending, drops the future and observes an empty queue instead of [7]).
- task-lifecycle: FAIL (stop_prevents_later_effect releases a worker after stop_worker returns and observes its side effect).
- async-evidence: probe/tests/async.rs imports unchanged implementation copied in probe/src. Three targeted tests all fail in async-controlled.log, exit 101 (original async.log retained); Tokio 1.54.1 current-thread runtime, explicit polling/oneshot ordering and a worker-start handshake before shutdown, 50ms progress/effect deadline, 120s process watchdog. No random sleeps establish the cancellation boundary. The deadlock is proven by the held count guard awaiting snapshot's acquisition of the same non-reentrant Mutex, not by the timer alone.
- sync-scope: REQUIRED (Published one-shot publication).
- loom: FAIL (one_shot_publication observes Some(0) after publish(7), loom.log).
- synchronization: FAIL (two relaxed atomics do not publish payload visibility through ready).
- model-evidence: probe/tests/model.rs, feature model, exact publication.rs. Loom 0.7.2 tracked AtomicUsize/AtomicBool and Arc/thread; one writer publishes once and the reader asserts before join that any Some is 7, then asserts after join. Loom default exploration parameters, no explicit preemption/permutation bound, external 120s watchdog. Run completed with a real counterexample before timeout, exit 101; it does not claim exhaustive success. The independent argument: relaxed ready store/load provides no release/acquire happens-before edge for the earlier value store, so observing ready=true need not imply observing value=7. Hashes and commands are in probe-hashes.json and commands.jsonl.

## Spec
- spec: FAIL (REQUIREMENTS.md; all six added contracts have counterexamples).
- missing: Bounds/alignment checks, retained buffer ownership, progress, cancellation preservation, termination barrier and publication ordering.
- unrequested: No unrelated runtime scope found.
- contradictions: The comments claim guarantees that the implementations and targeted probes disprove. Ordinary tests avoid the affected unsafe paths and unbounded waits as requested, but that does not validate the adapters.

## Findings
- [P1] src/bytes.rs:7 - Read requires bounds and alignment the safe API does not ensure. Trigger: a nonempty 1–3 byte allocation or a four-byte slice at an unaligned address. Impact: out-of-bounds or unaligned u32 read is undefined behavior. Fix: validate at least four bytes and decode an exactly sized byte array with from_ne_bytes (or use a separately justified unaligned read). Both violations are reproduced by Miri.
- [P1] src/registration.rs:21 - Retain the allocation until unregister has completed. Trigger: a conforming foreign consumer reads its retained pointer after new returns. Impact: bytes was dropped at constructor return, so the permitted read is use-after-free. Fix: redesign Registration to own the allocation through synchronous unregister, then free exactly once; separately validate moves/reborrows and retained-pointer provenance. The untested candidate ownership change alone is not a completed safety fix.
- [P1] src/service.rs:16 - Do not reacquire count while its guard is live. Trigger: any increment_and_snapshot call. Impact: snapshot waits for the same guard that the caller holds until snapshot finishes, permanently blocking progress. Fix: return the value through the existing guard, or drop it before snapshot if a later snapshot is the intended contract.
- [P1] src/service.rs:25 - Wait for approval before consuming the queue. Trigger: poll approved_pop while approval is pending, then cancel/drop it (or close approval). Impact: the queue item has already been removed and is lost without approval. Fix: await successful approval before pop_front, preserving cancellation behavior until that point.
- [P1] src/service.rs:32 - Dropping a JoinHandle does not stop its worker. Trigger: worker is pending and stop_worker returns, then its input becomes ready. Impact: the detached worker still performs a side effect after the promised termination barrier. Fix: request suitable cancellation and await observed task termination, or cooperatively stop and join; account for nonabortable blocking work if accepted by this API.
- [P1] src/publication.rs:23 - Publish the payload with a release/acquire handoff. Trigger: a concurrent reader sees ready=true before observing value's relaxed store. Impact: snapshot returns Some(0) for publish(7), violating the one-shot contract. Fix: Release-store ready and Acquire-load it in snapshot while retaining the single-writer one-shot invariant; re-run the model. The counterexample respects that invariant.

## Residual risks
- Scope: origin/main fcd0f85b00baa7a8caa47007d8c5d6438e5fac9f to HEAD 4e95a8098ff56532f0f7c76e1ad62f1672b88e2a, including working-tree and untracked scope. Git state is clean; no nonignored untracked files were present. Full diff captured in diff.log; context.log and source-inventory.txt record scope.
- Source integrity: before.json and after.json match (hash-check.txt). Only isolated review probes/evidence and ignored graph/build artifacts were created. No reviewed source or Git state changed.
- Edition 2024; no declared MSRV. Unpublished crate (publish=false), so semver-checks N/A; no release baseline required. Host target only; unsupported targets and online advisory freshness were not verified.
- Priorities are P1 because these are reachable blocking defects in an unpublished helper crate; no demonstrated broad production impact establishes P0. Suggested changes are candidates and were not applied or claimed validated.
