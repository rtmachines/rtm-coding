#!/usr/bin/env bash
# Run shared contracts against installed Claude scripts, never synthetic model reviews.
set -euo pipefail
kit=$(cd "$(dirname "$0")/.." && pwd)
RUST_REVIEW_RUNTIME=claude bash "$kit/tests/test-codex.sh"
