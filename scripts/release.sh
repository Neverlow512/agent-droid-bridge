#!/usr/bin/env bash
set -e

BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo "releases must be made from the main branch (currently on: $BRANCH)"
    exit 1
fi

cz bump "$@"
git push origin main --tags
