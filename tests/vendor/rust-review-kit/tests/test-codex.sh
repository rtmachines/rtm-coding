#!/usr/bin/env bash
set -euo pipefail
kit=$(cd "$(dirname "$0")/.." && pwd)
bash "$kit/tests/test-reviewdog.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
repo="$tmp/repo with spaces"
mkdir -p "$repo"
printf '[workspace]\nmembers=[]\n' > "$repo/Cargo.toml"
printf 'Existing instructions\n' > "$repo/AGENTS.md"
bash "$kit/install.sh" --all-optional "$repo" > "$tmp/install.log"
[[ -f "$repo/.agents/skills/rust-pr-review/SKILL.md" ]]
[[ -f "$repo/.agents/skills/tailrocks-grpc-review/agents/openai.yaml" ]]
[[ ! -d "$repo/.claude" ]]
[[ -f "$repo/.github/workflows/rust-gates.yml" ]]
printf 'custom policy\n' > "$repo/REVIEW.md"
bash "$kit/install.sh" --all-optional "$repo" > /dev/null
[[ $(cat "$repo/REVIEW.md") == 'custom policy' ]]
[[ $(grep -c 'rust-review-kit-codex:begin' "$repo/AGENTS.md") == 1 ]]
grep -q 'Existing instructions' "$repo/AGENTS.md"
printf 'user addition\n' > "$repo/.agents/skills/rust-pr-review/custom.txt"
bash "$kit/install.sh" --force "$repo" > /dev/null
[[ -f "$repo/.agents/skills/rust-pr-review/custom.txt" ]]
echo 'PASS install, optional skills, idempotency, force preservation'
mkdir "$tmp/no-ci"
bash "$kit/install.sh" --no-ci "$tmp/no-ci" > /dev/null 2>&1
[[ ! -e "$tmp/no-ci/.github" ]]
mkdir "$tmp/symlink" "$tmp/outside"
ln -s "$tmp/outside" "$tmp/symlink/.agents"
if bash "$kit/install.sh" "$tmp/symlink" > /dev/null 2>&1; then echo 'Symlink accepted' >&2; exit 1; fi
[[ -z $(ls -A "$tmp/outside") ]]
echo 'PASS no-ci and symlink refusal'
cd "$repo"
git init -q
git config user.email test@example.invalid
git config user.name test
git add Cargo.toml
git commit -qm initial
git branch baseline
printf '// new\n' > lib.rs
git add lib.rs
git commit -qm 'add source'
printf '// changed\n' >> lib.rs
printf '// untracked\n' > 'new file.rs'
scripts="$repo/.agents/skills/rust-pr-review/scripts"
bash "$scripts/context.sh" baseline > "$tmp/context"
grep -q 'new file.rs' "$tmp/context"
grep -q "BASE_SHA=$(git rev-parse baseline)" "$tmp/context"
if bash "$scripts/context.sh" absent-base > /dev/null 2>&1; then echo 'Missing base accepted' >&2; exit 1; fi
if bash "$scripts/context.sh" --help > /dev/null 2>&1; then exit 1; fi
echo 'PASS scope binding, dirty/untracked files and invalid refs'
mkdir "$tmp/bin"
cat > "$tmp/bin/cargo" <<'MOCK'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$TEST_CARGO_LOG"
case "$*" in
  'nextest --version') [[ ${TEST_NEXTEST:-1} == 1 ]];;
  'deny --version') [[ ${TEST_DENY:-1} == 1 ]];;
  clippy*) exit "${TEST_CLIPPY_EXIT:-0}";;
  'fmt --all -- --check') [[ ${TEST_FMT_FAIL:-0} == 0 ]];;
  *) exit 0;;
esac
MOCK
chmod +x "$tmp/bin/cargo"
export PATH="$tmp/bin:$PATH" TEST_CARGO_LOG="$tmp/cargo.log"
touch Cargo.lock deny.toml
bash "$scripts/gates.sh" > "$tmp/gates" 2> /dev/null
grep -q '^test --workspace --doc --all-features --locked$' "$TEST_CARGO_LOG"
grep -q '^deny --locked check$' "$TEST_CARGO_LOG"
TEST_FMT_FAIL=1 bash "$scripts/gates.sh" > "$tmp/gates" 2> /dev/null && exit 1
grep -q -- '- fmt: FAIL' "$tmp/gates"
TEST_DENY=0 bash "$scripts/gates.sh" > "$tmp/gates" 2> /dev/null && exit 1
grep -q -- '- deny: NOT RUN' "$tmp/gates"
rm deny.toml
bash "$scripts/gates.sh" > "$tmp/gates" 2> /dev/null && exit 1
grep -q 'deny.toml missing' "$tmp/gates"
touch deny.toml
: > "$TEST_CARGO_LOG"
TEST_NEXTEST=0 RUST_GATE_FEATURES='' bash "$scripts/gates.sh" > "$tmp/gates" 2> /dev/null
grep -q '^test --workspace --locked --no-fail-fast$' "$TEST_CARGO_LOG"
! grep -q -- '--all-features' "$TEST_CARGO_LOG"
# Reviewdog must not turn the aggregate Clippy gate green.
cat > "$tmp/bin/reviewdog" <<'MOCK'
#!/usr/bin/env bash
cat >/dev/null
exit 0
MOCK
chmod +x "$tmp/bin/reviewdog"
for dog in "$tmp/bin/reviewdog" "$tmp/missing-reviewdog"; do
  TEST_CLIPPY_EXIT=101 RUST_REVIEWDOG=1 RUST_REVIEWDOG_BIN="$dog" TMPDIR="$tmp" \
    bash "$scripts/gates.sh" > "$tmp/gates" 2> "$tmp/gate-errors" && exit 1
  grep -q -- '- clippy: FAIL' "$tmp/gates"
  ! grep -q -- '- clippy: PASS' "$tmp/gates"
done
echo 'PASS aggregate gate preserves Clippy failures with empty or missing reviewdog'
echo 'PASS gate failures, missing tools/configuration, doctests and cargo-test fallback'
cat > "$tmp/report" <<'REPORT'
## Verdict: APPROVE
Verified.
## Tooling
- rust-lsp: AVAILABLE (synthetic fixture)
- lsp-used: YES (synthetic semantic query)
- lsp-evidence: Test fixture query returned the expected definition; no live MCP claim.
- lsp-limitations: NONE within this synthetic validator fixture.
## Gates
- fmt: PASS
- clippy: PASS
- tests: PASS
- doctests: PASS
- deny: PASS
## Memory safety
- memory-scope: NONE (no affected unsafe/FFI)
- miri: N/A
- aliasing: N/A
- memory-evidence: N/A (safe-only)
- aliasing-evidence: N/A (safe-only)
## Concurrency
- async-scope: NONE (synchronous code)
- deadlocks: N/A (no locks)
- cancellation: N/A (no futures)
- task-lifecycle: N/A (no tasks)
- async-evidence: N/A (not applicable)
- sync-scope: NONE (no shared-state protocol)
- loom: N/A (not applicable)
- synchronization: N/A (not applicable)
- model-evidence: N/A (not applicable)
## Spec
- spec: PASS (user request)
- missing: none
- unrequested: none
- contradictions: none
## Findings
No findings.
## Residual risks
- None identified within reviewed scope.
REPORT
bash "$scripts/check-report.sh" "$tmp/report"
for change in 's/tests: PASS/tests: NOT RUN (unavailable)/' 's/spec: PASS/spec: PARTIAL/' 's/deny: PASS/deny: FAIL/' '/^## Residual risks/d' 's/No findings./- [P1] src\/lib.rs:42 - defect/' 's/tests: PASS/tests: N\/A (skip)/'; do
  sed "$change" "$tmp/report" > "$tmp/invalid"
  if bash "$scripts/check-report.sh" "$tmp/invalid" > /dev/null 2>&1; then echo "Invalid report accepted: $change" >&2; exit 1; fi
done
sed 's/Verdict: APPROVE/Verdict: INCOMPLETE/;s/tests: PASS/tests: NOT RUN (unavailable)/' "$tmp/report" | bash "$scripts/check-report.sh"
echo 'PASS report validation and INCOMPLETE support'
# These are report-contract scenarios, not claims that an MCP server was executed.
sed 's/rust-lsp: AVAILABLE.*/rust-lsp: UNAVAILABLE (MCP API absent)/;s/lsp-used: YES.*/lsp-used: NO (no semantic calls)/;s/lsp-evidence: .*/lsp-evidence: Tool discovery found no APIs; installation not authorized./;s/lsp-limitations: .*/lsp-limitations: Source and tests inspected; inferred types not verified by LSP./' "$tmp/report" > "$tmp/no-lsp"
bash "$scripts/check-report.sh" "$tmp/no-lsp"
for reason in 'MCP API absent' 'workspace load failed' 'initialization timed out' 'setup failed'; do
  sed "s/MCP API absent/$reason/" "$tmp/no-lsp" | bash "$scripts/check-report.sh"
done
# A health probe alone can report AVAILABLE, but must retain NO semantic use.
sed 's/rust-lsp: UNAVAILABLE.*/rust-lsp: AVAILABLE (health probe only)/' "$tmp/no-lsp" | bash "$scripts/check-report.sh"
for change in 's/lsp-used: NO/lsp-used: YES/' '/^## Tooling/d' '/^- lsp-evidence:/d' 's/lsp-evidence: .*/lsp-evidence: N\/A/' 's/lsp-limitations: .*/lsp-limitations: NONE no limitations/' 's/rust-lsp: UNAVAILABLE/rust-lsp: PASS/' '/^- lsp-used:/p'; do
  sed "$change" "$tmp/no-lsp" > "$tmp/invalid"
  if bash "$scripts/check-report.sh" "$tmp/invalid" > /dev/null 2>&1; then echo "Invalid LSP disclosure accepted: $change" >&2; exit 1; fi
done
# LSP absence never bypasses the existing gates and safety escalation rules.
sed 's/tests: PASS/tests: NOT RUN (unavailable)/' "$tmp/no-lsp" > "$tmp/invalid"
if bash "$scripts/check-report.sh" "$tmp/invalid" > /dev/null 2>&1; then exit 1; fi
sed 's/Verdict: APPROVE/Verdict: INCOMPLETE/;s/tests: PASS/tests: NOT RUN (unavailable)/' "$tmp/no-lsp" | bash "$scripts/check-report.sh"
echo 'PASS LSP unavailability, health-only status, evidence and consistency guards'

# A structurally complete required-memory report may approve only with both gates PASS.
sed 's/memory-scope: NONE.*/memory-scope: REQUIRED (src\/ffi.rs)/;s/miri: N\/A/miri: PASS/;s/aliasing: N\/A/aliasing: PASS/;s/memory-evidence: .*/memory-evidence: retained_pointer test, 1 run; toolchain and log attached/;s/aliasing-evidence: .*/aliasing-evidence: ownership and pointer access chain checked/' "$tmp/report" > "$tmp/memory-report"
bash "$scripts/check-report.sh" "$tmp/memory-report"
for change in 's/miri: PASS/miri: NOT RUN/' 's/miri: PASS/miri: FAIL/' 's/aliasing: PASS/aliasing: UNRESOLVED/' 's/aliasing: PASS/aliasing: FAIL/' 's/miri: PASS/miri: N\/A/' '/^- memory-evidence:/d' '/^## Memory safety/d'; do
  sed "$change" "$tmp/memory-report" > "$tmp/invalid"
  if bash "$scripts/check-report.sh" "$tmp/invalid" > /dev/null 2>&1; then echo "Invalid memory approval accepted: $change" >&2; exit 1; fi
done
sed 's/Verdict: APPROVE/Verdict: ESCALATE/;s/miri: PASS/miri: NOT RUN/;s/aliasing: PASS/aliasing: UNRESOLVED/' "$tmp/memory-report" | bash "$scripts/check-report.sh"
sed 's/Verdict: APPROVE/Verdict: REQUEST_CHANGES/;s/miri: PASS/miri: FAIL/;s/aliasing: PASS/aliasing: FAIL/' "$tmp/memory-report" | bash "$scripts/check-report.sh"
for verdict in APPROVE INCOMPLETE REQUEST_CHANGES; do
  sed "s/Verdict: APPROVE/Verdict: $verdict/;s/miri: PASS/miri: NOT RUN/;s/aliasing: PASS/aliasing: UNRESOLVED/" "$tmp/memory-report" > "$tmp/invalid"
  if bash "$scripts/check-report.sh" "$tmp/invalid" > /dev/null 2>&1; then echo "Unresolved memory risk accepted without ESCALATE: $verdict" >&2; exit 1; fi
done
echo 'PASS targeted memory evidence and escalation enforcement' 
sed 's/async-scope: NONE.*/async-scope: REQUIRED (src\/service.rs)/;s/^\(- deadlocks:\).*/\1 PASS/;s/^\(- cancellation:\).*/\1 PASS/;s/^\(- task-lifecycle:\).*/\1 PASS/;s/async-evidence: .*/async-evidence: controlled polls and handshakes, tests and logs attached/;s/^- sync-scope: NONE.*/- sync-scope: REQUIRED (publication)/;s/^\(- loom:\).*/\1 PASS/;s/^\(- synchronization:\).*/\1 PASS/;s/model-evidence: .*/model-evidence: tracked source, two threads, completed model and ordering proof/' "$tmp/report" > "$tmp/concurrency-report"
bash "$scripts/check-report.sh" "$tmp/concurrency-report"
for change in 's/deadlocks: PASS/deadlocks: NOT RUN/' 's/cancellation: PASS/cancellation: FAIL/' 's/task-lifecycle: PASS/task-lifecycle: FAIL/' 's/loom: PASS/loom: NOT RUN/' 's/loom: PASS/loom: FAIL/' 's/synchronization: PASS/synchronization: UNRESOLVED/' 's/synchronization: PASS/synchronization: FAIL/' 's/loom: PASS/loom: N\/A (unsupported)/' '/^- model-evidence:/d' '/^- async-evidence:/d' '/^## Concurrency/d' 's/deadlocks: PASS/deadlocks: MAYBE/' 's/deadlocks: PASS/deadlocks: N\/A/'; do
  sed "$change" "$tmp/concurrency-report" > "$tmp/invalid"
  if bash "$scripts/check-report.sh" "$tmp/invalid" > /dev/null 2>&1; then echo "Invalid concurrency approval accepted: $change" >&2; exit 1; fi
done
for field in deadlocks cancellation task-lifecycle loom synchronization; do
  sed "s/Verdict: APPROVE/Verdict: REQUEST_CHANGES/;s/$field: PASS/$field: FAIL/" "$tmp/concurrency-report" | bash "$scripts/check-report.sh"
  status='NOT RUN'; [[ $field != synchronization ]] || status=UNRESOLVED
  sed "s/Verdict: APPROVE/Verdict: ESCALATE/;s/$field: PASS/$field: $status/" "$tmp/concurrency-report" | bash "$scripts/check-report.sh"
  for verdict in APPROVE INCOMPLETE REQUEST_CHANGES; do
    sed "s/Verdict: APPROVE/Verdict: $verdict/;s/$field: PASS/$field: $status/" "$tmp/concurrency-report" > "$tmp/invalid"
    if bash "$scripts/check-report.sh" "$tmp/invalid" > /dev/null 2>&1; then echo "Unresolved concurrency accepted without ESCALATE: $field $verdict" >&2; exit 1; fi
  done
done
# Scope decisions remain independent; absent task spawning does not require lifecycle tests.
sed 's/task-lifecycle: PASS/task-lifecycle: N\/A (no owned tasks)/' "$tmp/concurrency-report" | bash "$scripts/check-report.sh"
sed 's/async-scope: REQUIRED.*/async-scope: NONE (no async changes)/;s/deadlocks: PASS/deadlocks: N\/A (no locks)/;s/cancellation: PASS/cancellation: N\/A (no futures)/;s/task-lifecycle: PASS/task-lifecycle: N\/A (no tasks)/' "$tmp/concurrency-report" | bash "$scripts/check-report.sh"
sed 's/^- sync-scope: REQUIRED.*/- sync-scope: NONE (no custom protocol)/;s/loom: PASS/loom: N\/A (no custom protocol)/;s/synchronization: PASS/synchronization: N\/A (no custom protocol)/' "$tmp/concurrency-report" | bash "$scripts/check-report.sh"
sed 's/deadlocks: PASS/deadlocks: N\/A (skipped)/;s/cancellation: PASS/cancellation: N\/A (skipped)/;s/task-lifecycle: PASS/task-lifecycle: N\/A (skipped)/' "$tmp/concurrency-report" > "$tmp/invalid"
if bash "$scripts/check-report.sh" "$tmp/invalid" > /dev/null 2>&1; then echo 'Required async scope accepted with no applicable check' >&2; exit 1; fi
echo 'PASS targeted async and Loom evidence, scope and escalation enforcement'
echo 'All Codex kit tests passed.'  
