@echo off
chcp 65001 >nul
echo ========================================
echo   Tricard - Landlord Card Game
echo ========================================
echo.

:: Check venv
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run: uv venv .venv --python 3.11
    pause
    exit /b 1
)

:: Install backend deps
echo [1/4] Checking backend dependencies...
.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt 2>nul

:: Seed DB and AI accounts
echo [2/4] Initializing database...
.venv\Scripts\python.exe backend\scripts\seed_ai.py --ensure >nul

:: Build frontend
echo [3/4] Building frontend...
cd frontend
call npm install --silent 2>nul
call npx vite build --logLevel error
cd ..

:: Start server
echo [4/4] Starting server (port 8000)...
echo.
echo   LAN access: http://<your-ip>:8000
echo   Press Ctrl+C to stop
echo.
.venv\Scripts\python.exe -m uvicorn app.main:sio_app --app-dir backend --host 0.0.0.0 --port 8000

pause