#!/usr/bin/env bash
set -e
cz bump "$@"
git push origin main --tags
