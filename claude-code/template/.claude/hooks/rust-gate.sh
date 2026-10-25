#!/usr/bin/env bash
# Native adapter to the shared, uncached gate runner.
# commit: only gate commits in this project. stop: legacy report-only adapter.
# Failing code can still have a valid REQUEST_CHANGES/ESCALATE/INCOMPLETE report.
set -uo pipefail

mode="${1:-stop}"
input="$(cat)"
hook_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

case "$mode" in
  stop)
    # Kept for existing installations; new settings do not install a global Stop.
    # Ordinary completion must not trigger Cargo or ask a reviewer to fix code.
    message="$(printf '%s' "$input" | jq -r 'if type == "object" and (.last_assistant_message | type == "string") then .last_assistant_message else "" end' 2>/dev/null)"
    if [[ "$message" == *'## Verdict:'* ]]; then
      printf '%s' "$input" | bash "$hook_dir/check-review-report.sh"
      exit $?
    fi
    exit 0
    ;;
  commit) ;;
  *) echo "Unknown Rust gate mode: $mode" >&2; exit 2 ;;
esac

if ! command="$(printf '%s' "$input" | jq -er '
  select(type == "object") | .tool_input.command |
  select(type == "string" and test("[^[:space:]]"))' 2>/dev/null)"; then
  echo 'Cannot identify the proposed commit from the hook payload.' >&2
  exit 2
fi

# Match executable position, never words in e.g. echo or git show arguments.
# Alternative Git roots cannot safely share the current project gate result.
classification="${command//$'\n'/;}"
prefixed_commit='(^|[;&|])[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:];|&]+[[:space:]]+)+git[[:space:]]+commit([[:space:]]|$)'
wrapped_commit='(^|[;&|])[[:space:]]*(env|command|builtin)[[:space:]]+[^;&|]*git[[:space:]]+commit([[:space:]]|$)'
option_commit='(^|[;&|])[[:space:]]*git[[:space:]]+-[^;&|]*[[:space:]]commit([[:space:]]|$)'
direct_commit='(^|[;&|])[[:space:]]*git[[:space:]]+commit([[:space:]]|$)'
if [[ "$classification" =~ $prefixed_commit || "$classification" =~ $wrapped_commit || "$classification" =~ $option_commit ]] ||
   { [[ "$classification" =~ $direct_commit ]] && [[ "$classification" == *';'* || "$classification" == *'&'* || "$classification" == *'|'* ]]; }; then
  echo 'Commit blocked: use a standalone git commit from the intended project directory, without environment prefixes, shell composition or Git options. Its gates must validate the same tree and configuration.' >&2
  exit 2
fi
[[ "$command" =~ ^[[:space:]]*git[[:space:]]+commit([[:space:]]|$) ]] || exit 0

project="${CLAUDE_PROJECT_DIR:-$(dirname -- "$(dirname -- "$hook_dir")")}"
cd -- "$project" 2>/dev/null || { echo 'Cannot enter the project to verify commit gates.' >&2; exit 2; }
# A hook may run with a project root while Bash has changed to another repository.
command_cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)"
if [ -n "$command_cwd" ]; then
  project_root="$(git rev-parse --show-toplevel 2>/dev/null)"
  command_root="$(git -C "$command_cwd" rev-parse --show-toplevel 2>/dev/null)"
  if [ -z "$project_root" ] || [ "$command_root" != "$project_root" ]; then
    echo 'Commit blocked: command directory differs from the project being gated. Run the commit in the intended project.' >&2
    exit 2
  fi
fi
[ -f Cargo.toml ] || exit 0
runner="$project/.claude/skills/rust-pr-review/scripts/gates.sh"
if [ ! -f "$runner" ]; then
  echo 'Commit blocked: the Rust gate runner is missing.' >&2
  exit 2
fi

# Always run fresh: features, configuration, toolchain and advisory state can
# change independently of a source diff. No success cache or retry bypass.
if ! bash "$runner" >&2; then
  echo 'Commit blocked: Rust gates failed or required checks are unavailable. Inspect the gate output before retrying.' >&2
  exit 2
fi
