"""Standalone script used as the PyInstaller entry point."""

from __future__ import annotations

from windows_app.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
