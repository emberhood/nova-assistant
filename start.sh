#!/bin/bash
# Start Jarvis (backend + frontend)
JARVIS_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[Jarvis] Starting backend..."
cd "$JARVIS_DIR/backend"
source .venv/bin/activate
python main.py &
BACKEND_PID=$!

sleep 2

echo "[Jarvis] Starting frontend..."
cd "$JARVIS_DIR/ui"
npm run dev &
FRONTEND_PID=$!

echo "[Jarvis] Running — backend PID=$BACKEND_PID, frontend PID=$FRONTEND_PID"
echo "[Jarvis] Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
