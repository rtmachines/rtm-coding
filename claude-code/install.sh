#!/usr/bin/env bash
# Install the Codex kit (default) or the original Claude Code kit (--claude).
set -euo pipefail
kit="$(cd "$(dirname "$0")" && pwd)"
if [[ ${1:-} == --claude ]]; then shift; exec bash "$kit/install-claude.sh" "$@"; fi
usage() {
  echo 'Usage: install.sh [--axum] [--grpc] [--graphql] [--lib-guidelines] [--all-optional] [--no-ci] [--force] <repo>'
  echo 'Codex is the default. For the original kit use: install.sh --claude [legacy-options] <repo>'
}
repo='' force=0 ci=1
optional=()
for arg in "$@"; do
  case "$arg" in
    --codex) ;;
    --axum) optional+=(tailrocks-axum-review);;
    --grpc) optional+=(tailrocks-grpc-review);;
    --graphql) optional+=(tailrocks-graphql-review);;
    --lib-guidelines) optional+=(rust-lib-guidelines);;
    --all-optional) optional=(tailrocks-axum-review tailrocks-grpc-review tailrocks-graphql-review rust-lib-guidelines);;
    --no-ci) ci=0;; --force) force=1;;
    -h|--help) usage; exit 0;;
    -*) echo "Unsupported Codex option: $arg" >&2; usage >&2; exit 2;;
    *) [[ -z "$repo" ]] || { echo 'Expected one target directory.' >&2; exit 2; }; repo=$arg;;
  esac
done
[[ -n "$repo" ]] || { usage >&2; exit 2; }
repo="$(cd "$repo" && pwd)"
[[ -f "$repo/Cargo.toml" ]] || echo 'WARN: no Cargo.toml; configure a Cargo workspace before running gates.' >&2
# Refuse symlink traversal for every destination, including existing parent directories.
check_path() {
  local path=$1
  while [[ "$path" != "$repo" ]]; do
    [[ ! -L "$path" ]] || { echo "Refusing symlink destination: $path" >&2; exit 2; }
    path=$(dirname "$path")
  done
}
put() {
  local src=$1 dst=$2
  check_path "$dst"
  if [[ -e "$dst" && $force == 0 ]]; then echo "KEEP ${dst#"$repo"/}"; return; fi
  [[ ! -d "$dst" ]] || { echo "Expected file: $dst" >&2; exit 2; }
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "COPY ${dst#"$repo"/}"
}
put_tree() {
  local src=$1 dst=$2 file
  while IFS= read -r -d '' file; do put "$file" "$dst/${file#"$src"/}"; done < <(find "$src" -type f -print0)
}
T="$kit/codex-template"
put_tree "$T/.agents/skills" "$repo/.agents/skills"
for name in "${optional[@]}"; do put_tree "$kit/codex-optional/skills/$name" "$repo/.agents/skills/$name"; done
put "$T/REVIEW.md" "$repo/REVIEW.md"
if (( ci )); then put "$T/.github/workflows/rust-gates.yml" "$repo/.github/workflows/rust-gates.yml"; fi
put "$kit/vendored.tsv" "$repo/.agents/rust-review-kit/vendored.tsv"
put "$kit/THIRD_PARTY_NOTICES.md" "$repo/.agents/rust-review-kit/THIRD_PARTY_NOTICES.md"
put "$kit/scripts/check-upstream.sh" "$repo/.agents/rust-review-kit/scripts/check-upstream.sh"
put_tree "$kit/licenses" "$repo/.agents/rust-review-kit/licenses"
check_path "$repo/AGENTS.md"
if ! grep -qF '<!-- rust-review-kit-codex:begin -->' "$repo/AGENTS.md" 2>/dev/null; then
  cat "$T/AGENTS.md.snippet" >> "$repo/AGENTS.md"
  echo 'APPEND AGENTS.md'
else
  echo 'KEEP AGENTS.md (existing kit block; update manually even with --force)'
fi
[[ ! -f "$repo/AGENTS.override.md" ]] || echo 'WARN: AGENTS.override.md takes precedence; merge the kit instructions there manually.' >&2
printf '\nInstalled Codex kit in %s\n' "$repo"
echo 'Adapt REVIEW.md, features/toolchain and deny.toml. Review the installed files.'
echo 'In Codex: $rust-pr-review origin/main <requirements>'
echo 'Checks: bash .agents/skills/rust-pr-review/scripts/gates.sh'
echo 'No Claude hooks, external plugins, global settings or branch protection were installed.'
