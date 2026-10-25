# Verify rust-analyzer through rust-lsp

At the start of Rust review, discover the `rust-lsp` skill and read its instructions
if available. Discover the current Rust LSP tool APIs; do not invent tool names or
assume that `rust-analyzer --version`, a skill listing or a plugin registration
proves that the integration can analyze this project.

Use a read-only workspace probe exposed by the integration (for example
`analyzer_status` with the absolute `workspace_root`, if available). Check its
payload as well as its error status: a response describing failed workspace loading
is not success. If no status API exists, use a read-only semantic query on a known
symbol in an in-scope Rust file. Allow bounded initialization using the integration's
documented behavior; do not retry indefinitely. Record failures, timeouts, partial
indexing, unsupported features and unresolved macros.

If the skill or APIs are missing, follow the rust-lsp setup instructions only within
existing authorization. Review alone does not authorize installation: its setup may
install a rustup component and a Cargo package from Git. If setup is unauthorized,
fails or still exposes no usable APIs, record UNAVAILABLE and continue source review.
Do not change global configuration or install packages merely to turn this status green.

When available, use semantic queries for the reviewed symbols: definitions,
references, hover/types or implementations, according to the exposed APIs. Read the
resolved source. Do not rename symbols or apply workspace edits during review.
An empty result, tool discovery or a health probe alone does not establish actual
semantic use. Count use only after a successful relevant query with interpretable
results; record its target and what it established.

## Report

Always include `## Tooling` in a standalone report:

- `rust-lsp: AVAILABLE` means a workspace probe or semantic query confirmed usable
  analysis for the reviewed scope. Otherwise use `UNAVAILABLE` with the reason.
- `lsp-used: YES` means at least one relevant semantic query succeeded. A successful
  health check alone means `NO`. If the integration later fails, describe its partial
  coverage; retain AVAILABLE/YES only for the scope actually analyzed successfully.
- `lsp-evidence:` names the tool, absolute workspace, target file/symbol and observed
  result or log. When unavailable, describe discovery/setup attempts and their outcome.
- `lsp-limitations:` states fallback coverage and remaining gaps. `NONE` is allowed
  only with a reason after actual semantic use; it is never a default for an omitted LSP.

Example when no integration is exposed:

```text
## Tooling
- rust-lsp: UNAVAILABLE (no Rust LSP APIs exposed)
- lsp-used: NO (no semantic calls executed)
- lsp-evidence: Tool discovery found no rust-lsp APIs; setup not authorized.
- lsp-limitations: Read definitions, callers and tests directly; inferred types and macro expansion were not verified by LSP.
```

Absence of LSP is not itself a code defect and does not automatically require
ESCALATE. Continue with exact-source inspection and existing compiler/test evidence.
If this resolves the review obligations, APPROVE remains possible with the limitation
disclosed. If ordinary required analysis remains incomplete, use INCOMPLETE; unresolved
memory/concurrency safety requires ESCALATE under the existing rules. Honor project
policy if it explicitly requires LSP. LSP never replaces Cargo gates, Miri or Loom.

The report validator checks declarations and consistency, not whether MCP calls really
happened. Inspect the recorded tool evidence before trusting a claim of semantic use.
