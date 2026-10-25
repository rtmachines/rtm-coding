---
name: rust-lib-guidelines
description: Review a public Rust library crate against the Microsoft Pragmatic Rust Guidelines checklist (M-* rules). Use only when the user explicitly asks for a library/API guideline review.
license: MIT
metadata:
  source: microsoft/rust-guidelines
  commit: 19723b3
---

# Rust library guideline review (Microsoft Pragmatic Rust Guidelines)

Read-only. Never edit files.

1. Read `CHECKLIST.md`. Mark which sections apply to the target (Universal always;
   Library sections only for crates meant to be consumed by other crates; Apps,
   FFI, Macros, AI only when relevant).
2. For each applicable item that the diff or crate plausibly touches, open only
   that rule file in `rules/M-<ID>.md` and judge against its text. Do not load
   all rules.
3. Report only violations with evidence, in the format used by
   `$rust-pr-review`: `- [P0..P3] path.rs:LINE - <defect>. Rule: M-<ID>. Fix: <...>`.
   Map severity with the project's `REVIEW.md`. Where an M-rule conflicts with
   `REVIEW.md` or the repo lint configuration, the repo wins; mention the
   conflict as a P3 note.
4. End with `## Not checked` listing applicable checklist items you could not
   judge from the available code.

Rule texts are © Microsoft Corporation, MIT License (see the kit's `licenses/`).
