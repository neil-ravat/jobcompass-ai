#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python -m jobcompass.worker --once --semantic
.venv/bin/python -m jobcompass.worker --semantic &
refresh_pid=$!
trap 'kill "$refresh_pid" 2>/dev/null || true' EXIT
trap 'exit 130' INT TERM
.venv/bin/python -m uvicorn jobcompass.api:app --host 127.0.0.1 --port "${JOBCOMPASS_PORT:-8765}"
