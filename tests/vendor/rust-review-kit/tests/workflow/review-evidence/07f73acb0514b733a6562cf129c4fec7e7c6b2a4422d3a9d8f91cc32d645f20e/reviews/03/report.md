## Verdict: REQUEST_CHANGES
Targeted Miri, async and Loom probes demonstrate blocking defects. Clippy also fails. Ordinary happy-path tests do not cover these transitions.

## Tooling
- rust-lsp: AVAILABLE (analyzer_status loaded /tmp/rust-review-lsp-20261025/cases/03)
- lsp-used: YES (hover resolves service.rs:16 call to Service::snapshot async method)
- lsp-evidence: tools.json retains actual workspace status, semantic hover and graph build/detect/flows/tests queries.
- lsp-limitations: Limited semantic query scope; exact source and targeted runtime probes establish remaining behavior. Initial graph Service query was ambiguous; qualified follow-up and full source inspection covered it.

## Gates
- fmt: PASS (fmt.log exit 0)
- clippy: FAIL (clippy.log exit 101: boxed_local at registration.rs:15; reviewdog.log reports it)
- tests: PASS (tests.log: 2 ordinary tests; additional targeted failures below)
- doctests: N/A (included in cargo test; zero doctests exist, so no documentation behavior was exercised)
- deny: PASS (deny.log exit 0; cached offline database, unmatched license allowance warning)

## Memory safety
- memory-scope: REQUIRED (bytes::read_word and Registration retained buffer)
- miri: FAIL (three separate targeted tests demonstrate out-of-bounds, alignment and use-after-free)
- aliasing: FAIL (access validity and allocation lifetime fail independently of experimental aliasing assumptions)
- memory-evidence: probe/tests/memory.rs: short_word, unaligned_word, registration_retained. Each ran separately under nightly Miri 0.1.0 (48f4b05538 2026-10-23), default MIRIFLAGS, 90s external timeout; each exit 1 with explicit UB, not timeout. Logs miri-short_word.log, miri-unaligned_word.log, miri-registration_retained.log. Source hashes in probe-source-hashes.json match reviewed files.
- aliasing-evidence: read_word derives a u32 pointer from an arbitrary byte slice: its nonempty check proves neither four available bytes nor alignment. Registration derives a read-only pointer from a live Box, but does not transfer ownership to Self; parameter drops at new return, before retained access or unregister. The mock reads only, uses one serialized registration and synchronous unregister; it honors documented caller obligations. No unknown provider promise is needed for the demonstrated failure. A candidate repair must retain ownership through unregister and separately validate pointer provenance across owner moves; this report does not certify a repair.

## Concurrency
- async-scope: REQUIRED (increment, approved_pop, stop_worker)
- deadlocks: FAIL (increment_progress reaches nested acquisition and exceeds 100ms bound)
- cancellation: FAIL (cancellation_keeps_item observes empty queue after pending future dropped)
- task-lifecycle: FAIL (stop_prevents_effect receives 42 after stop returns)
- async-evidence: probe/tests/async_contracts.rs, async-probe.log: 3 tests, 3 failures, exit 101. Tokio 1.54.1 current-thread runtime; explicit manual poll reaches approval await, oneshot signal gates worker effect, 100ms in-runtime deadline and 90s process bound. Increment holds count guard until function return while snapshot waits for that same mutex, establishing a self wait-cycle beyond the observed timeout.
- sync-scope: REQUIRED (Published one-shot atomic protocol)
- loom: FAIL (publication model observes Some(0) after publish(42))
- synchronization: FAIL (ready Relaxed store/load establishes no happens-before edge for value publication)
- model-evidence: probe/tests/model.rs, loom-probe.log exit 101 with counterexample. Exact publication.rs uses its model feature to substitute Loom 0.7.2 AtomicBool/AtomicUsize; Arc and spawned thread also tracked. Two threads, one publish and one snapshot, one-shot/single-writer precondition respected. Default Loom bounds, 90s process bound; stops on concrete counterexample, not exhaustive pass. Relaxed atomics have separate modification orders, so reader can see ready=true and old value=0; candidate release/acquire handshake must be retested.

## Spec
- spec: FAIL (REQUIREMENTS.md and targeted probes)
- missing: Required boundary/cancellation/lifecycle protections are absent.
- unrequested: None beyond broken specified behavior.
- contradictions: All six requested adapter contracts have demonstrated violations below.

## Findings
- [P1] src/bytes.rs:7 - Safe read_word performs an invalid typed read. Trigger: a one-byte allocation or an unaligned four-byte slice. Impact: out-of-bounds or misaligned read, demonstrated separately in Miri. Fix: require four bytes and decode a copied [u8;4] using from_ne_bytes (or a correctly bounded unaligned read).
- [P1] src/registration.rs:21 - Constructor frees the registered buffer on return. Trigger: valid foreign consumer retains and reads the pointer before synchronous unregister. Impact: use-after-free demonstrated by compliant Rust C-ABI mock under Miri. Fix: retain a suitable owner until after unregister; validate both lifetime and provenance of the candidate design.
- [P1] src/service.rs:16 - Increment awaits snapshot while retaining the same mutex guard. Trigger: any increment call. Impact: permanent self-deadlock, confirmed by bounded probe and lock-cycle analysis. Fix: return the updated guard value directly or release the guard before awaiting snapshot.
- [P1] src/service.rs:25 - Dequeue precedes approval. Trigger: poll with a populated queue and pending approval, then cancel or close approval. Impact: queued item disappears despite no approval. Fix: await successful approval before removing the item, preserving cancellation behavior around lock acquisition.
- [P1] src/service.rs:32 - Dropping the join handle detaches the worker. Trigger: worker awaiting a later signal when stop_worker returns. Impact: worker still performs effects; deterministic probe receives 42 afterward. Fix: request cancellation and await termination (or use a cooperative shutdown handshake suitable to worker type).
- [P1] src/publication.rs:23 - Relaxed ready flag does not publish the stored value. Trigger: reader races the one allowed writer. Impact: Some(0) instead of Some(42), found by Loom. Fix: use a release ready store and acquire ready load, then rerun the exact-source model.

## Residual risks
- Scope: origin/main fcd0f85b00baa7a8caa47007d8c5d6438e5fac9f to HEAD 1c9b73664681400c5bbb2f05f72e2c77a01f9846 plus clean working tree, no untracked source. before.json/after.json and git-before.txt/git-after.txt retain source and Git state; no reviewed source edited.
- commands.log logs commands/exits; ordinary checks used default features as required (model is only for Loom). Source copy under probe is exact; harness alone is new. No suspected UB ran natively.
- Offline cargo-deny 0.20.2 uses supported --offline rather than unsupported --disable-fetch. Cached advisories were not refreshed; new advisories unverified. No tools installed. Semver N/A: publish=false. Miri mock verifies wrapper behavior, not an external SDK.
