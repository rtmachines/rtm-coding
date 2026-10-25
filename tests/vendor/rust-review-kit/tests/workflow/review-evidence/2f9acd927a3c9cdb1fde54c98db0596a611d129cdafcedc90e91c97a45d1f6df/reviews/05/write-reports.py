from pathlib import Path
import subprocess,json
root=Path('/tmp/rust-skills-review-20261025')
for id in ['05','06','09']:
 p=root/'cases'/id;o=root/'reviews'/id
 base,head=subprocess.check_output(['git','rev-parse','origin/main','HEAD'],cwd=p,text=True).split()
 common=f'''## Tooling
- rust-lsp: AVAILABLE (successful workspace_symbols probe of {p}).
- lsp-used: YES (workspace symbols and references for {'Session::attach' if id=='05' else 'Registration::new' if id=='06' else 'Published::publish'}).
- lsp-evidence: graph-lsp.json records the real workspace_symbols response with definitions in src/; lsp-references.json records target positions and resolved references. Case 06 resolves Registration::new to tests/memory.rs:21. Case 05 has no in-repository attach caller. Case 09 default-feature references do not include the feature-gated model test; that test was read and compiled separately.
- lsp-limitations: default-feature workspace analysis; model configuration checked through Cargo/Loom. External vendor implementation and downstream callers are outside LSP scope. Graph build used explicit repo_root; detect_changes(origin/main), get_affected_flows(origin/main), and tests_for(src/lib.rs) precede source inspection. Empty graph edges are not evidence of absent coverage. Full direct source/tests review supplements graph output.
- Knowledge: rtmachines/rust-skills pinned a1e290d53d43a85421ff16dde23b5f8ec0b48539 per .agents/rust-review-kit/vendored.tsv. Its index and the complete relevant rule files were read. Kit records SKILL.md/rules/CORRECTIONS.json unchanged from that fork; LOCAL_CHANGES.md has a pinned-link adjustment. The fork itself includes corrections relative to its original upstream. No dirty local modifications; instructions-read.json records exact local hashes, shared-reading-equivalence.json verifies identical shared texts across assigned cases.
- Rules consulted: {', '.join(['unsafe-safety-comment.md','unsafe-miri-ci.md'] if id=='05' else ['conc-atomic-ordering.md','test-loom-concurrency.md']+(['unsafe-safety-comment.md','unsafe-miri-ci.md','async-cancel-safety.md','async-no-lock-await.md'] if id=='06' else []))}, under .agents/skills/rust-skills/rules/. Rust review references read: SMELLS, SAFETY-PRECHECK, MEMORY-VALIDATION, CONCURRENCY-VALIDATION, SPEC-PASS, RUST-LSP and REVIEWDOG. Rust LSP skill: /home/rtm/.codex/skills/rust-lsp/SKILL.md.

## Gates
- fmt: PASS (fmt.log, exit 0).
- clippy: PASS (clippy.log, --workspace --all-targets --locked --offline -- -D warnings, exit 0). Raw short diagnostics also passed local reviewdog, reviewdog.log; its status is independent of Clippy.
- tests: PASS (tests.log, cargo test --workspace --locked --offline --no-fail-fast, exit 0).
- doctests: PASS (doctests.log, separate --doc run, exit 0; zero doctests defined).
- deny: PASS (deny.log, cargo deny --locked --offline check, exit 0). Unused BSD-3-Clause allowance warning only; advisory freshness limited to existing offline database.
- Environment: Rust stable 1.99.1, commit 58cf8f9c35b355199727627d07ae34a4e2846d67; edition 2024, no declared MSRV. Default features for ordinary gates per project policy. Explicit model feature tested separately where applicable. Exact commands, environments and exit statuses: commands.json. Raw outputs retained alongside this report. No network or installation.
'''
 if id=='05':
  report='''## Verdict: ESCALATE
The vendor callback contract and pointer provenance remain unresolved. Ordinary gates pass, but they contain no behavioral tests. The available vendor.h declares ABI signatures only; it does not establish that unregister waits for all callbacks. Conditional exact-source probes disagree between aliasing models. Neither missing provider evidence nor that disagreement is reported as a proven vendor defect.

'''+common+'''
## Memory safety
- memory-scope: REQUIRED (src/vendor.rs:22-32, retained callback context and destruction).
- miri: FAIL (conditional retained_read_after_move shim: Stacked Borrows rejects the retained read; Tree Borrows passes; no run against the actual vendor binary).
- aliasing: UNRESOLVED (conflicting model evidence and missing foreign teardown guarantee).
- memory-evidence: probe/src/lib.rs is a byte-identical copy of src/vendor.rs; probe-source-mapping.json and probe-hashes.json record mapping/hashes. One test, retained_read_after_move, reads the retained pointer after attach returns and the owner moves, then drops it. Both runs use nightly 1.101.0-nightly commit 48f4b05538b8eca412137042d9647a61e692c6b3, 120-second process limit. probe-stacked.log uses MIRIFLAGS=-Zmiri-strict-provenance and exits 1; probe-tree.log adds -Zmiri-tree-borrows and exits 0. The shim supplies same-thread, read-only retention and immediate unregister; it is NOT the supported vendor runtime mandated by attach's contract. It diagnoses a conditional Rust ownership problem, not actual vendor behavior.
- aliasing-evidence: token starts as a Box<u64>. src/vendor.rs:25 derives an escaped pointer through &mut *token. Stacked Borrows reports invalidation on the Box move into Self at line 26; the later retained read fails despite the allocation remaining live. Tree Borrows accepts the same source/test. Drop at line 32 creates another mutable reborrow before unregister; its interaction with retained pointers is also not justified by address stability. The Box is freed after Drop returns, which is safe only if all foreign accesses have ceased. vendor.h:1-3 provides no retention/quiescence, concurrent-callback, or reentrancy guarantee. Closure requires a versioned vendor contract/implementation establishing permitted access and synchronous quiescence, plus a justified ownership/provenance design and targeted tests for constructor return, moves and teardown. A raw-owner design is only a candidate until tested; no reviewed code was changed.

## Concurrency
- async-scope: NONE (no async Rust operations).
- deadlocks: N/A (no Rust async lock protocol).
- cancellation: N/A (no futures).
- task-lifecycle: N/A (no Rust spawned tasks).
- async-evidence: N/A; foreign callback quiescence is tracked under Memory safety.
- sync-scope: NONE (no changed custom Rust atomic or lock synchronization protocol; foreign synchronization unknown).
- loom: N/A (no modelable Rust synchronization protocol supplied).
- synchronization: N/A (foreign teardown obligations remain unresolved under Memory safety).
- model-evidence: N/A; a guessed foreign model cannot establish vendor behavior.

## Spec
- spec: PARTIAL (REQUIREMENTS.md requests RAII and memory-safe vendor teardown; RAII shape exists, but actual vendor guarantees and aliasing cannot be verified).
- missing: Evidence for safe callback teardown and pointer validity, not a proven missing implementation.
- unrequested: Review workflow and bundled knowledge updates support review; no additional runtime behavior observed.
- contradictions: None proven against the actual vendor contract; ABI declaration is insufficient to determine it.

## Findings
No findings. Unresolved safety obligations above require escalation rather than an invented P0/P1.
'''
 elif id=='06':
  report='''## Verdict: APPROVE
The requested adapters meet the supplied contracts in the reviewed configuration. Ordinary gates, targeted async tests, retained-pointer Miri checks and the instrumented publication model pass. Approval is conditional on callers satisfying the explicit unsafe registration contract and single-writer, one-shot publication precondition.

'''+common+'''
## Memory safety
- memory-scope: REQUIRED (src/registration.rs retained buffer ownership; src/bytes.rs input bounds/alignment).
- miri: PASS (2 existing targeted memory tests plus 2 isolated exact-source tests, both alias models for supplemental tests).
- aliasing: PASS (raw owner preserved until documented synchronous quiescence).
- memory-evidence: miri.log runs tests/memory.rs: ffi_storage_lives_until_unregister and short_slice_rejected on nightly 1.101.0-nightly, commit 48f4b05538b8eca412137042d9647a61e692c6b3, default flags. Supplemental probe preserves src/registration.rs and src/bytes.rs byte-for-byte (probe-source-mapping.json, probe-hashes.json). retained_read_during_unregister_after_move reads after construction and owner movement, and again inside unregister before quiescence; arbitrary_alignment_and_short_inputs checks offsets 0..3 and lengths 0..3. Both supplemental tests pass under -Zmiri-strict-provenance and additionally -Zmiri-tree-borrows, logs probe-stacked.log/probe-tree.log. All Miri commands have 120-second external limits, exit 0. Original source hashes unchanged.
- aliasing-evidence: Box::into_raw transfers allocation ownership and slice metadata to Registration without recreating a Box/reference while callbacks can read. Moving Registration moves only a raw pointer; len/is_empty access scalar metadata without reborrowing allocation contents. Constructor documentation requires read-only callbacks, no free, serialized matching registration, no replacement, synchronous stop and no unwind on unregister. Drop first calls unregister; only after all reads stop does Box::from_raw reconstruct the original allocation exactly once and free with its original Rust allocator. No manual Send/Sync claims. Empty slices are permitted provided callbacks respect the zero length. read_word copies four checked bytes to an aligned local array and uses from_ne_bytes, so it imposes no input alignment. Rust shims validate these stated obligations, not arbitrary foreign implementations; the API explicitly places them on the unsafe caller.

## Concurrency
- async-scope: REQUIRED (Service, approved_pop, stop_worker in src/service.rs).
- deadlocks: PASS (nested_lock_completes; scoped guard drops before snapshot reacquires it).
- cancellation: PASS (cancel_before_approval_preserves_item; explicit Pending poll then drop leaves front item 7).
- task-lifecycle: PASS (stopped_worker_cannot_receive_more_work; started/release/effect handshakes verify termination before return).
- async-evidence: async-targeted.log runs 3 tests with Tokio 1.54.1 current-thread test runtimes and timeout 120 around process, exit 0. nested-lock operation uses a 100ms timeout. Cancellation uses direct polling and noop Waker, not timing guesses. Worker test waits for started signal, calls stop, and verifies release receiver is gone; it bounds the erroneous side-effect path at 100ms. stop_worker aborts AND awaits the JoinHandle, observing destruction/completion. A running spawn_blocking worker cannot be aborted but is still awaited, so completion barrier remains; eventual completion requires its cooperative progress. approved_pop performs no queue mutation before approval and has no suspension after pop. Queue lock contention can lose fairness position on cancellation but not an item. No requirement to complete a cancelled shutdown future is inferred. Exact source hashes in hashes-before/after.json.
- sync-scope: REQUIRED (Published publication in src/publication.rs).
- loom: PASS (publication_is_coherent, 1 model test, completed, loom.log, exit 0).
- synchronization: PASS (single-writer one-shot Release/Acquire handoff).
- model-evidence: cargo test --locked --offline --features model --test publication -- --nocapture; 120-second external watchdog, completed normally. Loom 0.7.2, actual Published source cfg-selects Loom AtomicUsize/AtomicBool, Loom Arc and thread. One spawned writer stores value 42 then ready; concurrent main thread asserts any Some equals 42 before joining, covering the publication boundary without join masking it. No LOOM_* environment variables set; Builder defaults: max_threads 5, max_branches 1000, no permutation/duration/preemption bounds, no checkpoint file. Completion within these model bounds, not a claim of exhaustive real hardware behavior. Independent proof: payload store is sequenced before Release true. Acquire reading true synchronizes with that store, so payload store happens-before subsequent Relaxed payload load. Under one-shot, single-writer use there is no later competing payload write, and coherent atomic load must see the published value. A false flag returns None as allowed. Reuse or multiple writers are outside the stated contract.

## Spec
- spec: PASS (each bullet in REQUIREMENTS.md checked separately against source and targeted tests).
- missing: None. Short/unaligned word reads, retained read-only registration, lock progress, preapproval cancellation, worker termination and coherent one-shot publication all addressed.
- unrequested: Review tooling/knowledge additions support validation; no extra runtime behavior requiring removal found.
- contradictions: None. Ordinary tests avoid UB and unbounded waits for the covered states.

## Findings
No findings.
'''
 else:
  report='''## Verdict: APPROVE
The one-shot publication protocol satisfies REQUIREMENTS.md. The dedicated model completed six executions and independently matches the Release/Acquire ordering argument; all ordinary checks passed.

'''+common+'''
## Memory safety
- memory-scope: NONE (safe std/Loom atomics only; no changed unsafe ownership, FFI or reclamation boundary).
- miri: N/A (no affected memory boundary).
- aliasing: N/A (safe atomic accesses; no raw pointer ownership).
- memory-evidence: N/A; exact src/lib.rs and model source read.
- aliasing-evidence: N/A; no unsafe invariant introduced by these changes.

## Concurrency
- async-scope: NONE (no futures, locks or spawned async tasks in reviewed implementation).
- deadlocks: N/A (straight-line atomic operations).
- cancellation: N/A (no futures).
- task-lifecycle: N/A (no owned async workers).
- async-evidence: N/A; synchronous one-shot publication only.
- sync-scope: REQUIRED (src/lib.rs:13-20, ready/payload publication protocol).
- loom: PASS (publication_model; one test, six completed model executions, loom.log, exit 0).
- synchronization: PASS (matching Release/Acquire establishes payload visibility).
- model-evidence: timeout 120 cargo test --locked --offline --features model --test publication_model -- --nocapture. Loom 0.7.2; exact production operations switch to tracked Loom atomics by feature. Model uses Loom Arc/thread, one writer publish(42), a concurrent prejoin snapshot that asserts any Some is 42, and a postjoin snapshot asserting Some(42). Six executions printed after Builder::check returned; count >1 asserted. The std atomic counts harness executions only and does not replace modeled payload/ready atomics. Builder sets checkpoint_interval=1, max_permutations=None, max_duration=None, preemption_bound=None and checkpoint_file=None. No LOOM_* environment variables; defaults retain max_threads=5 and max_branches=1000. External watchdog was not reached. This is completed bounded model evidence, not all possible hardware behaviors. Independent ordering argument: relaxed payload store precedes Release ready=true; Acquire read of true synchronizes with that sole publication, making payload store happen-before the later relaxed payload load. Atomic coherence plus no subsequent write ensures Some(value). False yields None as required. Single-writer, at-most-once assumption is explicit in both API and requirements; multiple writers/reuse are not valid counterexamples.

## Spec
- spec: PASS (REQUIREMENTS.md: one writer, exactly-once publication; concurrent None allowed; Some equals published value; model exploration required).
- missing: None. Actual prejoin reader checks payload, not only postjoin visibility, and exploration completed.
- unrequested: Review workflow/knowledge changes support validation; no added runtime feature beyond the requested protocol.
- contradictions: None.

## Findings
No findings.
'''
 report+=f'''
## Residual risks
- Scope: origin/main base {base}; HEAD {head}; branch plus staged/unstaged/untracked scope. Tree was clean before and after; no untracked source files. context.log records context.sh output; diff.log contains the full raw base-to-working-tree diff, including review-workflow files. Runtime source/tests and relevant policy/configuration were inspected directly after graph narrowing.
- Preservation: hashes-before.json and hashes-after.json match for all original tracked/untracked files; source-unchanged.log and status-after.log record verification. Graph writes are ignored review cache only. Build targets live outside evidence and source. Probe sources are isolated under reviews where applicable.
- Semver checks: N/A for unpublished 0.1.0 crate (publish=false; no supported release baseline specified). No inferred MSRV validation. Reviewed host is x86_64-unknown-linux-gnu; other targets untested.
- Offline cargo-deny uses existing advisory data and does not establish today's advisory freshness. Passing tests and models are scoped evidence, not universal correctness proofs. Graph/LSP limitations are recorded above.
'''
 (o/'report.md').write_text(report)
 r=subprocess.run(['bash','.agents/skills/rust-pr-review/scripts/check-report.sh',str(o/'report.md')],cwd=p,capture_output=True,text=True);(o/'report-validation.log').write_text(r.stdout+r.stderr);print(id,r.returncode,r.stdout,r.stderr)
