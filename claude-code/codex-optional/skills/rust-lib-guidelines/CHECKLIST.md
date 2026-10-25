<!-- Copyright (c) Microsoft Corporation. Licensed under the MIT license. -->

# Checklist

- **Universal**
  - [ ] Follow the upstream guidelines ([M-UPSTREAM-GUIDELINES])
  - [ ] Use static verification ([M-STATIC-VERIFICATION])
  - [ ] Lint overrides should use `#[expect]` ([M-LINT-OVERRIDE-EXPECT])
  - [ ] Public types are Debug ([M-PUBLIC-DEBUG])
  - [ ] Public types meant to be read are Display ([M-PUBLIC-DISPLAY])
  - [ ] If in doubt, split the crate ([M-SMALLER-CRATES])
  - [ ] Names are free of weasel words ([M-WEASEL-WORDS])
  - [ ] Names of items are short ([M-SHORT-NAMES])
  - [ ] Prefer regular over associated functions ([M-REGULAR-FN])
  - [ ] Magic values are documented ([M-DOCUMENTED-MAGIC])
  - [ ] Use structured logging with message templates ([M-LOG-STRUCTURED])
- **Library / Interoperability**
  - [ ] Types are Send ([M-TYPES-SEND])
  - [ ] Native escape hatches ([M-ESCAPE-HATCHES])
  - [ ] Don't leak external types ([M-DONT-LEAK-TYPES])
  - [ ] Items come from their original crate ([M-FOREIGN-REEXPORTS])
  - [ ] Accept `impl AsRef<>` where feasible ([M-IMPL-ASREF])
  - [ ] Accept `impl RangeBounds<>` where feasible ([M-IMPL-RANGEBOUNDS])
  - [ ] Accept `impl 'IO'` where feasible ('sans IO') ([M-IMPL-IO])
- **Library / UX**
  - [ ] Abstractions don't visibly nest ([M-SIMPLE-ABSTRACTIONS])
  - [ ] Avoid smart pointers and wrappers in APIs ([M-AVOID-WRAPPERS])
  - [ ] Prefer types over generics, generics over dyn traits ([M-DI-HIERARCHY])
  - [ ] Errors are canonical structs ([M-ERRORS-CANONICAL-STRUCTS])
  - [ ] Canonical error conversion uses `From`, not `map_err` ([M-FROM-ERROR])
  - [ ] Complex type construction has builders ([M-INIT-BUILDER])
  - [ ] Complex type initialization hierarchies are cascaded ([M-INIT-CASCADED])
  - [ ] Services are Clone ([M-SERVICES-CLONE])
  - [ ] Essential functionality should be inherent ([M-ESSENTIAL-FN-INHERENT])
  - [ ] Modules are balanced in size and scope ([M-BALANCED-MODULES])
  - [ ] Don't define preludes ([M-NO-PRELUDE])
  - [ ] Parameter ordering is consistent ([M-PARAMETER-CONSISTENCY])
  - [ ] Collections implement the appropriate iter traits ([M-COLLECTION-TRAITS])
  - [ ] Functions are `async` over returning a Future ([M-ASYNC-FN])
- **Library / Resilience**
  - [ ] I/O and system calls are mockable ([M-MOCKABLE-SYSCALLS])
  - [ ] Test utilities are feature gated ([M-TEST-UTIL])
  - [ ] Integration tests live under `tests/` ([M-INTEGRATION-TESTS])
  - [ ] Use the proper type family ([M-STRONG-TYPES])
  - [ ] Newtypes guard their invariants ([M-STRONG-TYPES-GUARD])
  - [ ] Builders validate in final `.build()` ([M-BUILD-RESULT])
  - [ ] Don't glob re-export items ([M-NO-GLOB-REEXPORTS])
  - [ ] Avoid statics ([M-AVOID-STATICS])
  - [ ] Production code uses telemetry, not println ([M-LOG-NOT-PRINT])
- **Library / Building**
  - [ ] Libraries work out of the box ([M-OOBE])
  - [ ] Native `-sys` crates compile without dependencies ([M-SYS-CRATES])
  - [ ] Features are additive ([M-FEATURES-ADDITIVE])
- **Macros**
  - [ ] Macros are a last resort ([M-MACRO-LAST-RESORT])
  - [ ] Prefer 'macros by example' over proc macros ([M-EXAMPLE-OVER-PROC])
  - [ ] Macros don't lie about signatures ([M-MACROS-DONT-LIE])
  - [ ] Macros assume main crate ([M-MACRO-MAIN-CRATE])
  - [ ] Pin supporting proc macro crates ([M-MACRO-VERSION-PIN])
  - [ ] Third party items come from hidden `_private` module ([M-MACRO-HELPERS])
  - [ ] Proc macros should have separate impl crate incl. tests ([M-PROC-IMPL])
  - [ ] Proc macros don't produce implied or hidden items ([M-PROC-IMPLIED-ITEMS])
- **Applications**
  - [ ] Use mimalloc for apps ([M-MIMALLOC-APPS])
  - [ ] Applications may use Anyhow or derivatives ([M-APP-ERROR])
  - [ ] Applications target highest viable target-cpu ([M-TARGET-CPU])
- **FFI**
  - [ ] Isolate DLL state between FFI libraries ([M-ISOLATE-DLL-STATE])
  - [ ] Business logic belongs in core crates, FFI only translates ([M-FFI-TRANSLATES])
  - [ ] FFI crates follow established naming conventions ([M-FFI-NAMING])
- **Correctness**
  - [ ] Unsafe needs reason, should be avoided ([M-UNSAFE])
  - [ ] Unsafe implies undefined behavior ([M-UNSAFE-IMPLIES-UB])
  - [ ] All code must be sound ([M-UNSOUND])
  - [ ] Panic means 'stop the program' ([M-PANIC-IS-STOP])
  - [ ] Detected programming bugs are panics, not errors ([M-PANIC-ON-BUG])
  - [ ] Panic continuation is last resort ([M-PANIC-CONTINUATION])
  - [ ] Custom panics have a helpful message ([M-PANIC-MESSAGE])
- **Performance**
  - [ ] Optimize for throughput, avoid empty cycles ([M-THROUGHPUT])
  - [ ] Identify, profile, optimize the hot path early ([M-HOTPATH])
  - [ ] Long-running tasks should have yield points ([M-YIELD-POINTS])
  - [ ] Reuse allocations where possible ([M-MEM-REUSE])
  - [ ] Library telemetry does not tank performance ([M-LOG-OVERHEAD])
  - [ ] Nested type hierarchies should avoid needless indirection ([M-AVOID-INDIRECTION])
  - [ ] Use boxed slices and strings for immutable owned sequences ([M-BOX-DST])
  - [ ] Shrink collections to fit after building ([M-SHRINK-TO-FIT])
  - [ ] Use a fast hasher where possible ([M-FAST-HASHER])
  - [ ] Collections are created with sufficient initial capacity ([M-INITIAL-CAPACITY])
  - [ ] Hot `async` functions reduce stack size ([M-ASYNC-STACK-SIZE])
- **Project**
  - [ ] Common settings come from the workspace Cargo.toml ([M-CARGO-WORKSPACE])
  - [ ] The workspace lists and versions all crates ([M-CRATES-IN-WORKSPACE])
  - [ ] All crates are siblings in one folder ([M-CRATES-FLAT-FOLDER])
  - [ ] New crates target latest edition ([M-LATEST-EDITION])
  - [ ] MSRV is conservatively updated ([M-MSRV])
- **Documentation**
  - [ ] First sentence is one line; approx. 15 words ([M-FIRST-DOC-SENTENCE])
  - [ ] Has comprehensive module documentation ([M-MODULE-DOCS])
  - [ ] Documentation has canonical sections ([M-CANONICAL-DOCS])
  - [ ] Mark `pub use` items with `#[doc(inline)]` ([M-DOC-INLINE])
- **AI**
  - [ ] Design with AI use in mind ([M-DESIGN-FOR-AI])
  - [ ] Items are only visible through one path ([M-SINGLE-ITEM-PATH])
  - [ ] Avoid meta design documentation ([M-NO-META-DESIGN-DOCUMENTATION])
  - [ ] Tests do not assert ground truth ([M-TAUTOLOGICAL-TESTS])
  - [ ] Rust code solves Rust problems ([M-RUST-SHAPED])

<!-- Universal  -->
[M-UPSTREAM-GUIDELINES]: rules/M-UPSTREAM-GUIDELINES.md
[M-STATIC-VERIFICATION]: rules/M-STATIC-VERIFICATION.md
[M-LINT-OVERRIDE-EXPECT]: rules/M-LINT-OVERRIDE-EXPECT.md
[M-PUBLIC-DEBUG]: rules/M-PUBLIC-DEBUG.md
[M-PUBLIC-DISPLAY]: rules/M-PUBLIC-DISPLAY.md
[M-SMALLER-CRATES]: rules/M-SMALLER-CRATES.md
[M-WEASEL-WORDS]: rules/M-WEASEL-WORDS.md
[M-SHORT-NAMES]: rules/M-SHORT-NAMES.md
[M-REGULAR-FN]: rules/M-REGULAR-FN.md
[M-DOCUMENTED-MAGIC]: rules/M-DOCUMENTED-MAGIC.md
[M-LOG-STRUCTURED]: rules/M-LOG-STRUCTURED.md
[M-LOG-NOT-PRINT]: rules/M-LOG-NOT-PRINT.md

<!-- Libs -->
[M-TYPES-SEND]: rules/M-TYPES-SEND.md
[M-DONT-LEAK-TYPES]: rules/M-DONT-LEAK-TYPES.md
[M-FOREIGN-REEXPORTS]: rules/M-FOREIGN-REEXPORTS.md
[M-ESCAPE-HATCHES]: rules/M-ESCAPE-HATCHES.md
[M-STRONG-TYPES]: rules/M-STRONG-TYPES.md
[M-STRONG-TYPES-GUARD]: rules/M-STRONG-TYPES-GUARD.md
[M-NO-GLOB-REEXPORTS]: rules/M-NO-GLOB-REEXPORTS.md
[M-ESSENTIAL-FN-INHERENT]: rules/M-ESSENTIAL-FN-INHERENT.md
[M-MOCKABLE-SYSCALLS]: rules/M-MOCKABLE-SYSCALLS.md
[M-SIMPLE-ABSTRACTIONS]: rules/M-SIMPLE-ABSTRACTIONS.md
[M-AVOID-WRAPPERS]: rules/M-AVOID-WRAPPERS.md
[M-DI-HIERARCHY]: rules/M-DI-HIERARCHY.md
[M-ERRORS-CANONICAL-STRUCTS]: rules/M-ERRORS-CANONICAL-STRUCTS.md
[M-FROM-ERROR]: rules/M-FROM-ERROR.md
[M-INIT-BUILDER]: rules/M-INIT-BUILDER.md
[M-BUILD-RESULT]: rules/M-BUILD-RESULT.md
[M-INIT-CASCADED]: rules/M-INIT-CASCADED.md
[M-SERVICES-CLONE]: rules/M-SERVICES-CLONE.md
[M-IMPL-ASREF]: rules/M-IMPL-ASREF.md
[M-IMPL-RANGEBOUNDS]: rules/M-IMPL-RANGEBOUNDS.md
[M-IMPL-IO]: rules/M-IMPL-IO.md
[M-BALANCED-MODULES]: rules/M-BALANCED-MODULES.md
[M-NO-PRELUDE]: rules/M-NO-PRELUDE.md
[M-PARAMETER-CONSISTENCY]: rules/M-PARAMETER-CONSISTENCY.md
[M-COLLECTION-TRAITS]: rules/M-COLLECTION-TRAITS.md
[M-ASYNC-FN]: rules/M-ASYNC-FN.md
[M-TEST-UTIL]: rules/M-TEST-UTIL.md
[M-INTEGRATION-TESTS]: rules/M-INTEGRATION-TESTS.md
[M-AVOID-STATICS]: rules/M-AVOID-STATICS.md
[M-OOBE]: rules/M-OOBE.md
[M-SYS-CRATES]: rules/M-SYS-CRATES.md
[M-FEATURES-ADDITIVE]: rules/M-FEATURES-ADDITIVE.md

<!-- Apps -->
[M-APP-ERROR]: rules/M-APP-ERROR.md
[M-MIMALLOC-APPS]: rules/M-MIMALLOC-APPS.md
[M-TARGET-CPU]: rules/M-TARGET-CPU.md

<!-- FFI -->
[M-ISOLATE-DLL-STATE]: rules/M-ISOLATE-DLL-STATE.md
[M-FFI-TRANSLATES]: rules/M-FFI-TRANSLATES.md
[M-FFI-NAMING]: rules/M-FFI-NAMING.md

<!-- Correctness -->
[M-UNSAFE]: rules/M-UNSAFE.md
[M-UNSAFE-IMPLIES-UB]: rules/M-UNSAFE-IMPLIES-UB.md
[M-UNSOUND]: rules/M-UNSOUND.md
[M-PANIC-IS-STOP]: rules/M-PANIC-IS-STOP.md
[M-PANIC-ON-BUG]: rules/M-PANIC-ON-BUG.md
[M-PANIC-CONTINUATION]: rules/M-PANIC-CONTINUATION.md
[M-PANIC-MESSAGE]: rules/M-PANIC-MESSAGE.md

<!-- Performance -->
[M-HOTPATH]: rules/M-HOTPATH.md
[M-THROUGHPUT]: rules/M-THROUGHPUT.md
[M-YIELD-POINTS]: rules/M-YIELD-POINTS.md
[M-MEM-REUSE]: rules/M-MEM-REUSE.md
[M-LOG-OVERHEAD]: rules/M-LOG-OVERHEAD.md
[M-AVOID-INDIRECTION]: rules/M-AVOID-INDIRECTION.md
[M-BOX-DST]: rules/M-BOX-DST.md
[M-SHRINK-TO-FIT]: rules/M-SHRINK-TO-FIT.md
[M-FAST-HASHER]: rules/M-FAST-HASHER.md
[M-INITIAL-CAPACITY]: rules/M-INITIAL-CAPACITY.md
[M-ASYNC-STACK-SIZE]: rules/M-ASYNC-STACK-SIZE.md

<!-- Project -->
[M-CARGO-WORKSPACE]: rules/M-CARGO-WORKSPACE.md
[M-CRATES-IN-WORKSPACE]: rules/M-CRATES-IN-WORKSPACE.md
[M-CRATES-FLAT-FOLDER]: rules/M-CRATES-FLAT-FOLDER.md
[M-LATEST-EDITION]: rules/M-LATEST-EDITION.md
[M-MSRV]: rules/M-MSRV.md

<!-- Docs -->
[M-FIRST-DOC-SENTENCE]: rules/M-FIRST-DOC-SENTENCE.md
[M-MODULE-DOCS]: rules/M-MODULE-DOCS.md
[M-CANONICAL-DOCS]: rules/M-CANONICAL-DOCS.md
[M-DOC-INLINE]: rules/M-DOC-INLINE.md

<!-- Macros -->
[M-MACRO-LAST-RESORT]: rules/M-MACRO-LAST-RESORT.md
[M-EXAMPLE-OVER-PROC]: rules/M-EXAMPLE-OVER-PROC.md
[M-MACROS-DONT-LIE]: rules/M-MACROS-DONT-LIE.md
[M-MACRO-MAIN-CRATE]: rules/M-MACRO-MAIN-CRATE.md
[M-MACRO-VERSION-PIN]: rules/M-MACRO-VERSION-PIN.md
[M-MACRO-HELPERS]: rules/M-MACRO-HELPERS.md
[M-PROC-IMPL]: rules/M-PROC-IMPL.md
[M-PROC-IMPLIED-ITEMS]: rules/M-PROC-IMPLIED-ITEMS.md

<!-- AI -->
[M-DESIGN-FOR-AI]: rules/M-DESIGN-FOR-AI.md
[M-SINGLE-ITEM-PATH]: rules/M-SINGLE-ITEM-PATH.md
[M-NO-META-DESIGN-DOCUMENTATION]: rules/M-NO-META-DESIGN-DOCUMENTATION.md
[M-TAUTOLOGICAL-TESTS]: rules/M-TAUTOLOGICAL-TESTS.md
[M-RUST-SHAPED]: rules/M-RUST-SHAPED.md
