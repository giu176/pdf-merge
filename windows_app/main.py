"""Entry point for the Windows specific GUI wrapper."""

from __future__ import annotations

from .gui_windows import launch_gui


def main() -> None:
    """Launch the Windows GUI."""

    launch_gui()


if __name__ == "__main__":  # pragma: no cover - manual execution guard
    main()
