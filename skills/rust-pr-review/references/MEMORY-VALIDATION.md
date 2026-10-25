# Targeted memory validation

Required for changed unsafe/FFI code and safe callers that change its lifetime,
ownership, aliasing or synchronization assumptions. A grep for new `unsafe` tokens
alone is not sufficient to determine scope. A safe-only change with no affected
unsafe invariant may report memory-scope NONE with a reason.

## Establish the invariant and exercise it

For each affected memory boundary, record the owner, allocation/free pairing,
origin and validity of retained pointers, allowed reads/writes, lifetime, alignment,
and thread/reentrancy obligations. Read the implementation and actual callers.

Check aliasing separately from liveness: a stable address and a live allocation do
not establish that an earlier pointer remains usable. Trace owner moves, reference
creation and reborrowing, mutable/exclusive access, callbacks and destruction. Include
Box/Vec ownership transitions, raw-pointer conversions, pinning assumptions and any
manual Send/Sync proof. A SAFETY comment is a claim to verify, not evidence by itself.

Map each relevant invariant to a named targeted test. For retained FFI pointers,
exercise access after the constructor returns and the owner moves, while the owner
is alive, during deregistration when the contract permits it, and until callback
quiescence. Check bounds/alignment and exceptional paths where applicable. Tests must
respect the unsafe API caller's documented obligations; violations by an invalid
mock do not prove a defect in the wrapper.

Run these tests under Miri on the reviewed source. Zero tests or unrelated tests
are NOT RUN for this memory gate, even if cargo exits successfully. Record the test
names, exercised paths, count, exact command, toolchain/commit, MIRIFLAGS, result and
log path. A targeted PASS is necessary for approval, but is not a soundness proof.

If adequate tests are absent and execution is authorized, build bounded probes in
an isolated temporary workspace. Copy/import the exact reviewed implementation,
record source hashes and dependencies/configuration, and write only the harness
there. Do not repair or simplify the implementation to make it testable. Do not edit
the reviewed repository. If this requires unavailable permissions or cannot preserve
the relevant behavior, report the gap and ESCALATE rather than declare safety.

For Miri setup, check available toolchains/components and existing sysroot first.
Miri may install rust-src during first-use setup; follow session permissions and do
not let a supposedly read-only check silently install components when prohibited.
Use a timeout. Run suspected UB only in Miri or an authorized diagnostic environment,
never as an ordinary native reproducer.

## FFI evidence boundaries

Miri cannot validate arbitrary native foreign libraries. A Rust callback or shim can
exercise the wrapper's pointer/lifetime behavior only when it obeys the documented
ABI and contract. State this limit. Missing provider guarantees (retention,
quiescence, allocator ownership, thread affinity, unwinding) remain unresolved even
if a guessed shim passes. Request the versioned SDK contract or implementation audit
needed to close the question; do not invent a vendor defect.

## Failures and conflicting models

Keep the original failing log. Distinguish demonstrated invalid accesses (for example
freed allocation or out-of-bounds) from experimental alias-model diagnostics. For an
aliasing diagnostic, inspect the creation/invalidation/access chain and, where useful
and supported, compare Stacked Borrows with Tree Borrows on the same source and test.
Record both configurations. Do not turn off checks to obtain a passing result, and do
not choose whichever model passes as proof. Disagreement means aliasing UNRESOLVED
and verdict ESCALATE pending a justified provenance argument or a validated redesign.

For any proposed unsafe/FFI fix, re-check both ownership and aliasing. Keeping an
allocation alive is not enough. An untested suggested fix must be labeled a candidate;
do not claim that it closes the safety issue. Test authorized fixes in a separate copy
and keep original and modified evidence distinct.

## Report and verdict

Fill `## Memory safety` for every review. NONE means no affected memory boundary;
REQUIRED needs targeted Miri evidence and an aliasing argument. Missing tests,
unsupported operations, unknown external guarantees or conflicting models mean
UNRESOLVED and ESCALATE. A clearly demonstrated violation may use FAIL and
REQUEST_CHANGES. If both a proved defect and unresolved risks exist, use ESCALATE and
list the proved blockers too. Never convert missing evidence into a fabricated P1.

References: [Miri](https://github.com/rust-lang/miri) and
[unsafe-code guidelines](https://github.com/rust-lang/unsafe-code-guidelines).
