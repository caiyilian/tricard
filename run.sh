#!/bin/bash
set -e

echo "========================================"
echo "  Tricard 斗地主 - 一键启动"
echo "========================================"
echo ""

# Check venv
if [ ! -f ".venv/bin/python" ]; then
    echo "[ERROR] .venv not found. Run: uv venv .venv --python 3.11"
    exit 1
fi

# Install deps
echo "[1/4] Installing backend dependencies..."
.venv/bin/pip install -q -r backend/requirements.txt 2>/dev/null

# Seed DB & AI accounts
echo "[2/4] Initializing database..."
.venv/bin/python backend/scripts/seed_ai.py --ensure 2>/dev/null

# Build frontend
echo "[3/4] Building frontend..."
cd frontend
npm install --silent 2>/dev/null
npx vite build --logLevel error 2>/dev/null
cd ..

# Start
echo "[4/4] Starting server (port 8000)..."
echo ""
echo "  LAN access: http://<your-ip>:8000"
echo "  Press Ctrl+C to stop"
echo ""
.venv/bin/python -m uvicorn app.main:sio_app --app-dir backend --host 0.0.0.0 --port 8000