#!/usr/bin/env bash
# Replay frozen source with the current review skill, without exposing old results.
set -euo pipefail
kit=$(cd "$(dirname "$0")/../.." && pwd)
root=${1:?Usage: create-concurrency-retest.sh NEW_DIRECTORY}
[[ ! -e "$root" ]] || { echo 'Destination exists' >&2; exit 2; }
mkdir -p "$root/evidence" "$root/frozen"
root=$(cd "$root" && pwd)
tar -xzf "$kit/tests/e2e/results/2026-10-24-advanced/example-repositories.tar.gz" -C "$root/frozen" case-a case-d
mv "$root/frozen/case-a" "$root/r1"
mv "$root/frozen/case-d" "$root/r2"
rmdir "$root/frozen"
for case_name in r1 r2; do
  repo="$root/$case_name"
  (cd "$repo" && git ls-files -z src tests | sort -z | xargs -0 sha256sum) > "$root/evidence/$case_name-source-before.sha256"
  cp -r "$kit/codex-template/.agents/skills/rust-pr-review/." "$repo/.agents/skills/rust-pr-review/"
  # Preserve the project's feature policy, but update the kit-level review policy.
  sed -n '/^## Runtime bridge project policy/,$p' "$repo/REVIEW.md" > "$root/evidence/$case_name-project-policy.txt"
  cp "$kit/codex-template/REVIEW.md" "$repo/REVIEW.md"
  cat "$root/evidence/$case_name-project-policy.txt" >> "$repo/REVIEW.md"
  (cd "$repo" && git add .agents/skills/rust-pr-review REVIEW.md && git -c user.name='Workflow Fixture' -c user.email=fixture@example.invalid commit -qm 'Require targeted concurrency validation in review')
  (cd "$repo" && git ls-files -z src tests | sort -z | xargs -0 sha256sum) > "$root/evidence/$case_name-source-after-setup.sha256"
  diff -u "$root/evidence/$case_name-source-before.sha256" "$root/evidence/$case_name-source-after-setup.sha256"
done
printf '%s\n' "$root"
