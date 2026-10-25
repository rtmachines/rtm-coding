#!/usr/bin/env bash
# Install the Claude Code Rust review workflow offline.
# Usage: ./install-claude.sh [options] <path-to-rust-repo>
#   --axum            add tailrocks-axum-review (manual skill)
#   --grpc            add tailrocks-grpc-review (manual skill)
#   --graphql         add tailrocks-graphql-review (manual skill)
#   --lib-guidelines  add rust-lib-guidelines (manual skill)
#   --zeroize         explicitly enable Trail of Bits zeroize-audit plugin
#   --pr-toolkit      explicitly enable Anthropic pr-review-toolkit plugin
#   --all-optional    all of the above (including plugin opt-ins)
#   --no-ci           do not add .github/workflows/rust-gates.yml
#   --force           update kit-owned files; keep unrelated files/settings
set -euo pipefail

kit="$(cd "$(dirname "$0")" && pwd -P)"
opt_axum=0 opt_grpc=0 opt_graphql=0 opt_lib=0 opt_zeroize=0 opt_toolkit=0 opt_ci=1 force=0
repo=""
for a in "$@"; do
  case "$a" in
    --axum) opt_axum=1;; --grpc) opt_grpc=1;; --graphql) opt_graphql=1;;
    --lib-guidelines) opt_lib=1;; --zeroize) opt_zeroize=1;; --pr-toolkit) opt_toolkit=1;;
    --all-optional) opt_axum=1 opt_grpc=1 opt_graphql=1 opt_lib=1 opt_zeroize=1 opt_toolkit=1;;
    --no-ci) opt_ci=0;; --force) force=1;;
    -h|--help) sed -n '2,12p' "$0"; exit 0;;
    -*) echo "unknown option: $a" >&2; exit 1;;
    *) [ -z "$repo" ] || { echo "expected exactly one destination" >&2; exit 1; }; repo="$a";;
  esac
done
[ -n "$repo" ] || { sed -n '2,12p' "$0"; exit 1; }
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }
repo="$(cd "$repo" && pwd -P)"
T="$kit/template"

# Check all ancestors, including dangling links. --force never follows links.
safe_destination() {
  local path="$1" parent
  case "$path" in "$repo"/*) ;; *) echo "destination outside repo: $path" >&2; exit 1;; esac
  parent="$path"
  while [ "$parent" != "$repo" ]; do
    [ ! -L "$parent" ] || { echo "refusing symlink destination: $parent" >&2; exit 1; }
    if [ "$parent" != "$path" ] && [ -e "$parent" ] && [ ! -d "$parent" ]; then
      echo "destination parent is not a directory: $parent" >&2; exit 1
    fi
    parent="${parent%/*}"
  done
}

sources=() destinations=()
add_file() {
  local src="$1" dst="$2"
  [ -f "$src" ] && [ ! -L "$src" ] || { echo "missing/nonregular kit file: $src" >&2; exit 1; }
  safe_destination "$dst"
  [ ! -e "$dst" ] || [ -f "$dst" ] || { echo "destination is not a file: $dst" >&2; exit 1; }
  sources+=("$src"); destinations+=("$dst")
}
add_tree() {
  local src="$1" dst="$2" file
  [ -d "$src" ] && [ ! -L "$src" ] || { echo "missing/nonregular kit directory: $src" >&2; exit 1; }
  safe_destination "$dst"
  [ ! -e "$dst" ] || [ -d "$dst" ] || { echo "destination is not a directory: $dst" >&2; exit 1; }
  while IFS= read -r -d '' file; do
    add_file "$file" "$dst/${file#"$src/"}"
  done < <(find "$src" -type f -print0)
}

# Preflight the complete installation before writing any destination files.
for file in "$T"/.claude/hooks/*.sh; do add_file "$file" "$repo/.claude/hooks/$(basename "$file")"; done
add_file "$T/.claude/agents/rust-reviewer.md" "$repo/.claude/agents/rust-reviewer.md"
add_tree "$T/.claude/skills/rust-pr-review" "$repo/.claude/skills/rust-pr-review"
add_tree "$T/.claude/skills/rust-best-practices" "$repo/.claude/skills/rust-best-practices"
# Reuse the pinned Codex source without downloading or duplicating rules in this kit.
add_tree "$kit/codex-template/.agents/skills/rust-skills" "$repo/.claude/skills/rust-skills"
add_file "$T/REVIEW.md" "$repo/REVIEW.md"
[ "$opt_ci" -eq 0 ] || add_file "$T/.github/workflows/rust-gates.yml" "$repo/.github/workflows/rust-gates.yml"
[ "$opt_axum" -eq 0 ] || add_tree "$kit/optional/skills/tailrocks-axum-review" "$repo/.claude/skills/tailrocks-axum-review"
[ "$opt_grpc" -eq 0 ] || add_tree "$kit/optional/skills/tailrocks-grpc-review" "$repo/.claude/skills/tailrocks-grpc-review"
[ "$opt_graphql" -eq 0 ] || add_tree "$kit/optional/skills/tailrocks-graphql-review" "$repo/.claude/skills/tailrocks-graphql-review"
[ "$opt_lib" -eq 0 ] || add_tree "$kit/optional/skills/rust-lib-guidelines" "$repo/.claude/skills/rust-lib-guidelines"
metadata="$repo/.claude/rust-review-kit"
add_file "$kit/vendored.tsv" "$metadata/vendored.tsv"
add_file "$kit/scripts/check-upstream.sh" "$metadata/scripts/check-upstream.sh"
add_tree "$kit/licenses" "$metadata/licenses"
add_file "$kit/THIRD_PARTY_NOTICES.md" "$metadata/THIRD_PARTY_NOTICES.md"

settings="$repo/.claude/settings.json"
claude_md="$repo/CLAUDE.md"
backup="$metadata/settings.json.before-install"
for file in "$settings" "$backup" "$claude_md"; do
  safe_destination "$file"
  [ ! -e "$file" ] || [ -f "$file" ] || { echo "destination is not a file: $file" >&2; exit 1; }
done
if [ -f "$settings" ]; then
  jq -e 'type == "object" and ((.hooks // {}) | type == "object") and
    ((.permissions // {}) | type == "object") and
    ((.enabledPlugins // {}) | type == "object")' "$settings" >/dev/null || {
    echo "invalid existing settings; left unchanged: $settings" >&2; exit 1;
  }
fi
if [ -f "$claude_md" ]; then
  awk '
    /^<!-- rust-review-kit:begin -->$/ {if (begun || inside) exit 1; begun=1; inside=1}
    /^<!-- rust-review-kit:end -->$/ {if (!inside) exit 1; inside=0}
    END {if (inside) exit 1}
  ' "$claude_md" || { echo "malformed rust-review-kit markers; CLAUDE.md left unchanged" >&2; exit 1; }
fi

copied=0 kept=0
for i in "${!sources[@]}"; do
  dst="${destinations[$i]}"
  if [ -e "$dst" ] && [ "$force" -eq 0 ]; then
    kept=$((kept + 1))
  else
    mkdir -p "$(dirname "$dst")"
    # Atomic replacement also avoids changing another file through a hard link.
    temporary="$(mktemp "$(dirname "$dst")/.rust-review-kit.XXXXXX")"
    cp -p "${sources[$i]}" "$temporary"
    mv -f "$temporary" "$dst"
    copied=$((copied + 1))
  fi
done

extra='{}'
if [ "$opt_zeroize" -eq 1 ]; then
  extra="$(jq '.enabledPlugins["zeroize-audit@trailofbits"]=true |
    .extraKnownMarketplaces.trailofbits.source={source:"github",repo:"trailofbits/skills"}' <<< "$extra")"
fi
[ "$opt_toolkit" -eq 0 ] || extra="$(jq '.enabledPlugins["pr-review-toolkit@claude-plugins-official"]=true' <<< "$extra")"
[ -f "$settings" ] || printf '{}\n' > "$settings"
[ -f "$backup" ] || cp "$settings" "$backup"
temporary="$(mktemp "$repo/.claude/.settings.XXXXXX")"
trap 'rm -f "$temporary"' EXIT
jq -s '
  def uniq: reduce .[] as $x ([]; if any(.[]; . == $x) then . else . + [$x] end);
  # Only exact kit-owned legacy commands are migrated. User hooks survive.
  def legacy:
    . == {type:"command",command:"${CLAUDE_PROJECT_DIR}/.claude/hooks/review-router.sh",args:[]} or
    . == {type:"command",command:"${CLAUDE_PROJECT_DIR}/.claude/hooks/rust-gate.sh",args:["stop"],timeout:900} or
    . == {type:"command",if:"Bash(git commit *)",command:"${CLAUDE_PROJECT_DIR}/.claude/hooks/rust-gate.sh",args:["commit"],timeout:900};
  def migrate: with_entries(.value |= map(.hooks |= map(select(legacy | not))) | .value |= map(select(.hooks | length > 0)) | select(.value | length > 0));
  def hookmerge($a; $b): reduce ((($a // {}) | keys) + (($b // {}) | keys) | unique)[] as $k
      ({}; .[$k] = ((($a // {})[$k] // []) + (($b // {})[$k] // []) | uniq));
  .[0] as $a | .[1] as $b | .[2] as $c
  | ($b * $a * $c)
  | .permissions.deny = ((($a.permissions.deny // []) + ($b.permissions.deny // [])) | uniq)
  | .hooks = hookmerge(($a.hooks // {} | migrate); $b.hooks)
' "$settings" "$T/.claude/settings.json" <(printf '%s\n' "$extra") > "$temporary"
mv -f "$temporary" "$settings"

# Replace only our marked block on --force, retaining all surrounding prose.
if ! grep -q '^<!-- rust-review-kit:begin -->$' "$claude_md" 2>/dev/null; then
  cat "$T/CLAUDE.md.snippet" >> "$claude_md"
elif [ "$force" -eq 1 ]; then
  temporary="$(mktemp "$repo/.CLAUDE.XXXXXX")"
  RRK_SNIPPET="$T/CLAUDE.md.snippet" awk '
    /^<!-- rust-review-kit:begin -->$/ {inside=1; while ((getline line < ENVIRON["RRK_SNIPPET"]) > 0) print line; close(ENVIRON["RRK_SNIPPET"]); next}
    /^<!-- rust-review-kit:end -->$/ {inside=0; next}
    !inside {print}
  ' "$claude_md" > "$temporary"
  mv -f "$temporary" "$claude_md"
fi

printf 'Installed Claude Rust review into %s: %s files updated, %s existing files kept.\n' "$repo" "$copied" "$kept"
cat <<'EOF'
The pinned rust-skills knowledge, licenses and source metadata are bundled offline.
Existing custom settings/plugins are preserved. No plugins are enabled by default.
Review the diff and REVIEW.md, then run /rust-pr-review in Claude Code.
Claude Code >=2.1.295 is required for fail-closed hook execution (onFailure: block).
The reviewer validates its own report at Stop; the project gate runs before git commit.
Cargo commands execute repository code: authorize the selected scope before running them.
EOF
