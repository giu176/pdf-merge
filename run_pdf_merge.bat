@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0run_pdf_merge.ps1"
exit /b %errorlevel%
