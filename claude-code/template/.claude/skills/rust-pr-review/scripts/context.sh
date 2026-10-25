#!/usr/bin/env bash
# Usage: context.sh [base-ref]. Local Git only; no network or implicit fallback.
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0
base_ref="${1:-origin/main}"
[[ $# -le 1 && -n "$base_ref" && "$base_ref" != -* ]] || { echo 'Usage: context.sh [base-ref]' >&2; exit 2; }
cd "$(git rev-parse --show-toplevel)"
head=$(git rev-parse --verify 'HEAD^{commit}')
target=$(git rev-parse --verify --end-of-options "${base_ref}^{commit}") || {
  echo "Cannot resolve base: $base_ref. Supply an existing base ref; scope was not changed." >&2; exit 2;
}
base=$(git merge-base "$head" "$target") || { echo 'No merge base; review scope unresolved.' >&2; exit 2; }
printf 'BASE_REF=%s\nBASE_SHA=%s\nHEAD_SHA=%s\n' "$base_ref" "$base" "$head"
printf '\n### Working-tree status (includes untracked files)\n'
git -c core.quotePath=true status --short --untracked-files=all
printf '\n### Tracked changes: merge base -> working tree\n'
git --no-pager diff --no-ext-diff --no-textconv --stat "$base" --
printf '\n### Commit claims (not an independent specification)\n'
git --no-pager log --format='- %s' "$base..$head"
printf '\nUntracked files are NOT included in git diff; inspect them separately.\n'
