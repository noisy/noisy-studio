#!/bin/sh
# Run from a permanent checkout: linked worktrees share its Git hook directory.
set -eu
cd "$(dirname "$0")/.."
uv sync --frozen
npm ci
npm ci --prefix dashboard
npm ci --prefix website
npm ci --prefix desktop --ignore-scripts
# Default migration mode preserves/chains existing hooks. Never use --overwrite.
uv run --frozen pre-commit install
