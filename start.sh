#!/bin/bash
# =========================================================
# VeriCall Malaysia - One-Click Startup (Mac/Linux)
# =========================================================
# Prerequisites: Python 3.11+, Node.js 18+
# =========================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "============================================"
echo "  VeriCall Malaysia - Starting All Services"
echo "============================================"
echo ""

# --- Backend ---
echo "[1/3] Starting Backend (Flask + AI Engine)..."
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "     Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt --quiet 2>/dev/null

echo "     Backend starting on http://localhost:5000"
python -m app.main &
BACKEND_PID=$!

# --- Web App ---
echo "[2/3] Starting Web App (Uncle Ah Hock Panel)..."
cd "$SCRIPT_DIR/uncle-ah-hock---johor-kopi-chat"

if [ ! -d "node_modules" ]; then
    echo "     Installing npm dependencies..."
    npm install
fi

echo "     Web app starting on http://localhost:3000"
npm run dev &
WEB_PID=$!

# --- Summary ---
echo ""
echo "[3/3] Done! Services running."
echo ""
echo "============================================"
echo "  Backend API:  http://localhost:5000"
echo "  Web App:      http://localhost:3000"
echo "  Audio Relay:  ws://localhost:8765"
echo "============================================"
echo ""
echo "For the mobile app, run in the mobile/ folder:"
echo "  flutter run --dart-define=VERICALL_API_BASE_URL=http://YOUR_IP:5000/api"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for background processes
trap "kill $BACKEND_PID $WEB_PID 2>/dev/null; exit 0" INT TERM
wait
