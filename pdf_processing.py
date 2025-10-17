"""Utility functions for merging PDF files with templates.

This module centralises the core logic used by both the command line
interface and the GUI so that future features can re-use the same
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Optional

import fitz  # PyMuPDF


@dataclass
class MergeConfig:
    """Configuration options for the merge operation."""

    template_path: Path
    input_path: Path
    output_path: Path
    scale_percent: float = 85.0
    remove_first_page: bool = True
    delete_template: bool = False

    def __post_init__(self) -> None:
        if self.scale_percent <= 0:
            raise ValueError("scale_percent must be greater than zero")


def _with_template_suffix(path: Path) -> Path:
    """Return a new path with ``_temp`` appended before the suffix."""

    return path.with_name(f"{path.stem}_temp{path.suffix}")


def _prepare_template_copy(template_path: Path) -> Path:
    """Copy the template so the output can re-use the original file name."""

    suffixed_path = _with_template_suffix(template_path)
    if template_path.resolve() == suffixed_path.resolve():
        # The template already follows the naming convention.
        return template_path

    shutil.copy2(template_path, suffixed_path)
    return suffixed_path


def merge_pdfs(config: MergeConfig) -> None:
    """Merge PDFs according to the supplied configuration."""

    template_path = config.template_path
    input_path = config.input_path
    output_path = config.output_path

    template_path_to_use: Optional[Path] = None
    needs_temp_copy = (
        template_path.resolve(strict=False) == output_path.resolve(strict=False)
    )

    try:
        if needs_temp_copy:
            template_path_to_use = _prepare_template_copy(template_path)
        else:
            template_path_to_use = template_path
        _merge_documents(
            template_path_to_use,
            input_path,
            output_path,
            scale=config.scale_percent / 100.0,
            remove_first_page=config.remove_first_page,
        )
    finally:
        # Always remove the suffixed copy if we created one.
        if (
            template_path_to_use
            and template_path_to_use != template_path
            and template_path_to_use.exists()
        ):
            template_path_to_use.unlink()

        if config.delete_template and template_path.exists():
            used_temp_copy = (
                template_path_to_use is not None
                and template_path_to_use != template_path
            )
            same_as_output = needs_temp_copy

            if not used_temp_copy and not same_as_output:
                template_path.unlink()


def _merge_documents(
    template_pdf: Path,
    input_pdf: Path,
    output_pdf: Path,
    *,
    scale: float,
    remove_first_page: bool,
) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    template_doc = fitz.open(str(template_pdf))
    input_doc = fitz.open(str(input_pdf))

    writer = fitz.open()

    try:
        for page in template_doc:
            writer.insert_pdf(template_doc, from_page=page.number, to_page=page.number)

        last_template_page = template_doc[-1]
        last_template_rect = last_template_page.rect

        start_page = 1 if remove_first_page and len(input_doc) > 0 else 0

        for page_index in range(start_page, len(input_doc)):
            input_page = input_doc[page_index]
            input_rect = input_page.rect

            new_page = writer.new_page(
                width=last_template_rect.width, height=last_template_rect.height
            )
            new_page.show_pdf_page(
                last_template_rect, template_doc, len(template_doc) - 1
            )

            scale_x = (last_template_rect.width / input_rect.width) * scale
            scale_y = (last_template_rect.height / input_rect.height) * scale
            scale_factor = min(scale_x, scale_y)

            new_width = input_rect.width * scale_factor
            new_height = input_rect.height * scale_factor

            x_offset = (last_template_rect.width - new_width) / 2
            y_offset = (last_template_rect.height - new_height) / 2

            new_page.show_pdf_page(
                fitz.Rect(
                    x_offset,
                    y_offset,
                    x_offset + new_width,
                    y_offset + new_height,
                ),
                input_doc,
                page_index,
            )

        writer.delete_page(len(template_doc) - 1)
        writer.save(str(output_pdf))
    finally:
        writer.close()
        template_doc.close()
        input_doc.close()

