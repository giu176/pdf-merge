"""Command line and GUI entry points for the PDF merge utility."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from pdf_processing import MergeConfig, merge_pdfs


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise argparse.ArgumentTypeError("Scale must be a number") from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError("Scale must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Merge a template PDF with another document while scaling the content "
            "and optionally removing the first page. Run without arguments to "
            "launch the graphical interface."
        )
    )
    parser.add_argument("template", nargs="?", help="Path to the template PDF")
    parser.add_argument("input", nargs="?", help="Path to the input PDF")
    parser.add_argument("output", nargs="?", help="Path to the output PDF")
    parser.add_argument(
        "--scale",
        type=_positive_float,
        default=85.0,
        help="Scale percentage applied equally to both axes (default: 85)",
    )
    parser.add_argument(
        "--keep-cover",
        action="store_false",
        dest="remove_cover",
        help="Keep the first page of the input file instead of removing it",
    )
    parser.add_argument(
        "--delete-template",
        action="store_true",
        help="Delete the original template file after merging",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Force the graphical interface even if arguments are supplied",
    )
    return parser


def run_cli(args: argparse.Namespace) -> None:
    if not args.template or not args.input or not args.output:
        raise ValueError("Template, input and output paths are required for CLI usage")

    config = MergeConfig(
        template_path=Path(args.template),
        input_path=Path(args.input),
        output_path=Path(args.output),
        scale_percent=args.scale,
        remove_first_page=args.remove_cover,
        delete_template=args.delete_template,
    )
    merge_pdfs(config)
    print(f"Documento PDF creato: {config.output_path}")


def run_gui() -> None:
    from gui import launch_gui

    launch_gui()


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.gui or not (args.template and args.input and args.output):
        run_gui()
        return 0

    try:
        run_cli(args)
    except Exception as exc:  # pragma: no cover - CLI convenience
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

