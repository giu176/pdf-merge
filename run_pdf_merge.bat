@echo off
setlocal EnableDelayedExpansion

REM Ensure the repository exists and is up to date before launching the GUI
set "WSL_SCRIPT=set -euo pipefail; REPO_DIR=/home/pdf-merge; UPDATED=0; if [ ! -d "$REPO_DIR/.git" ]; then git clone https://github.com/giu176/pdf-merge.git "$REPO_DIR"; UPDATED=1; else cd "$REPO_DIR"; git remote get-url origin >/dev/null 2>&1 || git remote add origin https://github.com/giu176/pdf-merge.git; git fetch origin; if git status -sb 2>/dev/null | grep -q '[[]behind'; then git pull --ff-only; UPDATED=1; fi; fi; cd "$REPO_DIR"; if [ $UPDATED -eq 1 ]; then if [ -x install.sh ]; then ./install.sh; else bash install.sh; fi; fi; if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi; python3 pdf.py"
wsl.exe -d Debian -- bash -lc "%WSL_SCRIPT%"

pause
