#!/usr/bin/env bash
# Review scope guard, NOT a sandbox. Cargo/build scripts and executables can write.
# Nothing is auto-approved. Commands outside the obvious mutation checks below
# retain normal session permissions, including already authorised isolated probes.
set -uo pipefail

input="$(cat)"
deny() {
  local decision
  if ! decision="$(jq -n --arg reason "$1" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}')"; then
    decision='{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Review decision formatting failed; repair the hook dependency before retrying."}}'
  fi
  printf '%s\n' "$decision"
  exit 0
}
if ! command="$(printf '%s' "$input" | jq -er '
  select(type == "object") | .tool_input.command |
  select(type == "string" and test("[^[:space:]]"))' 2>/dev/null)"; then
  deny 'Cannot validate the review command: missing or malformed hook payload.'
fi

# Shell programs, variables and heredocs remain governed by normal permissions.
# Never inspect their embedded Rust/Python text as if it were shell redirection.
# This deliberately narrow guard is not a shell parser or an isolation boundary.
case "$command" in
  *$'\n'*|*';'*|*'&'*|*'|'*|*'$'*|*'`'*|*'('*|*')'*|*'{'*|*'}'*|*'\\'*|*'<<'*) exit 0 ;;
esac

project="${CLAUDE_PROJECT_DIR:-$PWD}"
command_cwd="$(printf '%s' "$input" | jq -r 'if .cwd | type == "string" then .cwd else empty end' 2>/dev/null)"
command_cwd="${command_cwd:-$PWD}"
path_in_project() {
  # Resolve only a literal path in a simple command. The runtime cwd matters:
  # relative probe/log paths may belong to an authorised external harness.
  python3 - "$project" "$command_cwd" "$1" <<'PY_PATH'
import os
import sys
try:
    project = os.path.realpath(sys.argv[1])
    target = os.path.realpath(os.path.join(sys.argv[2], sys.argv[3]))
    sys.exit(0 if os.path.commonpath((project, target)) == project else 1)
except (OSError, ValueError):
    sys.exit(1)
PY_PATH
}

# Unambiguous direct Git/Cargo mutations in the reviewed project stay denied.
# The same executables in an external harness retain existing permissions.
mutation='^[[:space:]]*(git[[:space:]]+(commit|push|checkout|reset|restore|stash|add|rm|clean|switch|rebase|merge|apply|config|init)|cargo[[:space:]]+(\+[^[:space:]]+[[:space:]]+)?(add|remove|update|install|uninstall|publish|upgrade|fix))([[:space:]]|$)'
if [[ "$command" =~ $mutation ]] && path_in_project .; then
  deny 'This command explicitly mutates the reviewed project dependencies or Git state. Project edits belong in the parent editing session.'
fi
if [[ "$command" =~ ^[[:space:]]*cargo[[:space:]] ]] && path_in_project .; then
  if [[ "$command" =~ --(fix|allow-dirty|bless)([[:space:]=]|$) ]] ||
     { [[ "$command" =~ ^[[:space:]]*cargo[[:space:]]+(\+[^[:space:]]+[[:space:]]+)?fmt([[:space:]]|$) ]] &&
       ! [[ "$command" =~ [[:space:]]--check([[:space:]]|$) ]]; }; then
    deny 'Source-changing Cargo commands are outside review scope; formatting must use --check.'
  fi
fi

# Quoted program bodies and quoted/escaped paths need shell understanding. Defer
# them instead of mistaking e.g. a Rust return arrow for an output redirect.
case "$command" in *\"*|*\'*) exit 0;; esac
file_mutation='^[[:space:]]*(rm|mv|cp|touch|mkdir|chmod|chown|tee)([[:space:]]|$)'
inplace='^[[:space:]]*(sed|perl)[[:space:]]+([^[:space:]]+[[:space:]]+)*-[[:alpha:]]*i'
if [[ "$command" =~ $file_mutation ]] || [[ "$command" =~ $inplace ]]; then
  read -r -a words <<< "$command"
  destination="${words[${#words[@]}-1]}"
  if [[ "$destination" != -* ]] && path_in_project "$destination"; then
    deny 'This simple command writes into the reviewed project; use the authorised isolated evidence directory.'
  fi
fi

# Only literal destinations are examined. Variable/composed commands returned
# above; anything outside the reviewed project retains normal permissions.
output_option='--output[=[:space:]]+([^[:space:]]+)'
if [[ "$command" =~ ^[[:space:]]*git[[:space:]]+diff([[:space:]]|$) ]] && [[ "$command" =~ $output_option ]]; then
  destination="${BASH_REMATCH[1]}"
  path_in_project "$destination" && deny 'git diff output must not overwrite the reviewed project.'
fi
redirects="$command"
output_redirect='>>?[[:space:]]*([^[:space:]]+)'
while [[ "$redirects" =~ $output_redirect ]]; do
  destination="${BASH_REMATCH[1]}"
  matched="${BASH_REMATCH[0]}"
  path_in_project "$destination" && deny 'Literal output redirection into the reviewed project is outside review scope.'
  redirects="${redirects#*"$matched"}"
done

# No permissionDecision: preserve the user's current native permissions.
exit 0
