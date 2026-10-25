#!/usr/bin/env bash
# Preserve Clippy's exit status independently of optional diagnostic presentation.
set -uo pipefail
export CARGO_TERM_COLOR=never
if [[ ${RUST_REVIEWDOG:-0} != 1 ]]; then
  exec cargo clippy "$@"
fi
logs=$(mktemp -d "${TMPDIR:-/tmp}/rust-review-clippy.XXXXXXXX") || exit 2
printf 'Clippy/reviewdog evidence: %s\n' "$logs" >&2
# Capture raw output without a pipeline; retain unfiltered compiler errors.
cargo clippy --message-format=short --color=never "$@" > "$logs/clippy.log" 2>&1
clippy_status=$?
printf '%s\n' "$clippy_status" > "$logs/clippy.exit"
cat "$logs/clippy.log" >&2
reviewdog_bin=${RUST_REVIEWDOG_BIN:-reviewdog}
if ! command -v "$reviewdog_bin" >/dev/null 2>&1; then
  echo 'reviewdog: NOT RUN (optional tool missing; Clippy result retained)' >&2
  exit "$clippy_status"
fi
args=(-f=clippy -reporter=local -filter-mode=nofilter -fail-level=warning)
if [[ -n ${RUST_REVIEWDOG_BASE:-} ]]; then
  # Only a resolved commit hash enters reviewdog's shell diff command.
  if base=$(git rev-parse --verify --end-of-options "${RUST_REVIEWDOG_BASE}^{commit}" 2>/dev/null); then
    args=(-f=clippy -reporter=local -filter-mode=added -fail-level=warning
      "-diff=git diff --no-ext-diff --no-textconv --no-color $base --")
  else
    echo 'reviewdog: invalid base; displaying unfiltered diagnostics' >&2
  fi
fi
"$reviewdog_bin" "${args[@]}" < "$logs/clippy.log" > "$logs/reviewdog.log" 2> "$logs/reviewdog.stderr"
reviewdog_status=$?
printf '%s\n' "$reviewdog_status" > "$logs/reviewdog.exit"
cat "$logs/reviewdog.log" "$logs/reviewdog.stderr" >&2
printf 'reviewdog: exit=%s (presentation only; Clippy exit=%s)\n' "$reviewdog_status" "$clippy_status" >&2
if [[ ! -s "$logs/reviewdog.log" ]]; then
  echo 'Empty reviewdog report is not evidence of Clippy PASS; inspect clippy.log.' >&2
fi
exit "$clippy_status"
