#!/usr/bin/env bash
# Held-out checks in isolated copies; never edit the independently reviewed trees.
set -euo pipefail
kit=$(cd "$(dirname "$0")/../.." && pwd)
root=${1:?Usage: verify-concurrency-retest.sh RUN_DIRECTORY}
mkdir -p "$root/oracle-results"
for case_name in r1 r2; do
  probe="$root/oracle-$case_name"
  [[ ! -e "$probe" ]] || { echo 'Probe exists' >&2; exit 2; }
  mkdir -p "$probe/src" "$probe/tests"
  cp "$root/$case_name/Cargo.toml" "$root/$case_name/Cargo.lock" "$probe/"
  cp "$root/$case_name/src/"*.rs "$probe/src/"
  cp "$kit/tests/e2e/advanced-fixture/oracle/async_regressions.rs" "$kit/tests/e2e/advanced-fixture/oracle/publication.rs" "$probe/tests/"
  for check in async loom; do
    log="$root/oracle-results/$case_name-$check.log"
    set +e
    if [[ $check == async ]]; then
      (cd "$probe" && timeout 120 cargo test --offline --locked --test async_regressions) > "$log" 2>&1
    else
      (cd "$probe" && env -u LOOM_MAX_DURATION -u LOOM_MAX_PERMUTATIONS -u LOOM_MAX_PREEMPTIONS -u LOOM_CHECKPOINT_FILE timeout 120 cargo test --offline --locked --features model --test publication) > "$log" 2>&1
    fi
    rc=$?
    set -e
    printf '%s\t%s\t%s\n' "$case_name" "$check" "$rc" | tee -a "$root/oracle-results/status.tsv"
    [[ $rc != 124 ]] || { echo 'Process timeout is not a reproduced bug' >&2; exit 1; }
    if [[ $case_name == r1 ]]; then
      [[ $rc != 0 ]]
      if [[ $check == async ]]; then grep -q '0 passed; 3 failed' "$log"; else grep -q 'left: 0' "$log"; fi
    else
      [[ $rc == 0 ]] || { tail -30 "$log"; exit 1; }
      if [[ $check == async ]]; then grep -q '3 passed; 0 failed' "$log"; else grep -q '1 passed; 0 failed' "$log"; fi
    fi
  done
done
