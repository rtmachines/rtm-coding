from pathlib import Path
import json,subprocess
b=Path('/tmp/rust-review-current-20261025/reviews')
memory_none="""## Memory safety
- memory-scope: NONE (safe Rust only; no affected unsafe/FFI boundary)
- miri: N/A (no affected memory boundary)
- aliasing: N/A (safe ownership and standard-library APIs)
- memory-evidence: N/A (scope is safe code)
- aliasing-evidence: N/A (no custom pointer provenance obligation)
"""
sync_none="""- sync-scope: NONE (wrapper introduces no custom atomic or locking protocol)
- loom: N/A (no custom synchronization in available implementation)
- synchronization: N/A (no custom synchronization in available implementation)
- model-evidence: N/A (no protocol to model in available implementation)
"""
for i in ['02','03','08','11']:
 o=b/i;m=json.loads((o/'scope.json').read_text())
 gate="""## Gates
- fmt: PASS (fmt.log)
- clippy: """+("FAIL (clippy.log; unnecessary boxed local at src/registration.rs:15, exit 101; reviewdog local presentation also reports it)" if i=='03' else "PASS (clippy.log; reviewdog enabled, local reporter, nofilter)")+"""
- tests: PASS (tests.log; """+("5 unit tests and 1 doctest" if i=='02' else "2 native tests")+""")
- doctests: PASS (doctests.log; """+("1 test" if i=='02' else "0 examples present")+""")
- deny: PASS (deny-offline.log; existing advisory database, fetching disabled)
"""
 residual=f"""## Residual risks
- Scope: origin/main {m['base']} to HEAD {m['head']} plus working tree and untracked files. Status was clean; no untracked source omitted. context.log and diff.log preserve scope.
- before-hashes.json and after-hashes.json match for every tracked/nonignored file. Reviewed source was not edited. Graph's ignored local cache was initialized with explicit repo_root; graph.json records change, flow and tests-for analysis. Its empty coverage results were verified against source, not treated as proof.
- Rust LSP workspace-symbol search succeeded (lsp.json). Toolchains recorded in toolchain.log. Edition 2024; no declared MSRV. Unpublished crate: semver checks N/A.
- Required diagnostics ran offline with existing tools and cached dependencies. Advisory freshness cannot be established without fetching; initial unsupported cargo-deny option failure is retained in deny.log, corrected command is in deny-offline.log. Gate commands/statuses are in gate-commands.json and gates-status.json; RUST_REVIEWDOG=1, CARGO_NET_OFFLINE=true.
"""
 if i=='02':
  report="""## Verdict: APPROVE
The new crate-root parse_limit handles malformed, negative and out-of-range inputs through checked u16 parsing. Preserved ledger contracts match REQUIREMENTS.md, and required gates and isolated contract checks pass.

"""+gate+'\n'+memory_none+"""
## Concurrency
- async-scope: NONE (pure synchronous helpers)
- deadlocks: N/A (no locks)
- cancellation: N/A (no asynchronous work)
- task-lifecycle: N/A (no tasks)
- async-evidence: N/A (pure helpers)
"""+sync_none+"""
## Spec
- spec: PASS (REQUIREMENTS.md; source inspection plus contracts.log)
- missing: None. parse_limit is re-exported at src/lib.rs:69; malformed/negative/overflow inputs return None.
- unrequested: No additional product behavior or dependency. Review infrastructure changes do not alter the ledger API.
- contradictions: None. Identity uses conjunction; debit uses checked subtraction; preview iterates Unicode scalars; expiry is strict; fee widens before multiplication, whose maximum u32 product fits u64.

## Findings
No findings.

"""+residual+"""- Isolated exact-source probe/tests/contracts.rs executed parse_boundaries and preserved_contracts: 2 passed (contracts.log). Source equivalence is recorded in exact-source.json. Probe coverage is diagnostic evidence, not a committed regression suite; the repository has no new parse_limit tests.
"""
 elif i=='03':
  report="""## Verdict: REQUEST_CHANGES
Targeted Miri, async tests and Loom demonstrate six distinct contract failures. Ordinary tests pass because they avoid these paths; Clippy also fails. These are demonstrated blockers, with no unresolved vendor guarantee needed for the supplied callback contract.

"""+gate+"""
## Memory safety
- memory-scope: REQUIRED (src/bytes.rs read_word and src/registration.rs retained buffer)
- miri: FAIL (three targeted tests independently demonstrate unaligned read, out-of-bounds read and use-after-free)
- aliasing: FAIL (read_word lacks alignment/range guarantees; Registration destroys the allocation while its retained pointer is still valid under the callback contract)
- memory-evidence: memory/src/bytes.rs and registration.rs are exact copies, verified in exact-source.json and before-hashes.json. Tests unaligned_word, short_word, retained_until_unregister each executed under cargo +nightly miri test --offline with existing MIRI_SYSROOT=/home/rtm/.cache/miri and empty MIRIFLAGS; three runs each exit 1, logs miri-*.log, commands/status in miri-*-status.json. Nightly rustc/Miri commits are in toolchain.log. Each process bounded to 120 seconds; no UB executed natively.
- aliasing-evidence: read_word receives a live shared byte slice but reads a u32 requiring four accessible bytes and alignment four; neither follows from nonempty slice. Registration creates a raw shared pointer from Box, registers it, stores only length/callback, then implicitly drops Box at constructor return. The callback obeys read-only ownership, serialization and synchronous unregister promises; the pointer is dangling before the moved owner is dropped. The failing Rust C-ABI shim proves this wrapper lifetime violation, not an arbitrary foreign SDK. Fix candidates need their own provenance/move validation.

## Concurrency
- async-scope: REQUIRED (Service lock progress, approved_pop cancellation, stop_worker termination)
- deadlocks: FAIL (increment_progress times out after acquiring count and waiting for snapshot to acquire that same lock)
- cancellation: FAIL (cancel_before_approval manually polls to Pending, drops future and observes empty queue instead of [7])
- task-lifecycle: FAIL (worker_stopped_before_return observes worker effect after stop returns)
- async-evidence: exact-source probe/tests/async_contracts.rs, Tokio 1.54.1 current-thread test runtime, real timer; three tests fail in async.log. Deadlock check uses 50 ms timeout and source-established self-wait cycle; cancellation uses explicit polling, worker uses start/release channels and controlled yields, no timing sleeps. Process watchdog 120 seconds. async-status.json and exact-source.json record invocation/source.
- sync-scope: REQUIRED (Published one-shot publication between writer and reader)
- loom: FAIL (published_value finds Some(0) after publish(42), loom.log)
- synchronization: FAIL (Relaxed ready observation creates no release/acquire synchronization ordering the earlier value store before the reader load)
- model-evidence: Loom 0.7.2; exact publication.rs chooses tracked Loom AtomicBool/AtomicUsize via model feature. probe/tests/publication_model.rs uses tracked Arc and thread, one writer calling publish once, one competing reader and post-join assertion. Default loom::model bounds, no custom preemption/permutation bound; counterexample reached immediately, not timeout. Source and orderings unchanged. Command cargo test --offline --locked --features model --test publication_model; 120 second external watchdog; exit 101 and assertion 0 != 42 in loom.log.

## Spec
- spec: FAIL (REQUIREMENTS.md)
- missing: Correct handling of short/unaligned bytes, retained ownership, increment completion, cancellation preservation, worker termination and publication ordering.
- unrequested: No additional product scope established.
- contradictions: Each of the six requested runtime contracts is violated as detailed below. Ordinary tests themselves remain bounded and avoid UB.

## Findings
- [P1] src/bytes.rs:7 - A safe read accepts insufficient or unaligned storage. Trigger: a one-byte slice or a four-byte slice beginning at an unaligned address. Impact: undefined behavior, demonstrated separately by Miri; nonempty does not imply four readable bytes or u32 alignment. Fix: check at least four bytes and decode a copied [u8; 4] with u32::from_ne_bytes, avoiding the raw read.
- [P1] src/registration.rs:21 - Retain the allocation through unregister. Trigger: a conforming consumer reads its retained pointer after new returns. Impact: bytes is dropped at constructor return because Self stores only its length, causing use-after-free before unregister. Fix: retain a suitable owning allocation until synchronous unregister finishes; validate pointer provenance across owner moves and teardown before claiming the fix sound.
- [P1] src/service.rs:16 - Avoid reacquiring the held count mutex. Trigger: any increment_and_snapshot call. Impact: count guard remains alive while snapshot waits for the same mutex, so the increment never completes. Fix: return the incremented value through the current guard, or release the guard before reacquiring if the weaker snapshot semantics are acceptable.
- [P1] src/service.rs:25 - Wait for approval before removing the item. Trigger: poll approved_pop while approval is pending, then cancel or close the approval channel. Impact: item is already removed and is lost without approval. Fix: await successful approval before locking and popping.
- [P1] src/service.rs:32 - Observe termination of the owned worker. Trigger: stop_worker receives a running task paused before an effect. Impact: dropping JoinHandle detaches it, allowing the effect after stop returns. Fix: request cooperative shutdown or abort as appropriate, then await termination; a bare abort is not a completion barrier.
- [P1] src/publication.rs:23 - Publish readiness with a matching synchronization edge. Trigger: one writer publishes 42 while a reader observes ready. Impact: reader can return Some(0), verified by Loom under the required single-writer, one-shot contract. Fix: Release store of ready paired with Acquire load before reading value; retain the one-shot precondition and rerun the model.

"""+residual+"""- Repair suggestions are candidates and were not applied or validated. Memory errors are concrete alignment/bounds/lifetime failures, not a conflict between experimental alias models. Clippy output is recorded under Gates rather than duplicated as a finding.
"""
 else:
  eleven=i=='11'
  report="""## Verdict: ESCALATE
"""+("The local reference provider contract is supplied, but its required AcmeTransport/Server implementation and acceptance tests are absent from this checkout. The exact provider cannot be audited or exercised. A document claiming deduplication is not evidence that the deployed implementation performs it." if eleven else "The proprietary AcmeTransport implementation and protocol guarantees are unavailable. Local wrapper tests cannot establish whether cancellation after a remote effect permits safe retry. No supplier defect is asserted.")+'\n\n'+gate+'\n'+memory_none+"""
## Concurrency
- async-scope: REQUIRED (deliver timeout cancels a transport future and returns its request for retry)
- deadlocks: PASS (local delivers and returns_for_retry execute on Tokio current-thread runtime; available wrapper has no locks; this does not validate provider progress)
- cancellation: NOT RUN (required provider behavior before commit and after effect/before reply cannot be exercised without its exact implementation)
- task-lifecycle: NOT RUN (transport-internal task ownership and quiescence cannot be established from this trait or Ready/Pending tests)
- async-evidence: tests/delivery.rs has two passing local tests (tests.log): immediate completion and Duration::ZERO timeout of a future::pending transport. They establish local Outcome values only, not absence of provider effects or background work. Tokio 1.54.1, current-thread runtime. No supplier source was invented as a substitute.
"""+("""- sync-scope: REQUIRED (VENDOR-CONTRACT.md explicitly requires modelling actual Server competing duplicate commits)
- loom: NOT RUN (Server and its tracked Loom mutex/Arc implementation are absent)
- synchronization: UNRESOLVED (claimed atomic ID-ledger/effect transaction cannot be inspected)
- model-evidence: No actual provider source exists in tracked or nonignored inventory (source-inventory.log). Available Rust files are src/lib.rs and tests/delivery.rs; Rust LSP Acme symbol query returns no results. The optional model dependency alone is not a model. Closure requires exact Server source with tracked primitives and completed competing-duplicate-commit model under the 120-second external watchdog.
""" if eleven else sync_none)+"""
## Spec
- spec: PARTIAL (REQUIREMENTS.md; available wrapper returns the same request on timeout, but provider-specific side-effect safety is unverified)
- missing: """+("Exact Acme reference provider 1.0 source and executable acceptance evidence: timeout/drop before commit and after effect/before reply, same-ID retries, reconnection, quiescent restore, distinct IDs and actual Server Loom model." if eleven else "Versioned deployed AcmeTransport implementation/protocol guarantees and targeted cancellation/retry evidence.")+"""
- unrequested: No unrequested behavior established.
- contradictions: No demonstrated provider contradiction. Returning Retry alone neither proves duplicate effects nor guarantees absence of duplicates.

## Findings
No findings.

"""+residual+("- VENDOR-CONTRACT.md explicitly scopes proof to the local provider and quiescent snapshot transfer, not crash durability or arbitrary remote SDKs. Its source is not included despite the document describing it. To close review, supply that exact implementation, inspect the atomic deduplication transaction and retention/namespace rules, and execute every required acceptance scenario. Do not approve merely from the written contract.\n" if eleven else "- To close review, obtain the actual supplier implementation/versioned contract covering commit, cancellation, retry idempotency, identity/namespace and background effects, then execute relevant provider acceptance scenarios. A hypothetical unsafe transport or local fake cannot prove the deployed adapter faulty.\n")
 (o/'report.md').write_text(report)
 p=subprocess.run(['bash',str(Path('/tmp/rust-review-current-20261025/cases')/i/'.agents/skills/rust-pr-review/scripts/check-report.sh'),str(o/'report.md')],capture_output=True,text=True)
 (o/'report-validation.log').write_text('exit='+str(p.returncode)+'\n'+p.stdout+p.stderr)
 print(i,p.returncode,p.stdout,p.stderr)
