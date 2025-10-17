@echo off
setlocal

REM Launch Debian WSL, activate the project's virtual environment, and run pdf.py
wsl.exe -d Debian -e /bin/bash -lc "cd /home/pdf-merge && if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi && python3 pdf.py"

pause
