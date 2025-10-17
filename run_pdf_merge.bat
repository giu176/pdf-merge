@echo off
setlocal EnableDelayedExpansion

REM Ensure Debian WSL distribution is installed
for /f "delims=" %%I in ('wsl.exe -l -q 2^>nul ^| findstr /i /c:"Debian"') do set "DEBIAN_INSTALLED=1"

if not defined DEBIAN_INSTALLED (
    for /f "usebackq tokens=*" %%I in (`wsl.exe -l 2^>nul`) do (
        set "DISTRO=%%I"
        call :CHECK_DEBIAN
    )
)

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

goto :EOF

:CHECK_DEBIAN
set "LINE=!DISTRO!"
if not defined LINE goto :EOF
for /f "tokens=* delims= " %%J in ("!LINE!") do set "LINE=%%J"
if not defined LINE goto :EOF
if "!LINE:~0,1!"=="*" (
    set "LINE=!LINE:~1!"
    for /f "tokens=* delims= " %%J in ("!LINE!") do set "LINE=%%J"
)
for /f "tokens=1 delims=(" %%J in ("!LINE!") do set "LINE=%%J"
for /f "tokens=* delims= " %%J in ("!LINE!") do set "LINE=%%J"
if /I "!LINE!"=="Debian" set "DEBIAN_INSTALLED=1"
goto :EOF
