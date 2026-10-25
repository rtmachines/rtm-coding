#!/usr/bin/env bash
# Behavioral checks in disposable copies; UB probes run only in Miri.
set -euo pipefail
kit=$(cd "$(dirname "$0")/../.." && pwd)
root=${1:?Usage: verify-advanced.sh RUN_DIRECTORY}
mkdir -p "$root/oracle-results"
for variant in case-a case-b case-d; do
  probe="$root/probe-$variant"
  memory="$root/memory-$variant"
  [[ ! -e "$probe" && ! -e "$memory" ]] || { echo 'Probe already exists' >&2; exit 2; }
  mkdir -p "$probe/src" "$probe/tests" "$memory/src" "$memory/tests"
  cp "$root/$variant/Cargo.toml" "$root/$variant/Cargo.lock" "$probe/"
  cp "$root/$variant/src/"*.rs "$probe/src/"
  cp "$kit/tests/e2e/advanced-fixture/oracle/async_regressions.rs" "$kit/tests/e2e/advanced-fixture/oracle/publication.rs" "$probe/tests/"
  cp "$root/$variant/src/bytes.rs" "$root/$variant/src/registration.rs" "$memory/src/"
  printf 'pub mod bytes;\npub mod registration;\n' > "$memory/src/lib.rs"
  printf '[package]\nname="memory-probe"\nversion="0.1.0"\nedition="2024"\n' > "$memory/Cargo.toml"
  cp "$kit/tests/e2e/advanced-fixture/oracle/memory.rs" "$memory/tests/"
  (cd "$memory" && cargo generate-lockfile --offline)
  for check in async loom short-slice ffi; do
    log="$root/oracle-results/$variant-$check.log"
    set +e
    case "$check" in
      async) (cd "$probe" && timeout 180 cargo test --locked --test async_regressions) > "$log" 2>&1;;
      loom) (cd "$probe" && timeout 180 cargo test --locked --features model --test publication) > "$log" 2>&1;;
      short-slice) (cd "$memory" && timeout 180 cargo +nightly miri test --test memory short_slice_rejected) > "$log" 2>&1;;
      ffi) (cd "$memory" && timeout 180 cargo +nightly miri test --test memory ffi_storage_lives_until_unregister) > "$log" 2>&1;;
    esac
    rc=$?
    set -e
    printf '%s\t%s\t%s\n' "$variant" "$check" "$rc" | tee -a "$root/oracle-results/status.tsv"
    [[ $rc != 124 ]] || { echo 'Timed out, not counted as a detected defect' >&2; exit 1; }
    if [[ $variant == case-a ]]; then
      [[ $rc -ne 0 ]] || { echo 'Faulty case unexpectedly passed' >&2; exit 1; }
      case "$check" in
        async) grep -q '0 passed; 3 failed' "$log";;
        loom) grep -q 'left: 0' "$log";;
        short-slice|ffi) grep -q 'Undefined Behavior' "$log";;
      esac
    elif [[ $variant == case-b && $check == ffi ]]; then
      # Preserve the initially unexpected experimental-model disagreement.
      [[ $rc -ne 0 ]]
      grep -q 'Stacked Borrows' "$log"
      grep -q 'Unique retag' "$log"
      (cd "$memory" && MIRIFLAGS=-Zmiri-tree-borrows timeout 180 cargo +nightly miri test --test memory ffi_storage_lives_until_unregister) > "$root/oracle-results/$variant-ffi-tree-borrows.log" 2>&1
    else
      [[ $rc == 0 ]] || { tail -40 "$log"; exit 1; }
    fi
  done
done
