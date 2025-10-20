Set shell = CreateObject("WScript.Shell")
command = "wsl.exe -d Debian -e /bin/bash -lc ""cd /home/pdf-merge && if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi && python3 pdf.py"""
shell.Run command, 0, False
