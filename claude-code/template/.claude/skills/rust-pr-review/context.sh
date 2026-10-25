#!/usr/bin/env bash
# Compatibility entry point; base resolution failures remain failures.
set -euo pipefail
exec bash "$(dirname "${BASH_SOURCE[0]}")/scripts/context.sh" "$@"
