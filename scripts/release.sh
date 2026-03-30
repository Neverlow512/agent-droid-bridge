#!/usr/bin/env bash
set -e

BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo "releases must be made from the main branch (currently on: $BRANCH)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CZ="${REPO_ROOT}/venv/bin/cz"

if [ ! -f "$CZ" ]; then
    echo "commitizen not found in venv — run: pip install -r requirements-dev.txt"
    exit 1
fi

"$CZ" bump "$@"
git push origin main --tags
