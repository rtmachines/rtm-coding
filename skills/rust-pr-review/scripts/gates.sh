#!/usr/bin/env bash
# Run from a trusted Cargo workspace. Additional arguments are Cargo feature flags.
# Example: gates.sh --no-default-features --features 'server,tls'
# No arguments: --all-features. RUST_GATE_FEATURES= disables that default.
set -uo pipefail
export CARGO_TERM_COLOR=never
[[ -f Cargo.toml ]] || { echo 'Run gates.sh from the Cargo workspace root.' >&2; exit 2; }
features=(--all-features)
if [[ ${RUST_GATE_FEATURES+x} ]]; then
  read -r -a features <<< "$RUST_GATE_FEATURES"
fi
if (( $# )); then features=("$@"); fi
for arg in "${features[@]}"; do
  case "$arg" in --manifest-path*|--target-dir*|--config*|--help|--version) echo "Unsupported feature argument: $arg" >&2; exit 2;; esac
done
locked=()
[[ ! -f Cargo.lock ]] || locked=(--locked)
failed=0
run_gate() {
  local name=$1; shift
  printf '\n$' >&2; printf ' %q' "$@" >&2; printf '\n' >&2
  if "$@" >&2; then printf -- '- %s: PASS\n' "$name"
  else printf -- '- %s: FAIL\n' "$name"; failed=1; fi
}
run_gate fmt cargo fmt --all -- --check
run_gate clippy bash "$(dirname "${BASH_SOURCE[0]}")/clippy.sh" --workspace --all-targets "${features[@]}" "${locked[@]}" -- -D warnings
if cargo nextest --version >/dev/null 2>&1; then
  run_gate tests cargo nextest run --workspace "${features[@]}" "${locked[@]}" --no-fail-fast --no-tests=pass
  run_gate doctests cargo test --workspace --doc "${features[@]}" "${locked[@]}"
else
  # cargo test includes doctests by default; no --all-targets here.
  run_gate tests cargo test --workspace "${features[@]}" "${locked[@]}" --no-fail-fast
  echo '- doctests: N/A (included in cargo test)'
fi
if [[ ! -f deny.toml ]]; then
  echo '- deny: NOT RUN (deny.toml missing)'; failed=1
elif ! cargo deny --version >/dev/null 2>&1; then
  echo '- deny: NOT RUN (cargo-deny missing)'; failed=1
else
  run_gate deny cargo deny "${locked[@]}" check
fi
exit "$failed"
