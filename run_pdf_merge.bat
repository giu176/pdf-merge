@echo off
setlocal
start "" /B wsl.exe -d Debian -e /bin/bash -lc "cd /home/pdf-merge && if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi && python3 pdf.py" >nul 2>&1
exit /b 0
