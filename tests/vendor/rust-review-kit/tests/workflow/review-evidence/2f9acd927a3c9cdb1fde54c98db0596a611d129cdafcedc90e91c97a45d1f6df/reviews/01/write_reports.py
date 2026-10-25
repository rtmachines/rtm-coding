from pathlib import Path
import subprocess,json,hashlib
root=Path('/tmp/rust-skills-review-20261025')
rules={'01':['num-overflow-explicit','num-saturating-clamp','err-result-over-panic','conv-fromstr-parsing'],'04':['unsafe-safety-comment','mem-drop-order','async-cancel-safety','async-no-lock-await','async-joinset-structured','conc-atomic-ordering','test-loom-concurrency'],'07':['conc-atomic-ordering','test-loom-concurrency'],'10':['async-cancel-safety','own-mutex-interior','test-loom-concurrency']}
verdicts={'01':('REQUEST_CHANGES','Six reachable contract violations were confirmed in exact-source isolated tests. The fee doctest also fails.'),'04':('ESCALATE','The retained pointer fails Stacked Borrows but passes Tree Borrows on identical source. Ownership is live, but provenance across Box moves remains unresolved; do not approve on the passing model alone. Async and publication checks passed.'),'07':('ESCALATE','The ordering argument is sound under the specified single-writer, one-shot contract, but permitted Loom exploration stops after one permutation. A successful process exit does not close the required model-exploration gate.'),'10':('APPROVE','The exact local reference provider, wrapper, acceptance scenarios and completed concurrent ledger model satisfy the stated deployment contract. Approval is limited to that local provider and its documented namespace/restart assumptions.')}
mem_none='''## Memory safety
- memory-scope: NONE (safe Rust only; no affected unsafe/FFI ownership or provenance boundary)
- miri: N/A (no affected memory boundary)
- aliasing: N/A (no affected unsafe aliasing obligation)
- memory-evidence: N/A; inspected all runtime source and tests, not merely added unsafe tokens.
- aliasing-evidence: N/A; ownership uses safe Rust APIs only.
'''
async_none='''- async-scope: NONE (no async work or task ownership in affected implementation)
- deadlocks: N/A (no locks/async waits)
- cancellation: N/A (no cancellable operation)
- task-lifecycle: N/A (no owned worker)
- async-evidence: N/A for the source scope above.
'''
sync_none='''- sync-scope: NONE (no custom shared-state protocol)
- loom: N/A (no affected concurrency)
- synchronization: N/A (no shared state)
- model-evidence: N/A for the source scope above.
'''
for id in rules:
 r=root/'cases'/id;o=root/'reviews'/id
 base=subprocess.check_output(['git','rev-parse','origin/main'],cwd=r,text=True).strip();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip()
 data=json.loads((o/'commands.json').read_text())
 rule_paths=['.agents/skills/rust-skills/rules/'+n+'.md' for n in rules[id]]
 (o/'rules-read.json').write_text(json.dumps({'pinned_revision':'a1e290d53d43a85421ff16dde23b5f8ec0b48539','rules':{f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in rule_paths},'notes':'Bundled rtmachines fork, recorded by vendored.tsv. No review edits. Index and rust-pr-review skill identical across assigned repositories by SHA256; read once and equality checked. Relevant references read: SMELLS, SPEC-PASS, RUST-LSP, REVIEWDOG; MEMORY-VALIDATION and SAFETY-PRECHECK for 04; CONCURRENCY-VALIDATION for 04/07/10.'},indent=2))
 v,reason=verdicts[id]
 s=f'''## Verdict: {v}
{reason}

## Tooling
- rust-lsp: AVAILABLE (successful actual workspace semantic queries)
- lsp-used: YES (workspace_symbols and hover)
- lsp-evidence: `tool-evidence.json` and `lsp-hover.json`; workspace `{r}`. Hover resolved '''+{'01':'`src/limits.rs:1` to `parse_limit(&str) -> Option<u16>` including the untracked module.','04':'`src/registration.rs:14` to the unsafe constructor with Box ownership and callback contract.','07':'`src/lib.rs:13` to `Published::publish` with its single-writer precondition.','10':'`src/acme.rs:25` to the actual `Server::commit(&self, u64) -> Receipt`.'}[id]+'''
- lsp-limitations: Queries confirm these symbols/types, not soundness or model completeness. Full source/test inspection and diagnostics supply the remaining analysis; no unsupported rename or edits used.
- Graph: initialized per-repository; detect_changes, affected flows, tests_for and explicit-file review context recorded in `tool-evidence.json` / `graph-context.json`. Graph tests_for returned no matches despite source tests; graph emptiness was not used to infer missing coverage. Explicit context includes relevant runtime paths and untracked code where applicable.
- Rust knowledge: bundled `rtmachines/rust-skills` revision `a1e290d53d43a85421ff16dde23b5f8ec0b48539`, verified against `.agents/rust-review-kit/vendored.tsv`; actual consulted rule paths/hashes are in `rules-read.json`. Vendoring documents a rewritten LOCAL_CHANGES regression link, otherwise the rules are the pinned subset. No local review modifications.
- Rules consulted: '''+', '.join('`'+f+'`' for f in rule_paths)+'''. Their general guidance was subordinated to the explicit requirements; no rule priority was converted directly into a finding severity.

## Gates
'''
 for name in ['fmt','clippy','tests','doctests','deny']:
  s+=f'- {name}: {"PASS" if data[name]["exit"]==0 else "FAIL"} (`{name}.log`, exit {data[name]["exit"]}; exact command in `commands.json`)\n'
 s+='''
Stable Rust 1.99.1, edition 2024, no declared MSRV. All checks use offline, locked Cargo resolution; no network or installations. Default features used (01 has no features; equivalent to all-features); optional model checked separately. Reviewdog read raw uncolored Clippy output, nofilter/local reporter, exit 0 (`reviewdog.log`); empty output does not substitute for Clippy's independently captured exit. Cargo-deny used `cargo deny --locked --offline check`; advisory freshness is limited to the installed local database. Semver checks N/A: unpublished crate, no release baseline policy.

'''
 if id!='04':s+=mem_none
 else:s+='''## Memory safety
- memory-scope: REQUIRED (`src/registration.rs:14-34`, retained foreign read-only pointer across constructor return, owner moves and deregistration)
- miri: FAIL (Stacked Borrows retained-pointer test failed; Tree Borrows passed both tests; disagreement remains unresolved)
- aliasing: UNRESOLVED (live/stable Box allocation does not establish validity of an earlier pointer after Box moves)
- memory-evidence: `memory-probe/` copies exact bytes.rs and registration.rs, changing only the probe crate root/manifest and adding tests. `retained_after_move_and_during_unregister` constructs a registration, moves it into a Box, calls len, reads via retained pointer, then deregisters; `unaligned_and_short` checks offset input and lengths 0..3. Nightly Miri 0.1.0 commit 48f4b05538 (2026-10-23), existing `/home/rtm/.cache/miri` sysroot. Default MIRIFLAGS: retained-pointer test fails at the first post-move read (subsequent tests not established by this run). `-Zmiri-tree-borrows`: both tests pass, including unregister-time access. Commands, exit statuses and raw logs: `miri-stacked-command.json`, `miri-tree-command.json`, `miri-stacked.log`, `miri-tree.log`. 120-second watchdog; neither timed out. Source hashes recorded with the harness mapping.
- aliasing-evidence: pointer is created by `bytes.as_ptr()` at registration.rs:20, retained without writes/free by a serialized C-ABI Rust callback. The Box is moved into Self at line 21, returned and moved into the harness Box. Stacked Borrows reports the line-21 Unique retag invalidating the earlier SharedReadOnly tag; Tree Borrows accepts the same read. No free precedes unregister: Drop calls unregister before field destruction, and no public mutable buffer access exists. That proves liveness, not provenance. The callbacks obey the unsafe API's documented read-only, serialized, synchronous-quiescence contract; this is not evidence about any unspecified native vendor. Closure requires a justified provenance argument for this ownership pattern or a separately validated redesign with both model results reconciled. No tested fix is claimed.
'''
 s+='\n## Concurrency\n'
 if id=='01':s+=async_none+sync_none
 elif id=='07':s+=async_none+'''- sync-scope: REQUIRED (one-shot atomic payload publication)
- loom: NOT RUN (approval-quality exploration incomplete; the single permitted permutation exited 0)
- synchronization: PASS (independent ordering proof under the explicit caller preconditions)
- model-evidence: `tests/publication_model.rs`, Loom 0.7.2, feature model replaces both atomics with tracked Loom types; tracked Arc/thread, one writer storing 42, one reader checks Some before join and Some(42) after join. `loom.log` / `loom-command.json`. Builder checkpoint_interval=1, max_permutations=Some(2) (one execution), max_duration=None, preemption_bound=None, default branch/thread bounds. A single invocation only; no rerun or isolated probe bypassed the project cap. This deliberately truncated search is not complete model evidence despite green assertions. The value Relaxed store is sequenced before the ready Release store; a reader observing true with Acquire synchronizes with it, so the later value load must see that store (there is no later writer). None is allowed before publication. To close: authorize sufficient exploration in a different review environment and complete the exact tracked model within documented bounds; the current cap cannot be bypassed here.
'''
 elif id=='04':s+='''- async-scope: REQUIRED (Service lock progress, approved_pop cancellation, owned worker stop)
- deadlocks: PASS (targeted `progress` test completes increment and subsequent snapshot within one second)
- cancellation: PASS (`cancel_before_approval_and_at_lock` drops pending futures at both awaits, preserves queue, and checks closed approval)
- task-lifecycle: PASS (`stop_observes_destructor_and_prevents_effect` handshakes worker readiness, verifies destructor completion before stop returns and prevents later signaled effect)
- async-evidence: exact source copy in `probe/`; 3 targeted tests in `probe/tests/transitions.rs`, Tokio 1.54.1 current-thread runtime, explicit polling/oneshot handshakes, 1-second timer where applicable and external 120-second process limit. `transitions.log` and `transitions-command.json`; all pass. Service releases its first mutex guard before snapshot reacquires. approved_pop has no removal before approval and no await after removal. stop_worker aborts then awaits termination; dropping its own supervisor before completion is outside the return guarantee. Await also waits for running spawn_blocking work rather than asserting abort stops it.
- sync-scope: REQUIRED (Published value/ready handoff)
- loom: PASS (one non-vacuous model completed, not a capped sample)
- synchronization: PASS (Release/Acquire publication argument)
- model-evidence: `probe/tests/publication_model.rs` imports the exact copied implementation using feature model, Loom 0.7.2 tracked AtomicUsize, AtomicBool, Arc and thread. One writer stores 42 and one reader asserts every pre-join Some equals 42, then post-join Some(42). max_threads=3, max_branches=1000, no permutation, time or preemption limit; external 120-second watchdog not reached. `loom.log`, `loom-command.json`; completed exit 0. Payload store precedes ready Release; true Acquire observes that release, placing the payload store before its Relaxed load. One-shot precondition excludes subsequent competing payload writes. This does not claim every C11 behavior is modeled.
'''
 else:s+='''- async-scope: REQUIRED (deliver timeout/drop boundaries in the actual Acme local provider)
- deadlocks: PASS (native acceptance tests complete; complete concurrent ledger model passes. One short synchronous mutex transaction, no nested acquisition or await while held)
- cancellation: PASS (explicit poll/drop both before commit and after effect/before reply; timeout and retry at both boundaries)
- task-lifecycle: N/A (provider starts no background task; each send is owned directly by the wrapper future)
- async-evidence: `tests/vendor_tests.rs` has 3 named tests covering post-commit timeout/repeated retry, `cancel_at_both_boundaries_then_retry`, and reconnect/quiescent restore/distinct IDs; `tests/delivery.rs` adds ready and pending-wrapper tests. All 5 native tests pass in `tests.log`. Isolated exact-source `probe/tests/timeout_before.rs::timeout_before_commit_then_retry` supplies the remaining explicit pre-commit timeout scenario (zero effects before retry, one afterward), pass in `timeout_before.log`; command/exit in matching JSON. Tokio 1.54.1 current-thread runtime, explicit single poll into pending states and zero timeout for fault modes, bounded normal retry timeout; outer 120-second watchdog. No sleeps are used to guess cancellation timing.
- sync-scope: REQUIRED (provider ledger transaction and competing duplicate requests)
- loom: PASS (exact Server model completed)
- synchronization: PASS (one mutex linearizes both ID insertion and effect increment)
- model-evidence: `tests/vendor_model.rs::competing_retries_commit_once`, Loom 0.7.2 tracked Arc/Mutex selected in actual `src/acme.rs` by feature model. Main and worker concurrently commit ID 7; each receipt is 7, effect_count is 1, then distinct ID 8 yields count 2. max_threads=3, max_branches=1000; no permutation/time/preemption truncation; external 120-second watchdog not reached. `loom-command.json` and `loom.log`, one model passes. Every commit acquires the same mutex, and only a newly inserted ID increments effects; every later duplicate sees the retained entry. No await or user callback splits the transaction. Restore clones/transfers both ledger and count at the specified quiescent boundary. Model coverage is ledger synchronization, not Tokio internals or remote-network behavior.
'''
 s+='\n## Spec\n'
 if id=='01':s+='''- spec: FAIL (REQUIREMENTS.md; six explicit contracts violated)
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
'''
 elif id=='04':s+='''- spec: PARTIAL (REQUIREMENTS.md available; safe decoding, progress, cancellation, stop and publication validated; retained-buffer aliasing unresolved)
- missing: a resolved provenance justification for the retained pointer across Box movement, not evidence that storage was freed early.
- unrequested: none found in runtime changes.
- contradictions: no definite additional contract violation established; experimental alias-model disagreement requires escalation.

## Findings
No findings promoted to definite P0/P1. The aliasing question at src/registration.rs:20-21 is an unresolved safety blocker detailed above, not a claimed universally proven use-after-free.
'''
 elif id=='07':s+='''- spec: PARTIAL (REQUIREMENTS.md available; ordering invariant established, required model exploration incomplete under imposed execution limit)
- missing: completed model exploration beyond the one permitted permutation.
- unrequested: none found.
- contradictions: no demonstrated runtime defect; do not relabel the environment's model-execution cap as a P1 algorithm bug.

## Findings
No findings. Unresolved model evidence is the approval blocker described above.
'''
 else:s+='''- spec: PASS (REQUIREMENTS.md and VENDOR-CONTRACT.md; exact local provider implementation and acceptance scenarios inspected and executed)
- missing: none within the explicitly local provider contract; added isolated pre-commit timeout probe closes that acceptance coverage gap.
- unrequested: none in runtime behavior.
- contradictions: none; same request ID/server namespace and retained state provide deduplication after lost reply and retry.

## Findings
No findings.
'''
 s+=f'''\n## Residual risks
- Scope: origin/main `{base}` -> HEAD `{head}` plus all local changes. '''+('Dirty tracked `src/lib.rs` and untracked `src/limits.rs` included; nothing untracked excluded from application review. ' if id=='01' else 'Worktree clean; no untracked application files. ')+'''Full tracked diff saved in `diff.log`; context and initial status in `context.log`.
- `hashes-before.json` and `hashes-after.json` match for every pre-existing tracked/untracked file. Git/source state was not changed. Generated graph/build caches are ignored or outside the repository. Probe-source mappings verify exact source copies; only harness files and reduced memory-probe manifest differ.
- Review evidence is fresh for this working tree, not historical reports or expected verdicts. Supporting vendored knowledge was consulted selectively as the review skill requires; not all 265 general rules were applied.
- Existing offline advisory database can miss later advisories; no live freshness claim. Native target is x86_64 Linux; no other platform or unspecified MSRV was validated.
'''
 if id=='10':s+='- Approval does not extend to a proprietary SDK, arbitrary Transport implementations, a fresh empty retry server, concurrent old/new servers, stale/lost snapshots, or crash/power-loss durability. These are explicitly outside VENDOR-CONTRACT.md; no missing remote-provider guarantees are invented for the complete local fixture.\n'
 (o/'report.md').write_text(s)
 p=subprocess.run(['bash','.agents/skills/rust-pr-review/scripts/check-report.sh',str(o/'report.md')],cwd=r,text=True,capture_output=True);(o/'report-validation.log').write_text(p.stdout+p.stderr);(o/'report-validation-command.json').write_text(json.dumps({'command':['bash','.agents/skills/rust-pr-review/scripts/check-report.sh',str(o/'report.md')],'exit':p.returncode}));print(id,p.returncode,p.stdout,p.stderr)
