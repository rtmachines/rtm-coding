# Third-party notices

rust-review-kit bundles material from the projects below. Exact upstream commits and
local modifications are listed in `vendored.tsv`. Full license texts are in `licenses/`.

| Component | Source | License | Where in the kit | Modified |
|---|---|---|---|---|
| rust-skills corrected edition | rtmachines/rust-skills @ a1e290d53d43a85421ff16dde23b5f8ec0b48539, © 2025 Leonardo Maldonado | MIT | `codex-template/.agents/skills/rust-skills/` | SKILL.md, rules, LICENSE and CORRECTIONS.json unchanged; LOCAL_CHANGES.md regression instructions link points to the pinned upstream commit; checks and agent configuration omitted |
| rust-best-practices skill | apollographql/skills @ f9843dc, © 2024 Apollo Graph, Inc. | MIT | `template/.claude/skills/rust-best-practices/` | no |
| Smell baseline | rewrite-rs/skills @ ae0fd62, © 2026-Present rewrite.rs | BSD-3-Clause | `template/.claude/skills/rust-pr-review/references/SMELLS.md` | yes: removed one incorrect row, added mapping note |
| Safety pre-check | rewrite-rs/skills @ ae0fd62 | BSD-3-Clause | `…/references/SAFETY-PRECHECK.md` | header note only |
| Spec pass (adapted) | rewrite-rs/skills @ ae0fd62, `REVIEW-PASSES.md` | BSD-3-Clause | `…/references/SPEC-PASS.md` | adapted |
| Axum / gRPC / GraphQL review skills | tailrocks/tailrocks-rust-skills @ 18467d1 | Apache-2.0 | `optional/skills/tailrocks-*-review/` | yes: subset note, cross-references, `agents/` removed |
| Pragmatic Rust Guidelines (rules + checklist) | microsoft/rust-guidelines @ 19723b3, © Microsoft Corporation | MIT | `optional/skills/rust-lib-guidelines/` | checklist links rewritten; SKILL.md written for the kit |

Not bundled, installed as plugins by `.claude/settings.json`:
Trail of Bits `rust-review` and `zeroize-audit` (CC-BY-SA-4.0, trailofbits/skills),
Anthropic `rust-analyzer-lsp`, `code-review`, `pr-review-toolkit` (claude-plugins-official).

BSD-3-Clause notice for rewrite-rs material: redistribution of the modified files keeps the
copyright notice and license text (`licenses/rewrite-rs-skills-BSD-3-Clause.txt`); the
names of rewrite.rs and its contributors are not used to endorse this kit.

Apache-2.0 notice for tailrocks material: modified files carry a note stating the change
(top of each SKILL.md and `vendored.tsv`).

The kit's own files (hooks, agent, `rust-pr-review` skill, installer, docs) may be used,
modified and redistributed freely.

## Codex adaptation

`codex-template/.agents/skills/` contains adapted copies of the Apollo and rewrite-rs
materials above. `codex-optional/skills/` contains adapted copies of the optional
Microsoft and tailrocks materials, under the same respective licenses. Changes
include Codex invocation metadata, explicit review scripts, evidence-first caveats,
and protocol-based routing. Exact copied paths and original pins are in vendored.tsv.
The original copies remain in template/ and optional/. Codex installation does not
install any of the Claude marketplace plugins listed above.
