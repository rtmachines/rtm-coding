#!/usr/bin/env bash
# Network is allowed only here; regression diagnostics themselves remain offline.
set -euo pipefail
kit=$(cd "$(dirname "$0")/../../.." && pwd)
readarray -t versions < <(python - "$kit/tests/workflow/ci/toolchains.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]));print(v['rust']);print(v['miri']);print(v['cargo_deny'])
PY
)
rustup toolchain install "${versions[0]}" --profile minimal --component rustfmt --component clippy
rustup toolchain install "${versions[1]}" --profile minimal --component miri --component rust-src
cargo +"${versions[0]}" install cargo-deny --version "=${versions[2]}" --locked
# Warm the two dependency sets before offline fixture preparation.
cache=$(mktemp -d)
trap 'rm -rf "$cache"' EXIT
python - "$kit" "$cache" <<'PY'
import pathlib,sys,tarfile
kit=pathlib.Path(sys.argv[1]);root=pathlib.Path(sys.argv[2])
with tarfile.open(kit/'tests/e2e/results/2026-10-24-advanced/example-repositories.tar.gz') as t:
 for name in ['Cargo.toml','Cargo.lock','deny.toml']:
  (root/name).write_bytes(t.extractfile('case-d/'+name).read())
(root/'src').mkdir();(root/'src/lib.rs').write_text('')
PY
cargo +"${versions[0]}" fetch --locked --manifest-path "$cache/Cargo.toml"
cargo +"${versions[0]}" deny --manifest-path "$cache/Cargo.toml" fetch all
cargo +"${versions[1]}" miri setup
if [[ -n ${GITHUB_ENV:-} ]]; then
  printf 'RUSTUP_TOOLCHAIN=%s\nMIRI_TOOLCHAIN=%s\n' "${versions[0]}" "${versions[1]}" >> "$GITHUB_ENV"
fi
