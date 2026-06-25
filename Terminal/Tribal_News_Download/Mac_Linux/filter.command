#!/bin/bash

# 1. Force navigate to the script's directory
cd "$(dirname "$0")"

echo "[STEP 3] Starting the Filtering Process..."

# 2. Check and Activate venv
if [ -d "venv" ]; then
    source "venv/bin/activate"
    
    # 3. Run app.py inside the program folder
    cd "program"
    python3 app.py
else
    echo "[ERROR] Virtual environment not found. Please run install.command first."
    exit 1
fi

echo ""
echo "Filtering process finished. You can close this window."