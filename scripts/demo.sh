#!/usr/bin/env bash
set -eu
umask 077
cd "$(dirname "$0")/.."
.venv/bin/python -m jobcompass.worker --once --semantic
.venv/bin/python -m jobcompass.worker --semantic &
refresh_pid=$!
trap 'kill "$refresh_pid" 2>/dev/null || true' EXIT
trap 'exit 130' INT TERM
.venv/bin/python -m jobcompass.serve
