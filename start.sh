#!/bin/bash
# Start Nova (backend + frontend)
NOVA_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[Nova] Starting backend..."
cd "$NOVA_DIR/backend"
source .venv/bin/activate
python main.py &
BACKEND_PID=$!

sleep 2

echo "[Nova] Starting frontend..."
cd "$NOVA_DIR/ui"
npm run dev &
FRONTEND_PID=$!

echo "[Nova] Running — backend PID=$BACKEND_PID, frontend PID=$FRONTEND_PID"
echo "[Nova] Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
