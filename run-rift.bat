@echo off
setlocal

echo [RIFT] Starting Rift - Portal & Anomaly Tracker...

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing / updating dependencies...
pip install -r requirements.txt --quiet

echo Launching Rift...
python -m rift

pause
