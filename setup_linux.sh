#!/bin/bash
# Nova — Linux setup script (Ubuntu/Debian)
set -e

echo "=== Nova Linux Setup ==="

# 1. System dependencies
echo "[1/4] Installing system packages..."
sudo apt-get update -q
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    portaudio19-dev \
    nodejs npm \
    pulseaudio-utils \
    xdg-utils

# 2. Python venv + packages
echo "[2/4] Installing Python packages..."
cd "$(dirname "$0")/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 3. Frontend
echo "[3/4] Installing frontend packages..."
cd ../ui
npm install

# 4. Done
echo ""
echo "=== Setup complete ==="
echo ""
echo "To start Nova:"
echo "  Terminal 1 (backend):  cd backend && source .venv/bin/activate && python main.py"
echo "  Terminal 2 (frontend): cd ui && npm run dev"
echo ""
echo "Or use the start script:  ./start.sh"
