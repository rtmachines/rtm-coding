from pathlib import Path
import json,re
root=Path('/tmp/rust-review-current-20261025')
none_memory='''## Memory safety
- memory-scope: NONE (safe Rust only; no affected unsafe/FFI ownership or provenance boundary)
- miri: N/A (no affected memory boundary)
- aliasing: N/A (no affected memory boundary)
- memory-evidence: N/A (safe operations and standard library ownership)
- aliasing-evidence: N/A (no retained raw pointer or unsafe invariant)
'''
none_async='''- async-scope: NONE (no asynchronous code)
- deadlocks: N/A (no async locks)
- cancellation: N/A (no futures)
- task-lifecycle: N/A (no tasks)
- async-evidence: N/A (synchronous operations only)
'''
none_sync='''- sync-scope: NONE (no custom synchronization)
- loom: N/A (no concurrent protocol)
- synchronization: N/A (no shared state protocol)
- model-evidence: N/A (no concurrency boundary)
'''
contents={}
contents['01']=('REQUEST_CHANGES','Six demonstrated contract regressions; the fee doctest fails despite the five happy-path unit tests passing.',none_memory,'## Concurrency\n'+none_async+none_sync,'''## Spec
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
''')
contents['04']=('ESCALATE','Ordinary gates and targeted async/publication checks pass. Registration has conflicting alias-model results: Stacked Borrows rejects retained-pointer access after the Box move while Tree Borrows accepts it. This unresolved provenance obligation blocks approval.', '''## Memory safety
- memory-scope: REQUIRED (Registration retains a pointer across Box ownership moves and Drop callbacks)
- miri: FAIL (default Stacked Borrows diagnostic in miri-stacked.log; identical test passes Tree Borrows in miri-tree.log)
- aliasing: UNRESOLVED (experimental models disagree; allocation liveness alone does not prove pointer validity)
- memory-evidence: One exact-source test retained_read_after_return_move_and_unregister, in probe/tests/memory.rs. Commands in miri-stacked-status.json and miri-tree-status.json; nightly rustc/Miri 1.101.0-nightly commit 48f4b05538b8eca412137042d9647a61e692c6b3 (2026-10-23), existing MIRI_SYSROOT=/home/rtm/.cache/miri, MIRIFLAGS empty versus -Zmiri-tree-borrows. Each process bounded at 120 seconds. No native UB run. Source equality recorded in probe-source-hashes.json against before-hashes.json.
- aliasing-evidence: bytes.as_ptr() at src/registration.rs:20 derives the retained read-only pointer. Moving bytes into Self at :21 keeps allocation/address alive but gives a Unique retag under Stacked Borrows, invalidating the shared tag before the first post-return read. The test also covers a later owner move, safe len access, and read during unregister; Tree Borrows reaches all of them. Drop invokes unregister before automatic Box free, so the lifetime/free ordering is correct under the documented synchronous no-write/no-free, serialized callback contract. Rust extern-C callbacks obey that contract and stop reads before return; they do not validate an arbitrary foreign provider. Need a justified provenance argument resolving the model discrepancy or a separately validated representation redesign. No tested fix is claimed.
''','''## Concurrency
- async-scope: REQUIRED (Service lock progress, approved_pop cancellation, stop_worker termination)
- deadlocks: PASS (progress_and_later_snapshot completes competing increments then snapshot within one-second Tokio timeout)
- cancellation: PASS (cancellation_and_channel_closure_preserve_queue polls pending before approval and while waiting for queue lock, drops futures, checks queue; closed approval consumes nothing)
- task-lifecycle: PASS (stop_observes_destructor_and_prevents_effects handshakes to a known suspended worker, stops it, checks destructor ran and later effect signal cannot reach worker)
- async-evidence: probe/tests/targeted.rs; targeted.log and targeted-status.json, three targeted async tests plus alignment_and_short_input all pass on Tokio 1.54.1 current-thread runtime. Controlled polls/oneshots, one-second local progress deadlines, 120-second external process watchdog. Exact source/manifests/lockfile copied unchanged; probe-source-hashes.json. Guard block ends before snapshot awaits; approved_pop mutates only after approval and acquiring queue; abort is followed by JoinHandle await.
- sync-scope: REQUIRED (one-shot Published release/acquire protocol)
- loom: PASS (publication_model completes without permutation/time/preemption truncation)
- synchronization: PASS (value.store Relaxed precedes ready.store Release; an Acquire load observing true synchronizes with the unique release, so subsequent Relaxed value load must see the only published value; false may return None. One writer/one publish is the explicit precondition.)
- model-evidence: probe/tests/model.rs imports exact src/publication.rs with feature model selecting Loom 0.7.2 tracked AtomicUsize/AtomicBool, Arc and thread. Main reader competes with one writer, checks every Some equals 42 and post-join Some(42). max_threads=3 (two active), max_branches=1000, no permutation/duration/preemption bound; model.log exit 0 before 120-second external watchdog. Source hashes preserved; command in model-status.json. This finite protocol model does not cover Tokio runtime scheduling.
''','''## Spec
- spec: PARTIAL (REQUIREMENTS.md: five behavioral contracts validated; Registration ownership/lifetime structure meets the requested shape but retained-pointer alias validity remains unresolved)
- missing: A resolved provenance justification for Registration; there were no shipped targeted async/memory/model tests, supplemented by authorized exact-source probes.
- unrequested: No extra functional subsystem identified.
- contradictions: No definitive functional contract contradiction established; alias-model disagreement is an escalation, not a proven portable unsoundness finding.

## Findings
No findings.
''')
contents['07']=('ESCALATE','Publication ordering has a coherent invariant argument, but the only allowed Loom invocation explores at most one permutation. The passing process is incomplete synchronization evidence, not completed model validation.',none_memory,'## Concurrency\n'+none_async+'''- sync-scope: REQUIRED (Published one-writer, one-shot atomic publication)
- loom: NOT RUN (for the approval gate: execution happened and passed, but exploration was truncated at the mandated one-permutation budget)
- synchronization: PASS (the value Relaxed store precedes ready Release; an Acquire read of true synchronizes with it, so the following value read observes the unique publication; readers observing false return None)
- model-evidence: tests/publication_model.rs uses actual Published with Loom 0.7.2 AtomicBool/AtomicUsize plus tracked Arc/thread, one writer and one reader, asserts Some equals 42 and post-join Some(42). model.log and model-status.json record the single permitted invocation with feature model, exit 0, 120-second external watchdog. checkpoint_interval=1, max_permutations=Some(2), max_duration=None, preemption_bound=None; Loom 0.7.2 starts i=1 and returns before executing i=2 at src/model.rs:178-180. Default branch bound remains 1000 and max_threads 5; only two active threads. A process success under this early-return limit is not proof exploration completed. No increased limit, alternate probe or aggregate rerun was attempted. before/after hashes are identical.
''','''## Spec
- spec: PARTIAL (REQUIREMENTS.md behavioral contract supported by source ordering argument; required model exploration remains incomplete)
- missing: Completed model evidence across the publication/read interleavings under an authorized execution budget.
- unrequested: No extra behavior identified.
- contradictions: No demonstrated implementation counterexample. The policy restriction prevents closing the evidence obligation and is not itself a P1 defect.

## Findings
No findings.
''')
contents['10']=('APPROVE','The exact local Acme 1.0 provider and delivery wrapper meet the documented same-ID/same-namespace retry contract. Ordinary gates, all supplied acceptance tests, an added timeout-before-commit probe and a completed competing-commit model pass.',none_memory,'''## Concurrency
- async-scope: REQUIRED (delivery timeout/drop before and after provider commit)
- deadlocks: PASS (complete wrapper/provider success and retry scenarios complete; competing commit Loom model completes; commit has one lock, no callbacks, no nested lock and no await while guarded)
- cancellation: PASS (cancel_at_both_boundaries_then_retry polls pending at pre-commit and post-effect boundaries, drops operation, then checks one total effect after retry; timeout after commit plus added before-commit timeout both pass)
- task-lifecycle: N/A (AcmeTransport and deliver spawn no tasks; the delivery future exclusively owns the pending operation, and synchronous commit contains no suspension)
- async-evidence: tests/delivery.rs: delivers and returns_for_retry; tests/vendor_tests.rs: timeout_after_commit_then_retry_deduplicates, cancel_at_both_boundaries_then_retry, reconnect_and_quiescent_restart_preserve_keys; all five pass in tests.log. probe/tests/before_timeout.rs adds timeout_before_commit_then_retry, passing in before_timeout.log. Tokio 1.54.1 current-thread runtime, controlled manual poll with noop waker for drop points, zero timeout for deterministic pending send, one-second retry deadlines (30-second unelapsed deadline during manual cancellation), 120-second external watchdog. Commands/status in gates.json and before_timeout-status.json; exact source/manifests/lockfile hashes in probe-source-hashes.json.
- sync-scope: REQUIRED (atomic deduplication/ledger-effect transaction under provider mutex)
- loom: PASS (competing_retries_commit_once completes with actual provider and tracked mutex/Arc)
- synchronization: PASS (Server::commit holds the single state mutex across key insertion and conditional effect increment. The first insertion linearizes the operation; every duplicate observes that key under the same lock and returns the same u64 receipt without another effect. Snapshot copies both ledger and effect count under that lock; quiescent restore preserves their invariant into the sole successor namespace. No await inside commit allows cancellation to split insertion from effect.)
- model-evidence: tests/vendor_model.rs exercises actual src/acme.rs under feature model with Loom 0.7.2 Arc/Mutex, two active threads racing commit(7), identical receipt checks, effect_count==1 then distinct commit(8) gives count 2. max_threads=3, max_branches=1000, no permutation/time/preemption limit; model.log exit 0 well before 120-second external watchdog. No checkpoint specified. model-status.json records exact command; before/after hashes identical. Loom explores only the ledger transaction; native tests cover the actual async wrapper and fault modes.
''','''## Spec
- spec: PASS (REQUIREMENTS.md and VENDOR-CONTRACT.md, local Acme reference provider 1.0 only)
- missing: None within stated scope: timeout and drop on both sides of commit, repeated retries, reconnect, quiescent state restore, distinct IDs and competing duplicate commits were executed.
- unrequested: No out-of-scope service or remote implementation added; supplied local fault modes and snapshots are explicitly required.
- contradictions: None. Returning Retry after an effect is permitted because the same ID and namespace deduplicate retry; cancellation does not claim to roll back committed effects.

## Findings
No findings.
''')
for id,(verdict,summary,memory,concurrency,spec) in contents.items():
 e=root/'reviews'/id;c=(e/'context.log').read_text();base=re.search('BASE_SHA=(.*)',c)[1];head=re.search('HEAD_SHA=(.*)',c)[1]
 gates=json.loads((e/'gates.json').read_text())
 gate_text='## Gates\n'+''.join(f'- {name}: {"PASS" if gates[name]["status"]==0 else "FAIL"} ({name}.log; exit {gates[name]["status"]})\n' for name in ['fmt','clippy','tests','doctests','deny'])
 counts={'01':'Five unit tests pass; one fee doctest fails. Six isolated contract probes fail as described below.','04':'Two shipped unit tests pass; zero doctests.','07':'Ordinary tests and doctests run zero tests; this is not counted as publication validation.','10':'Five native acceptance tests pass; zero doctests.'}[id]
 dirty='Dirty src/lib.rs plus untracked src/limits.rs included. Committed vs local attribution is given in each finding.' if id=='01' else 'Clean tracked tree; no untracked review inputs.'
 limitations='Semver checks N/A: unpublished crate (publish=false), no release baseline requested. All manifests edition 2024; no inferred MSRV. '
 if id=='04':limitations+='Foreign callbacks are caller-supplied under the documented unsafe contract; no undocumented native provider was assumed. Alias-model discrepancy needs specialist resolution.'
 if id=='07':limitations+='To close the escalation, obtain authorization for completed exploration or equivalent exact-source completed evidence; current one-permutation policy was honored.'
 if id=='10':limitations+='Approval applies to the complete local reference provider and its stated quiescent restart, unique-ID/same-namespace constraints. No claims about a real SDK, external business effects, crash durability, stale snapshots, or concurrent old/new servers.'
 text=f'## Verdict: {verdict}\n{summary}\n\n'+gate_text+'\n'+counts+' Equivalent offline gates used; exact commands/statuses are in gates.json. RUST_REVIEWDOG=1, nofilter local reporter, raw Clippy and reviewdog output retained in rust-review-clippy.* directories. Clippy verdict follows its own exit code; all reviewdog presentation statuses are recorded separately.\n\n'+memory+'\n'+concurrency+'\n'+spec+'\n## Residual risks\n'+f'- Scope: origin/main base {base}; HEAD {head}; base-to-current working tree including local/untracked files. {dirty} context.log and diff.log retain scope evidence.\n'+f'- Integrity: before-hashes.json equals after-hashes.json for every original tracked/untracked input. after-status.log preserves Git status. Probe implementation/configuration is byte-identical where used; harness additions are isolated under this review directory.\n'+'- Method: repository graph initialized with explicit repo_root, change/flow/tests-for queries and Rust LSP workspace symbol lookup preceded source inspection. graph-lsp.json and graph-review.json retain responses. Empty graph test edges were not treated as proof of no tests; exact source/tests were read.\n'+'- Offline freshness: cargo-deny passed using the existing cached advisory database without fetching; this does not establish current online advisory coverage. No dependency/tool installation or external service access. Host-only diagnostics; versions.log records compiler.\n'+f'- Limitations: {limitations}\n'
 (e/'report.md').write_text(text)
