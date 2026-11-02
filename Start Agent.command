#!/bin/bash
# Double-click in Finder: starts the NAZAR root-cause agent (port 8766). Close the window to stop it.
cd "$(dirname "$0")"
if lsof -nP -iTCP:8766 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Something is already listening on port 8766:"
  lsof -nP -iTCP:8766 -sTCP:LISTEN
  echo "The agent is probably already running. Press Enter to close."
  read -r
  exit 0
fi
echo "NAZAR root-cause agent - http://127.0.0.1:8766  (Ctrl+C or close this window to stop)"
./run.sh
echo "Agent stopped. Press Enter to close."
read -r
