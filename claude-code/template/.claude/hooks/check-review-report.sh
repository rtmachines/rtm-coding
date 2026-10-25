#!/usr/bin/env bash
# Stop/SubagentStop and PreToolUse(SubagentHandback) report validation adapter.
# Never turn retries into success.
# This validates the declared report; it is not proof that its evidence was run.
set -uo pipefail

input="$(cat)"
mode="${1:-stop}"
block() {
  # Native CLI Stop must receive the JSON decision; exit 2 alone is not a
  # reliable block on supported runtimes. PreToolUse uses its own decision shape.
  local decision
  if [ "$mode" = handback ]; then
    if ! decision="$(jq -n --arg reason "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}')"; then
      decision='{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Review decision formatting failed; repair the hook dependency before retrying."}}'
    fi
  else
    if ! decision="$(jq -n --arg reason "$1" '{decision: "block", reason: $reason}')"; then
      decision='{"decision":"block","reason":"Review decision formatting failed; repair the hook dependency before retrying."}'
    fi
  fi
  # Capture formatter output first so partial JSON on failure cannot contaminate
  # the static, dependency-free blocking response.
  printf '%s\n' "$decision"
  exit 0
}
case "$mode" in
  stop) field='.last_assistant_message' ;;
  handback) field='.tool_input.message' ;;
  *) block 'Unknown review report hook mode.' ;;
esac
if ! printf '%s' "$input" | jq -e 'type == "object"' >/dev/null 2>&1; then
  block 'Malformed review hook payload; report validation cannot pass.'
fi
if [ "$mode" = stop ] && ! printf '%s' "$input" | jq -e '
  .last_assistant_message == null or (.last_assistant_message | type == "string")' >/dev/null; then
  block 'Malformed final-message field; do not replace invalid hook data with an older report.'
fi
message="$(printf '%s' "$input" | jq -r "
  select(type == \"object\") | $field |
  if type == \"string\" then . else \"\" end" 2>/dev/null)"

if [ "$mode" = stop ] && ! grep -q '^## Verdict:' <<< "$message"; then
  # Native handback delivers the report before Stop, whose closing text may be
  # empty. Accept only the last tool call's successfully delivered message, never
  # a cached pass or an arbitrary earlier report. Parse transcript data, not code.
  transcript="$(printf '%s' "$input" | jq -er '
    (.agent_transcript_path // .transcript_path) |
    select(type == "string" and length > 0)' 2>/dev/null)"
  if ! message="$(python3 - "$transcript" <<'PY'
import json
import os
import stat
import sys

MAX_BYTES = 32 * 1024 * 1024
MAX_LINE = 2 * 1024 * 1024
last_call = None
delivered = False
try:
    # O_NONBLOCK prevents an unexpected FIFO from hanging before fstat rejects it.
    descriptor = os.open(sys.argv[1], os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError('transcript must be a bounded regular file')
        consumed = 0
        while True:
            line = stream.readline(MAX_LINE + 1)
            if not line:
                break
            consumed += len(line)
            if len(line) > MAX_LINE or consumed > MAX_BYTES:
                raise ValueError('transcript exceeds review parsing limits')
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError('invalid native transcript record')
            kind = record.get('type')
            if kind not in ('assistant', 'user'):
                continue
            message = record.get('message')
            if not isinstance(message, dict) or message.get('role') != kind:
                raise ValueError('missing native message envelope')
            content = message.get('content')
            if isinstance(content, str):
                # A later human request starts a different review scope.
                if kind == 'user' and content.strip():
                    last_call, delivered = None, False
                continue
            if not isinstance(content, list):
                raise ValueError('invalid native message content')
            for block in content:
                if not isinstance(block, dict):
                    raise ValueError('invalid native content block')
                if kind == 'assistant' and block.get('type') == 'tool_use':
                    last_call, delivered = block, False
                elif kind == 'user' and block.get('type') == 'tool_result':
                    if last_call and block.get('tool_use_id') == last_call.get('id'):
                        if delivered or block.get('is_error', False) is not False:
                            raise ValueError('failed or duplicate tool result')
                        delivered = True
                elif kind == 'user' and block.get('type') != 'tool_result':
                    last_call, delivered = None, False
    if not last_call or not delivered or last_call.get('name') != 'SubagentHandback':
        raise ValueError('last tool call is not a successful SubagentHandback')
    if not isinstance(last_call.get('id'), str) or not last_call['id']:
        raise ValueError('missing tool call identifier')
    arguments = last_call.get('input')
    report = arguments.get('message') if isinstance(arguments, dict) else None
    if not isinstance(report, str) or not report.strip():
        raise ValueError('missing handback report')
    print(report)
except (OSError, ValueError, UnicodeError) as error:
    print(f'Cannot recover a delivered review report: {error}', file=sys.stderr)
    sys.exit(1)
PY
  )"; then
    block 'Stop has no complete report or verifiable last handback. Emit the full report; no review success was recorded.'
  fi
fi
if ! grep -q '[^[:space:]]' <<< "$message"; then
  block 'Review report unavailable or hook payload malformed. Emit a complete report with explicit evidence gaps; missing output cannot pass review.'
fi

hook_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project="${CLAUDE_PROJECT_DIR:-$(dirname -- "$(dirname -- "$hook_dir")")}"
validator="$project/.claude/skills/rust-pr-review/scripts/check-report.sh"
if [ ! -f "$validator" ]; then
  block 'Review report validator is missing. Restore .claude/skills/rust-pr-review/scripts/check-report.sh; this review has not passed validation.'
fi

if ! validation="$(printf '%s\n' "$message" | bash "$validator" 2>&1)"; then
  block "$validation
Correct the report and resend it. Use REQUEST_CHANGES for confirmed defects, ESCALATE for unresolved safety risk, or INCOMPLETE for ordinary missing checks. Do not repair project source merely to finish a review."
fi
