@echo off
setlocal
REM Ensure the pdf-merge repository exists in /home, set up the virtual environment, and launch the GUI
wsl.exe -d Debian -e /bin/bash -lc 'set -e
REPO_DIR="/home/pdf-merge"
CLONED=0
if [ ! -d "$REPO_DIR" ]; then
    cd /home
    git clone https://github.com/giu176/pdf-merge.git
    CLONED=1
fi
cd "$REPO_DIR"
UPDATED=0
if [ -d .git ]; then
    BEFORE="$(git rev-parse HEAD 2>/dev/null || echo)"
    git pull --ff-only
    AFTER="$(git rev-parse HEAD 2>/dev/null || echo)"
    if [ "$BEFORE" != "$AFTER" ]; then
        UPDATED=1
    fi
fi
if [ ! -d .venv ] || [ "$CLONED" = "1" ] || [ "$UPDATED" = "1" ]; then
    bash install.sh
fi
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi
python3 pdf.py'
pause
