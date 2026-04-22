@echo off
REM ====================================================================
REM  NMDA Analysis App - Windows one-click launcher
REM
REM  WHAT THIS DOES (only the first time):
REM   1. Checks that Python is installed
REM   2. Creates a private "venv" folder so dependencies don't pollute
REM      your system Python
REM   3. Installs everything from requirements.txt
REM   4. Launches the app in your default browser
REM
REM  After the first run, every subsequent launch is instant.
REM
REM  TO USE: just double-click this file.
REM ====================================================================

setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo   NMDA Antagonist Study - Analysis App
echo ============================================================
echo.

REM --- Step 1. Verify Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed or not on your PATH.
    echo.
    echo Please install Python 3.10 or newer from:
    echo   https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

REM --- Step 2. Create venv if missing ---
if not exist "venv\Scripts\python.exe" (
    echo [SETUP] Creating private Python environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

REM --- Step 3. Install / update dependencies ---
echo [SETUP] Installing dependencies (first run only - takes ~2 min)...
call venv\Scripts\activate
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM --- Step 4. Launch the app ---
echo.
echo [READY] Launching app in your browser...
echo         (close this window to stop the app)
echo.
streamlit run app.py

pause
