#!/usr/bin/env bash
set -euo pipefail
kit=$(cd "$(dirname "$0")/.." && pwd)
helper="$kit/codex-template/.agents/skills/rust-pr-review/scripts/clippy.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/bin" "$tmp/logs"
export TMPDIR="$tmp/logs"
cat > "$tmp/bin/cargo" <<'MOCK'
#!/bin/bash
echo 'src/lib.rs:1:1: error: deliberate Clippy failure' >&2
exit "${CLIPPY_EXIT:-101}"
MOCK
cat > "$tmp/bin/reviewdog" <<'MOCK'
#!/bin/bash
cat >/dev/null
exit "${DOG_EXIT:-0}"
MOCK
chmod +x "$tmp/bin/"*
original_path=$PATH
export PATH="$tmp/bin:$PATH" RUST_REVIEWDOG=1
check() {
  local expected=$1 actual=0; shift
  "$@" > "$tmp/out" 2>&1 || actual=$?
  [[ $actual == "$expected" ]] || { cat "$tmp/out"; exit 1; }
}
check 101 env RUST_REVIEWDOG_BIN="$tmp/absent" bash "$helper" -- -D warnings
grep -q 'optional tool missing' "$tmp/out"
grep -q 'deliberate Clippy failure' "$tmp/out"
check 101 bash "$helper" -- -D warnings
grep -q 'Empty reviewdog report' "$tmp/out"
check 101 env DOG_EXIT=2 bash "$helper"
grep -q 'reviewdog: exit=2' "$tmp/out"
check 0 env CLIPPY_EXIT=0 DOG_EXIT=2 bash "$helper"
check 0 env CLIPPY_EXIT=0 RUST_REVIEWDOG_BIN="$tmp/absent" bash "$helper"
check 101 env RUST_REVIEWDOG=0 bash "$helper"
echo 'PASS optional reviewdog status isolation (6 cases)'

if [[ ${1:-} == --real ]]; then
  export PATH=$original_path
  unset RUST_REVIEWDOG_BIN
  command -v cargo >/dev/null
  command -v reviewdog >/dev/null
  mkdir -p "$tmp/repo/src"
  cd "$tmp/repo"
  printf '[package]\nname="reviewdog-regression"\nversion="0.1.0"\nedition="2021"\n' > Cargo.toml
  printf 'pub fn bad() -> bool { true == true }\n' > src/lib.rs
  git init -q
  git -c user.name=Test -c user.email=test@example.invalid add .
  git -c user.name=Test -c user.email=test@example.invalid -c commit.gpgsign=false commit -qm fixture
  export RUST_REVIEWDOG_BASE=HEAD
  check 101 bash "$helper" --offline -- -D warnings
  grep -q 'Empty reviewdog report' "$tmp/out"
  grep -q 'Clippy exit=101' "$tmp/out"
  grep -q 'equal expressions' "$tmp/out"
  check 101 env RUST_REVIEWDOG_BIN="$tmp/absent" bash "$helper" --offline -- -D warnings
  grep -q 'optional tool missing' "$tmp/out"
  echo 'PASS real Clippy failure with empty filtered report and missing reviewdog'
fi
