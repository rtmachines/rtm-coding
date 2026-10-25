from pathlib import Path
import json,subprocess,shutil
root=Path('/tmp/rust-skills-review-20261025')
rules={'02':['conv-fromstr-parsing','num-overflow-explicit','proj-pub-use-reexport'],'03':['unsafe-miri-ci','unsafe-safety-comment','conc-atomic-ordering','async-no-lock-await','async-cancel-safety','async-joinset-structured','test-loom-concurrency'],'08':['async-cancel-safety'],'11':['async-cancel-safety']}
for i in rules:
 p=root/'cases'/i;o=root/'reviews'/i
 for name in rules[i]:shutil.copy2(p/'.agents/skills/rust-skills/rules'/f'{name}.md',o/f'rule-{name}.read.md')
 state=(o/'git-state.txt').read_text().splitlines();base,head=state[:2];st=json.loads((o/'status.json').read_text())
 verdict={'02':'APPROVE','03':'REQUEST_CHANGES','08':'ESCALATE','11':'ESCALATE'}[i]
 reason={'02':'The added parser preserves the requested contracts; ordinary gates and isolated contract probes pass.','03':'Six reachable contract defects are demonstrated by exact-source probes. Clippy also fails. These are verified failures, not missing-evidence allegations.','08':'Retry safety for the proprietary deployed transport remains unresolved. The required supplier implementation and protocol contract are explicitly unavailable.','11':'The supplied contract describes AcmeTransport and Server, but neither implementation nor its acceptance/model tests exists in this checkout. The provider retry/cancellation obligations remain unresolved.'}[i]
 report=f'## Verdict: {verdict}\n{reason}\n\n## Tooling\n- rust-lsp: AVAILABLE (workspace_symbols succeeded in this repository).\n- lsp-used: YES (workspace symbol resolution and hover executed).\n- lsp-evidence: tools.json records workspace_symbols and graph calls with the explicit repository root; lsp-hover.json records the actual semantic response. '
 report+= {'02':'Hover at src/limits.rs:1 resolved parse_limit as fn(&str) -> Option<u16>.','03':"Hover at src/service.rs:15 resolved count as MutexGuard<'_, u64>.",'08':'Hover at src/lib.rs:14 resolved Tokio timeout, its cancellation contract and boxed-future type.','11':'Hover at src/lib.rs:14 resolved Tokio timeout, its cancellation contract and boxed-future type.'}[i]+'\n'
 report+='- lsp-limitations: Queries are navigation evidence, not proof of runtime safety or downstream behavior.\n- Graph: initialized locally, then detect_changes, affected flows and tests_for narrowed review; graph-context.json contains source context for actual Rust changes. Empty tests_for results were checked against actual tests. The graph misidentifies some method-name relationships and omits coverage; source wins.\n'
 report+='- Knowledge: rtmachines/rust-skills pinned at a1e290d53d43a85421ff16dde23b5f8ec0b48539, from .agents/rust-review-kit/vendored.tsv. Read its SKILL.md index and these complete rules: '+', '.join(x+'.md' for x in rules[i])+'. Local vendoring notes say index/rules unchanged; LOCAL_CHANGES.md link rewritten. This is the corrected fork, not a newly fetched upstream. Per-file before/after hashes record local content.\n'
 report+='- Also consulted rust-pr-review SKILL.md, SMELLS, SPEC-PASS, RUST-LSP and REVIEWDOG; memory/concurrency validation and SAFETY-PRECHECK for applicable paths.\n\n## Gates\n'
 for g in ['fmt','clippy','tests','doctests','deny']: report+=f'- {g}: '+('PASS' if st[g]==0 else 'FAIL')+f' ({g}.log; exit {st[g]}; commands.jsonl).\n'
 report+='\nAll commands ran offline on existing stable Rust 1.99.1 (versions.log). Features: '+('--all-features (no optional features).' if i=='02' else 'default for ordinary gates per project policy; model only in Loom probes where applicable.')+' cargo-deny used --locked --offline check with the existing advisory database; this does not establish current online advisory freshness. Reviewdog used raw Clippy output with local reporter and nofilter; its status is independent in status.json. No network/install was used.\n'
 if i=='03':report+='Clippy reports boxed_local at src/registration.rs:15 (exit 101); it is not duplicated as a behavioral finding.\n'
 report+='\n## Memory safety\n'
 if i!='03':
  report+='- memory-scope: NONE (safe parser/wrapper change has no affected unsafe ownership boundary in the available implementation).\n- miri: N/A (no changed memory invariant).\n- aliasing: N/A (no changed memory invariant).\n- memory-evidence: N/A; source inspected.\n- aliasing-evidence: N/A; no raw-pointer or foreign-memory transition is introduced.\n'
 else:
  report+='''- memory-scope: REQUIRED (bytes::read_word and registration::Registration).
- miri: FAIL (three targeted probes each report UB; miri-short_word.log, miri-unaligned_word.log, miri-retained_buffer.log).
- aliasing: FAIL (allocation liveness, bounds and alignment are violated independently of experimental alias models).
- memory-evidence: memory/src/bytes.rs and registration.rs are exact copies, with hashes in probe-hashes.json matching before.json. Three one-test runs: short_word, unaligned_word, retained_buffer. cargo +nightly miri test --offline <name>, strict provenance, existing /home/rtm/.cache/miri sysroot; toolchain/commit in miri-version.log, commands/environment/exit in commands.jsonl. Each run exits 1; external watchdog 120 seconds, no watchdog reached. Suspected UB was executed only under Miri.
- aliasing-evidence: read_word derives a u32 pointer from an arbitrary shared byte slice; nonempty does not prove four accessible bytes or alignment. Its read is invalid for a one-byte allocation and an offset-one slice of an align(4) object. Registration creates a read-only pointer from its owned Box but never transfers the Box into Self; the Box frees at constructor return. Any subsequent allowed consumer read (including unregister) is dangling. The serialized Rust C-ABI shim retains only that pointer, neither writes nor frees it, and synchronously unregisters; it satisfies the documented caller contract. Moving Registration does not retain the allocation. Miri fails on the first post-constructor read, before unregister; the destructor path is independently invalid by the same lifetime chain. This establishes defects without claiming validation of an undisclosed native FFI library. Suggested redesigns below require new liveness and aliasing validation after implementation.
'''
 report+='\n## Concurrency\n'
 if i=='02':report+='''- async-scope: NONE (synchronous scalar/string helper only).
- deadlocks: N/A (no locks or async changes).
- cancellation: N/A (no futures).
- task-lifecycle: N/A (no tasks).
- async-evidence: N/A (scope inspected).
- sync-scope: NONE (no shared synchronization).
- loom: N/A (no custom protocol).
- synchronization: N/A (no custom protocol).
- model-evidence: N/A (scope inspected).
'''
 elif i=='03':report+='''- async-scope: REQUIRED (Service progress, approved_pop cancellation, stop_worker termination).
- deadlocks: FAIL (increment_progress reaches nested acquisition and times out).
- cancellation: FAIL (cancel_before_approval polls Pending, drops the future and observes an empty queue instead of [7]).
- task-lifecycle: FAIL (stop_prevents_later_effect releases a worker after stop_worker returns and observes its side effect).
- async-evidence: probe/tests/async.rs imports unchanged implementation copied in probe/src. Three targeted tests all fail in async.log, exit 101; Tokio 1.54.1 current-thread runtime, explicit polling/oneshot ordering, 50ms progress/effect deadline, 120s process watchdog. No random sleeps establish the cancellation boundary. The deadlock is proven by the held count guard awaiting snapshot's acquisition of the same non-reentrant Mutex, not by the timer alone.
- sync-scope: REQUIRED (Published one-shot publication).
- loom: FAIL (one_shot_publication observes Some(0) after publish(7), loom.log).
- synchronization: FAIL (two relaxed atomics do not publish payload visibility through ready).
- model-evidence: probe/tests/model.rs, feature model, exact publication.rs. Loom 0.7.2 tracked AtomicUsize/AtomicBool and Arc/thread; one writer publishes once and the reader asserts before join that any Some is 7, then asserts after join. Loom default exploration parameters, no explicit preemption/permutation bound, external 120s watchdog. Run completed with a real counterexample before timeout, exit 101; it does not claim exhaustive success. The independent argument: relaxed ready store/load provides no release/acquire happens-before edge for the earlier value store, so observing ready=true need not imply observing value=7. Hashes and commands are in probe-hashes.json and commands.jsonl.
'''
 else:
  report+='''- async-scope: REQUIRED (timeout drops delivery before the remote outcome is necessarily known).
- deadlocks: PASS (local delivers and returns_for_retry complete; there is no local lock cycle).
- cancellation: NOT RUN (deployed provider commit/reply cancellation boundary unavailable).
- task-lifecycle: NOT RUN (deployed provider side effects after cancellation cannot be inspected).
- async-evidence: tests/delivery.rs has two passing current-thread Tokio 1.54.1 tests, immediate Ready and never-ready Pending with zero timeout; tests.log. These exercise only local outcomes, not effect ownership, retry deduplication or supplier background work. Overall process watchdog 120s. Inventing a replacement provider would not verify the required exact implementation.
'''
  if i=='08':report+='''- sync-scope: NONE (no custom protocol in available wrapper; supplier internals unknown).
- loom: N/A (no available custom synchronization implementation to model).
- synchronization: N/A (wrapper has no custom protocol; supplier behavior is unresolved under async scope).
- model-evidence: N/A for local wrapper. Missing supplier implementation is a residual evidence gap, not proof that it duplicates effects.
'''
  else:report+='''- sync-scope: REQUIRED (VENDOR-CONTRACT.md explicitly requires competing duplicate commits through the actual Server ledger).
- loom: NOT RUN (Server implementation and tracked model are absent).
- synchronization: UNRESOLVED (the contract claims atomic deduplication under a mutex; source and model are needed to establish it).
- model-evidence: source-inventory.txt lists every tracked and nonignored untracked file; only wrapper and Ready/Pending tests implement runtime behavior. Filesystem inspection also found no provider. Required closure: supply exact AcmeTransport/Server 1.0 source, run timeout/drop before and after commit, retries, reconnect, quiescent snapshot restore, distinct IDs, and duplicate-commit Loom model against that actual code. Contract prose cannot substitute for execution evidence.
'''
 report+='\n## Spec\n'
 if i=='02':report+='''- spec: PASS (REQUIREMENTS.md; exact source plus contracts.log, one isolated test covers all six contracts).
- missing: None in public behavior; parser regression scenarios exist in isolated review evidence rather than repository tests.
- unrequested: No runtime dependency or transport/storage change.
- contradictions: None. can_read uses both comparisons, checked_sub rejects overdraw, chars counts Unicode scalars, expiry uses strict <, and widened multiplication fits u64 since (2^32-1)^2 < 2^64. The parser uses inferred u16 FromStr and is re-exported at root; malformed/negative/overflow reject.
'''
 elif i=='03':report+='''- spec: FAIL (REQUIREMENTS.md; all six added contracts have counterexamples).
- missing: Bounds/alignment checks, retained buffer ownership, progress, cancellation preservation, termination barrier and publication ordering.
- unrequested: No unrelated runtime scope found.
- contradictions: The comments claim guarantees that the implementations and targeted probes disprove. Ordinary tests avoid the affected unsafe paths and unbounded waits as requested, but that does not validate the adapters.
'''
 else:report+='''- spec: PARTIAL (REQUIREMENTS.md: local delivered/retry results pass; deployed-provider no-duplicate-effects claim remains unverified).
- missing: Exact deployed provider implementation and acceptance evidence for its effect/cancellation contract.
- unrequested: No unrelated runtime scope found.
- contradictions: No demonstrated local defect; provider claims are unverified, not disproven.
'''
 report+='\n## Findings\n'
 if i=='03':report+='''- [P1] src/bytes.rs:7 - Read requires bounds and alignment the safe API does not ensure. Trigger: a nonempty 1–3 byte allocation or a four-byte slice at an unaligned address. Impact: out-of-bounds or unaligned u32 read is undefined behavior. Fix: validate at least four bytes and decode an exactly sized byte array with from_ne_bytes (or use a separately justified unaligned read). Both violations are reproduced by Miri.
- [P1] src/registration.rs:21 - Retain the allocation until unregister has completed. Trigger: a conforming foreign consumer reads its retained pointer after new returns. Impact: bytes was dropped at constructor return, so the permitted read is use-after-free. Fix: redesign Registration to own the allocation through synchronous unregister, then free exactly once; separately validate moves/reborrows and retained-pointer provenance. The untested candidate ownership change alone is not a completed safety fix.
- [P1] src/service.rs:16 - Do not reacquire count while its guard is live. Trigger: any increment_and_snapshot call. Impact: snapshot waits for the same guard that the caller holds until snapshot finishes, permanently blocking progress. Fix: return the value through the existing guard, or drop it before snapshot if a later snapshot is the intended contract.
- [P1] src/service.rs:25 - Wait for approval before consuming the queue. Trigger: poll approved_pop while approval is pending, then cancel/drop it (or close approval). Impact: the queue item has already been removed and is lost without approval. Fix: await successful approval before pop_front, preserving cancellation behavior until that point.
- [P1] src/service.rs:32 - Dropping a JoinHandle does not stop its worker. Trigger: worker is pending and stop_worker returns, then its input becomes ready. Impact: the detached worker still performs a side effect after the promised termination barrier. Fix: request suitable cancellation and await observed task termination, or cooperatively stop and join; account for nonabortable blocking work if accepted by this API.
- [P1] src/publication.rs:23 - Publish the payload with a release/acquire handoff. Trigger: a concurrent reader sees ready=true before observing value's relaxed store. Impact: snapshot returns Some(0) for publish(7), violating the one-shot contract. Fix: Release-store ready and Acquire-load it in snapshot while retaining the single-writer one-shot invariant; re-run the model. The counterexample respects that invariant.
'''
 else:report+='No findings. Missing provider evidence is reported as unresolved risk rather than an invented defect.\n' if i!='02' else 'No findings.\n'
 report+=f'\n## Residual risks\n- Scope: origin/main {base} to HEAD {head}, including working-tree and untracked scope. Git state is clean; no nonignored untracked files were present. Full diff captured in diff.log; context.log and source-inventory.txt record scope.\n'
 report+='- Source integrity: before.json and after.json match (hash-check.txt). Only isolated review probes/evidence and ignored graph/build artifacts were created. No reviewed source or Git state changed.\n- Edition 2024; no declared MSRV. Unpublished crate (publish=false), so semver-checks N/A; no release baseline required. Host target only; unsupported targets and online advisory freshness were not verified.\n'
 if i=='02':report+='- Review probe source copies are byte-identical; contracts.log exits 0. Repository tests do not themselves exercise parse_limit edge cases.\n'
 if i=='03':report+='- Priorities are P1 because these are reachable blocking defects in an unpublished helper crate; no demonstrated broad production impact establishes P0. Suggested changes are candidates and were not applied or claimed validated.\n'
 if i in ['08','11']:report+='- The provider implementation must be supplied to close cancellation/side-effect safety. Ordinary green gates cannot establish exactly-once effects or ledger durability. No real proprietary SDK, service or production incident is asserted.\n'
 (o/'report.md').write_text(report)
 r=subprocess.run(['bash','.agents/skills/rust-pr-review/scripts/check-report.sh',str(o/'report.md')],cwd=p,capture_output=True,text=True);(o/'report-validation.log').write_text(r.stdout+r.stderr);(o/'report-validation.exit').write_text(str(r.returncode));print(i,r.returncode,r.stdout,r.stderr)
