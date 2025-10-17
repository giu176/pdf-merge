@echo off
setlocal

REM Ensure Debian WSL distribution is installed
for /f "delims=" %%I in ('wsl.exe -l -q ^| findstr /i /c:"Debian"') do set "DEBIAN_INSTALLED=1"

if not defined DEBIAN_INSTALLED (
    echo Debian WSL distribution not found. Attempting installation...
    wsl.exe --install -d Debian
    if errorlevel 1 (
        echo Failed to install Debian. Please install WSL Debian manually and rerun this script.
        pause
        exit /b 1
    )
    echo Debian installation initiated. If prompted, please restart your computer and rerun this script.
    pause
    exit /b 0
)

REM Clone repository if missing and run install script
wsl.exe -d Debian -e /bin/bash -lc "\
    if [ ! -d /home/pdf-merge ]; then \
        git clone https://github.com/giu176/pdf-merge.git /home/pdf-merge; \
    fi && \
    cd /home/pdf-merge && \
    if [ -x install.sh ]; then ./install.sh; else bash install.sh; fi && \
    if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi && \
    python3 pdf.py"

pause
