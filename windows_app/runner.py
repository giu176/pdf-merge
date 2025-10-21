"""Main entry point shared by the Windows executable and module."""

from __future__ import annotations

import sys
from typing import Iterable

from pdf_processing import merge_pdfs

from .cli import build_parser, namespace_to_config


def _run_cli(namespace) -> None:
    config = namespace_to_config(namespace)
    merge_pdfs(config)
    print(f"PDF created at: {config.output_path}")


def _launch_gui(parser) -> None:
    try:
        from .gui import launch_gui
    except RuntimeError as exc:  # pragma: no cover - depends on tkinter availability
        parser.error(str(exc))
        return

    try:
        launch_gui()
    except RuntimeError as exc:  # pragma: no cover - GUI convenience
        parser.error(str(exc))


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.gui or not (args.template and args.input and args.output):
        _launch_gui(parser)
        return 0

    try:
        _run_cli(args)
    except Exception as exc:  # pragma: no cover - CLI convenience
        parser.error(str(exc))
    return 0


if __name__ == "__main__":  # pragma: no cover - module executable support
    raise SystemExit(main(sys.argv[1:]))


__all__ = ["main"]
