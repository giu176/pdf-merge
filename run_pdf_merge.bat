@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "EXE=%SCRIPT_DIR%windows_app\dist\pdf-merge.exe"

if exist "%EXE%" (
    start "" "%EXE%"
    exit /b 0
)

echo The Windows executable could not be found.
echo Expected location: %EXE%
echo.
echo Build the self-contained binary with:
echo     py -3.11 windows_app\build_exe.py
echo or run PyInstaller manually using windows_app\pyinstaller.spec.
exit /b 1
