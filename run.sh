#!/bin/bash
# Start the NAZAR root-cause agent on http://127.0.0.1:8766
#   ./run.sh                 (loads the local LLM in the background)
#   ./run.sh --no-preload    (loads it on the first report instead)
# Env: NAZAR_PY (Python with mlx-lm), NAZAR_LLM_DIR (model folder)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_PY="$HERE/../../10-AI/.venv/bin/python"
PY="${NAZAR_PY:-$DEFAULT_PY}"
if [ ! -x "$PY" ]; then
  echo "NAZAR_PY not found ($PY); using python3 - reports will use templates only (no mlx-lm)." >&2
  PY="$(command -v python3)"
fi
cd "$HERE"
exec "$PY" -m nazar_agent.service "$@"
