#!/bin/bash
set -e

echo "[RIFT] Starting Rift - Portal & Anomaly Tracker..."

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing / updating dependencies..."
pip install -r requirements.txt --quiet

echo "Launching Rift..."
python -m rift
