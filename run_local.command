#!/usr/bin/env bash
# ====================================================================
#  NMDA Analysis App - macOS / Linux one-click launcher
#
#  WHAT THIS DOES (only the first time):
#   1. Checks that python3 is installed
#   2. Creates a private "venv" folder so deps don't pollute system python
#   3. Installs everything from requirements.txt
#   4. Launches the app in your default browser
#
#  TO USE on macOS: double-click this file
#  (You may need to right-click -> Open the first time to bypass Gatekeeper.)
# ====================================================================

set -e
cd "$(dirname "$0")"

echo
echo "============================================================"
echo "  NMDA Antagonist Study - Analysis App"
echo "============================================================"
echo

# --- Step 1. Verify python3 ---
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 is not installed."
    echo
    echo "On macOS, install with Homebrew:   brew install python"
    echo "Or download from https://www.python.org/downloads/"
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

# --- Step 2. Create venv if missing ---
if [ ! -x "venv/bin/python" ]; then
    echo "[SETUP] Creating private Python environment..."
    python3 -m venv venv
fi

# --- Step 3. Install / update dependencies ---
echo "[SETUP] Installing dependencies (first run only - takes ~2 min)..."
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# --- Step 4. Launch the app ---
echo
echo "[READY] Launching app in your browser..."
echo "        (close this terminal window to stop the app)"
echo
streamlit run app.py
