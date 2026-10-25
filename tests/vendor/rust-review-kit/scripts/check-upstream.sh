#!/usr/bin/env bash
# Shows what changed upstream since the pinned commits in vendored.tsv.
# Usage: scripts/check-upstream.sh [name-filter]
# Read-only: clones into a temp dir, prints commit counts and diffstat per vendored path.
set -uo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
filter="${1:-}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

grep -v '^#' "$here/vendored.tsv" | while IFS=$'\t' read -r name repo pin path _kit license note; do
  [ -n "$name" ] || continue
  [ -n "$filter" ] && [[ "$name" != *"$filter"* ]] && continue
  dir="$tmp/${repo//\//_}"
  if [ ! -d "$dir" ]; then
    git clone -q --filter=blob:none --no-checkout "https://github.com/$repo" "$dir" 2>/dev/null \
      || { echo "== $name: cannot clone $repo"; continue; }
  fi
  head="$(git -C "$dir" rev-parse --short origin/HEAD 2>/dev/null || git -C "$dir" rev-parse --short HEAD)"
  n="$(git -C "$dir" rev-list --count "$pin"..origin/HEAD -- "$path" 2>/dev/null || echo '?')"
  echo "== $name ($repo, $license) pinned ${pin:0:7} -> upstream $head: $n commit(s) touching $path"
  [ "$note" != "unchanged" ] && echo "   local note: $note"
  if [ "$n" != "0" ] && [ "$n" != "?" ]; then
    git -C "$dir" log --format='   %h %ad %s' --date=short "$pin"..origin/HEAD -- "$path" | head -n 10
    git -C "$dir" diff --stat "$pin" origin/HEAD -- "$path" | tail -n 1 | sed 's/^/   /'
  fi
done
echo
echo "To update: review the upstream diff, copy the files over the kit_path, re-apply the local note/patch, bump the commit in vendored.tsv."
