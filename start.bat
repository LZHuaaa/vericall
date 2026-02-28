@echo off
REM =========================================================
REM VeriCall Malaysia - One-Click Startup (Windows)
REM =========================================================
REM This script starts the backend + web app.
REM Prerequisites: Python 3.11+, Node.js 18+
REM =========================================================

echo.
echo ============================================
echo   VeriCall Malaysia - Starting All Services
echo ============================================
echo.

REM --- Backend ---
echo [1/3] Starting Backend (Flask + AI Engine)...
cd /d "%~dp0backend"

if not exist "venv\Scripts\activate.bat" (
    echo      Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet 2>nul

echo      Backend starting on http://localhost:5000
start "VeriCall Backend" cmd /k "call venv\Scripts\activate.bat && python -m app.main"

REM --- Web App ---
echo [2/3] Starting Web App (Uncle Ah Hock Panel)...
cd /d "%~dp0uncle-ah-hock---johor-kopi-chat"

if not exist "node_modules" (
    echo      Installing npm dependencies...
    call npm install
)

echo      Web app starting on http://localhost:3000
start "VeriCall Web" cmd /k "npm run dev"

REM --- Summary ---
echo.
echo [3/3] Done! Services starting in separate windows.
echo.
echo ============================================
echo   Backend API:  http://localhost:5000
echo   Web App:      http://localhost:3000
echo   Audio Relay:  ws://localhost:8765
echo ============================================
echo.
echo For the mobile app, run in the mobile/ folder:
echo   flutter run --dart-define=VERICALL_API_BASE_URL=http://YOUR_IP:5000/api
echo.
echo Press any key to exit this window...
pause >nul
