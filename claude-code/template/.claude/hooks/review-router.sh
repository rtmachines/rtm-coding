#!/usr/bin/env bash
# UserPromptSubmit: when the user asks for a review in a Rust repo, steer Claude to /rust-pr-review.
set -uo pipefail
prompt="$(jq -r '.prompt // ""' 2>/dev/null)"
[ -f "${CLAUDE_PROJECT_DIR:-.}/Cargo.toml" ] || exit 0
case "$prompt" in /rust-pr-review*|/rust-review:*|/code-review*) exit 0;; esac
if printf '%s' "$prompt" | grep -qiE '(^|[^[:alnum:]])(review|code ?review|przegl[^ ]*d|zrecenzuj|sprawd[^ ]* (pr|zmiany|kod|diff)|pr)([^[:alnum:]]|$)'; then
  jq -n '{hookSpecificOutput: {hookEventName: "UserPromptSubmit",
    additionalContext: "Use the rust-pr-review skill for this Rust review (optional base ref, then request / acceptance criteria). Follow its evidence and report contract. ESCALATE identifies unresolved risks and closure evidence; invoke a specialist only if available and authorized. Do not automatically install tools, run a plugin, fix the reviewed source or publish comments."}}'
fi
exit 0
