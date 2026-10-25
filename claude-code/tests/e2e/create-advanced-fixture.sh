#!/usr/bin/env bash
set -euo pipefail
kit=$(cd "$(dirname "$0")/../.." && pwd)
root=${1:?Usage: create-advanced-fixture.sh NEW_DIRECTORY}
[[ ! -e "$root" ]] || { echo 'Destination already exists' >&2; exit 2; }
mkdir -p "$root/evidence"
root=$(cd "$root" && pwd)
for variant in bad good uncertain control; do
  case "$variant" in bad) case_name=case-a;; good) case_name=case-b;; uncertain) case_name=case-c;; control) case_name=case-d;; esac
  repo="$root/$case_name"
  mkdir -p "$repo/src"
  cat > "$repo/Cargo.toml" <<'MANIFEST'
[package]
name = "runtime-bridge"
version = "0.1.0"
edition = "2024"
license = "MIT"
publish = false
[features]
model = ["dep:loom"]
[dependencies]
tokio = { version = "=1.54.1", features = ["rt", "macros", "sync", "time"] }
loom = { version = "0.7", optional = true }
MANIFEST
  printf '/target/\n/.code-review-graph/\n' > "$repo/.gitignore"
  printf '[advisories]\n[licenses]\nallow=["MIT", "Apache-2.0", "Unicode-3.0", "BSD-3-Clause"]\n[bans]\nmultiple-versions="warn"\n[sources]\nunknown-registry="deny"\nunknown-git="deny"\n' > "$repo/deny.toml"
  echo '// Runtime adapters.' > "$repo/src/lib.rs"
  bash "$kit/install.sh" "$repo" > "$root/evidence/$variant-install.log"
  cat >> "$repo/REVIEW.md" <<'POLICY'

## Runtime bridge project policy
Required checks: fmt, clippy, tests, doctests, cargo-deny. Use default Cargo features
(RUST_GATE_FEATURES='') for ordinary gates. The optional model feature swaps std
atomics for Loom and is only exercised inside a loom::model closure; it is not a
production feature. For memory checks, Miri is available where code is supported.
This is unpublished, so semver checks do not apply. Requirements are in REQUIREMENTS.md.
POLICY
  cat > "$repo/REQUIREMENTS.md" <<'SPEC'
# Runtime bridge
Add the public adapters with these contracts:
- read_word accepts arbitrary alignment and returns None for fewer than four bytes.
- Registration retains read-only buffer ownership until synchronous unregister completes.
- Service increments must complete and allow later snapshots without deadlock.
- approved_pop consumes nothing if cancelled before approval is received.
- stop_worker must return only after its owned worker cannot cause further side effects.
- Published is single-writer, one-shot: any observed Some must equal the published value.
Keep ordinary checks runnable without executing undefined behavior or unbounded waits.
SPEC
  if [[ $variant == uncertain ]]; then
    cat > "$repo/REQUIREMENTS.md" <<'SPEC'
# Vendor callback adapter
Add an RAII adapter for the supported vendor runtime. The Session owns callback
context and unregisters it at destruction, preserving memory safety during teardown.
The SDK extract vendor.h is the available ABI declaration. The vendor binary and
implementation are supplied by the deployment environment and are not in this repo.
SPEC
  fi
  (cd "$repo" && cargo generate-lockfile && git init -q && git config user.name 'Workflow Fixture' && git config user.email 'fixture@example.invalid' && git add . && git commit -qm 'Review baseline and contracts' && git branch baseline && git update-ref refs/remotes/origin/main HEAD)
  cp "$kit/tests/e2e/advanced-fixture/$variant/"*.rs "$repo/src/"
  if [[ $variant == uncertain ]]; then cp "$kit/tests/e2e/advanced-fixture/uncertain/vendor.h" "$repo/"; fi
  if [[ $variant == control ]]; then
    mkdir "$repo/tests"
    cp "$kit/tests/e2e/advanced-fixture/oracle/async_regressions.rs" "$kit/tests/e2e/advanced-fixture/oracle/publication.rs" "$repo/tests/"
    sed 's/memory_probe/runtime_bridge/g' "$kit/tests/e2e/advanced-fixture/oracle/memory.rs" > "$repo/tests/memory.rs"
    (cd "$repo" && git add tests)
  fi
  (cd "$repo" && cargo fmt --all && git add src && git add -u && { [[ ! -f vendor.h ]] || git add vendor.h; } && git commit -qm 'Implement runtime adapters')
  (cd "$repo" && git rev-parse HEAD && git rev-parse baseline) > "$root/evidence/$variant-revisions.txt"
done
printf '%s\n' "$root"
