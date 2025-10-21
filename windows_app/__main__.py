"""Allow ``python -m windows_app`` to launch the Windows entry point."""

from .runner import main

if __name__ == "__main__":
    raise SystemExit(main())
