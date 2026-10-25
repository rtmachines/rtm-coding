#!/usr/bin/env bash
# Run the held-out oracle on isolated faulty and corrected copies, never the reviewed tree.
set -euo pipefail
root=${1:?Usage: verify-regressions.sh RUN_DIRECTORY}
repo="$root/repo"
mkdir "$root/faulty-probe" "$root/control-probe"
for copy in faulty-probe control-probe; do
  mkdir -p "$root/$copy/src" "$root/$copy/tests"
  cp "$repo/Cargo.toml" "$repo/Cargo.lock" "$root/$copy/"
  cp "$root/oracle/regressions.rs" "$root/$copy/tests/regressions.rs"
done
cp "$repo"/src/*.rs "$root/faulty-probe/src/"
git -C "$repo" show baseline:src/lib.rs > "$root/control-probe/src/lib.rs"
printf '\nmod limits;\npub use limits::parse_limit;\n' >> "$root/control-probe/src/lib.rs"
cat > "$root/control-probe/src/limits.rs" <<'RUST'
pub fn parse_limit(raw: &str) -> Option<u16> {
    raw.parse().ok()
}
RUST
for profile in debug release; do
  args=(); [[ $profile != release ]] || args=(--release)
  set +e
  (cd "$root/faulty-probe" && cargo test --offline --locked "${args[@]}" --test regressions) > "$root/evidence/faulty-$profile.log" 2>&1
  status=$?
  set -e
  [[ $status -ne 0 ]] || { echo 'Faulty fixture unexpectedly passed' >&2; exit 1; }
  grep -q '0 passed; 6 failed' "$root/evidence/faulty-$profile.log"
  (cd "$root/control-probe" && cargo test --offline --locked "${args[@]}" --test regressions) > "$root/evidence/control-$profile.log" 2>&1
  grep -q '6 passed; 0 failed' "$root/evidence/control-$profile.log"
done
printf 'Six oracle tests fail on faulty code and pass on the control in debug and release.\n'
