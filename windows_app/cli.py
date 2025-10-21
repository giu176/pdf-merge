"""Command line helpers for the Windows executable."""

from __future__ import annotations

import argparse
from pathlib import Path

from pdf_processing import MergeConfig


def _percentage(value: str) -> float:
    """Parse a positive floating point percentage value."""

    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Scale must be a number") from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError("Scale must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Return an argument parser configured for the Windows launcher."""

    parser = argparse.ArgumentParser(
        prog="pdf-merge",
        description=(
            "Merge a template PDF with another document. When launched without "
            "arguments the graphical interface is displayed."
        ),
    )
    parser.add_argument("template", nargs="?", help="Path to the template PDF")
    parser.add_argument("input", nargs="?", help="Path to the input PDF")
    parser.add_argument("output", nargs="?", help="Path to the output PDF")
    parser.add_argument(
        "--scale",
        type=_percentage,
        default=85.0,
        help="Scale percentage applied to the input pages (default: 85)",
    )
    parser.add_argument(
        "--keep-cover",
        action="store_false",
        dest="remove_first_page",
        help="Keep the first page of the input file instead of removing it",
    )
    parser.set_defaults(remove_first_page=True)
    parser.add_argument(
        "--append-only",
        action="store_true",
        help="Append the input document after the template without scaling",
    )
    parser.add_argument(
        "--delete-template",
        action="store_true",
        help="Delete the template file after the merge completes",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Force the graphical interface even if all arguments are provided",
    )
    return parser


def namespace_to_config(namespace: argparse.Namespace) -> MergeConfig:
    """Convert parsed arguments into a :class:`~pdf_processing.MergeConfig`."""

    if not namespace.template or not namespace.input or not namespace.output:
        raise ValueError("template, input and output paths are required")

    return MergeConfig(
        template_path=Path(namespace.template).expanduser(),
        input_path=Path(namespace.input).expanduser(),
        output_path=Path(namespace.output).expanduser(),
        scale_percent=namespace.scale,
        remove_first_page=namespace.remove_first_page,
        delete_template=namespace.delete_template,
        append_only=namespace.append_only,
    )


__all__ = ["build_parser", "namespace_to_config"]
