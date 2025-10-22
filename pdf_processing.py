"""Utility functions for merging PDF files with templates.

This module centralises the core logic used by both the command line
interface and the GUI so that future features can re-use the same
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF


_POSITION_ALIGNMENTS: Dict[str, int] = {
    "top_left": fitz.TEXT_ALIGN_LEFT,
    "top_center": fitz.TEXT_ALIGN_CENTER,
    "top_right": fitz.TEXT_ALIGN_RIGHT,
    "bottom_left": fitz.TEXT_ALIGN_LEFT,
    "bottom_center": fitz.TEXT_ALIGN_CENTER,
    "bottom_right": fitz.TEXT_ALIGN_RIGHT,
}

_MM_TO_POINTS = 72.0 / 25.4


@dataclass
class PageNumberingConfig:
    """Configuration options controlling page enumeration output."""

    position: str = "bottom_right"
    font_path: Path | str | None = None
    font_size: float = 11.0
    margin_top_mm: float = 10.0
    margin_bottom_mm: float = 10.0
    margin_left_mm: float = 10.0
    margin_right_mm: float = 10.0

    def __post_init__(self) -> None:
        valid_positions = {
            "top_left",
            "top_center",
            "top_right",
            "bottom_left",
            "bottom_center",
            "bottom_right",
        }
        if self.position not in valid_positions:
            raise ValueError(f"Unsupported page number position: {self.position}")

        if isinstance(self.font_path, str):
            self.font_path = Path(self.font_path).expanduser()
        if isinstance(self.font_path, Path):
            if not self.font_path.exists():
                raise ValueError(f"Font file does not exist: {self.font_path}")
        elif self.font_path is not None:
            raise TypeError("font_path must be a path, string or None")

        if self.font_size <= 0:
            raise ValueError("font_size must be greater than zero")

        for name in ("margin_top_mm", "margin_bottom_mm", "margin_left_mm", "margin_right_mm"):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(f"{name} must be zero or positive")


@dataclass
class MergeConfig:
    """Configuration options for the merge operation."""

    template_path: Path
    input_path: Path
    output_path: Path
    scale_percent: float = 85.0
    remove_first_page: bool = True
    delete_template: bool = False
    append_only: bool = False
    enumerate_pages: bool = False
    page_numbering: PageNumberingConfig | None = None

    def __post_init__(self) -> None:
        if self.scale_percent <= 0:
            raise ValueError("scale_percent must be greater than zero")

        if self.enumerate_pages and self.page_numbering is None:
            raise ValueError("Page numbering options are required when enumerate_pages is True")


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


def _ensure_template_has_multiple_pages(template_path: Path) -> Tuple[Path, Optional[Path]]:
    """Return a template path guaranteed to contain at least two pages."""

    template_doc = fitz.open(str(template_path))
    try:
        if len(template_doc) != 1:
            return template_path, None

        temp_path = template_path.parent / "template_one_page_temp.pdf"
        writer = fitz.open()
        try:
            writer.insert_pdf(template_doc)
            writer.insert_pdf(template_doc)
            writer.save(str(temp_path))
        finally:
            writer.close()

        return temp_path, temp_path
    finally:
        template_doc.close()


def merge_pdfs(config: MergeConfig) -> None:
    """Merge PDFs according to the supplied configuration."""

    template_path = config.template_path
    input_path = config.input_path
    output_path = config.output_path

    template_path_to_use: Optional[Path] = None
    temporary_paths: List[Path] = []
    needs_temp_copy = (
        template_path.resolve(strict=False) == output_path.resolve(strict=False)
    )

    drop_first_template_page = False

    try:
        if needs_temp_copy:
            template_path_to_use = _prepare_template_copy(template_path)
            if template_path_to_use != template_path:
                temporary_paths.append(template_path_to_use)
        else:
            template_path_to_use = template_path
        if not config.append_only:
            template_path_to_use, single_page_temp = _ensure_template_has_multiple_pages(
                template_path_to_use
            )
            if single_page_temp is not None:
                temporary_paths.append(single_page_temp)
                drop_first_template_page = True

        if config.append_only:
            _append_documents(
                template_path_to_use,
                input_path,
                output_path,
                remove_first_page=config.remove_first_page,
            )
        else:
            _merge_documents(
                template_path_to_use,
                input_path,
                output_path,
                scale=config.scale_percent / 100.0,
                remove_first_page=config.remove_first_page,
                drop_first_template_page=drop_first_template_page,
            )
    finally:
        # Always remove any temporary templates we created.
        for temp_path in temporary_paths:
            if temp_path.exists():
                temp_path.unlink()

        if config.delete_template and template_path.exists():
            if not needs_temp_copy:
                template_path.unlink()

    if config.enumerate_pages and config.page_numbering is not None:
        _enumerate_output_pdf(output_path, config.page_numbering)


def _merge_documents(
    template_pdf: Path,
    input_pdf: Path,
    output_pdf: Path,
    *,
    scale: float,
    remove_first_page: bool,
    drop_first_template_page: bool = False,
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
        if drop_first_template_page and len(writer) > 0:
            writer.delete_page(0)
        writer.save(str(output_pdf))
    finally:
        writer.close()
        template_doc.close()
        input_doc.close()


def _append_documents(
    template_pdf: Path,
    input_pdf: Path,
    output_pdf: Path,
    *,
    remove_first_page: bool,
) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    template_doc = fitz.open(str(template_pdf))
    input_doc = fitz.open(str(input_pdf))

    writer = fitz.open()

    try:
        writer.insert_pdf(template_doc)

        start_page = 1 if remove_first_page and len(input_doc) > 0 else 0
        if start_page < len(input_doc):
            writer.insert_pdf(
                input_doc,
                from_page=start_page,
                to_page=len(input_doc) - 1,
            )

        writer.save(str(output_pdf))
    finally:
        writer.close()
        template_doc.close()
        input_doc.close()


def _mm_to_points(value: float) -> float:
    return value * _MM_TO_POINTS


def _numbering_rect(page_rect: fitz.Rect, config: PageNumberingConfig) -> fitz.Rect:
    left = _mm_to_points(config.margin_left_mm)
    right = _mm_to_points(config.margin_right_mm)
    top = _mm_to_points(config.margin_top_mm)
    bottom = _mm_to_points(config.margin_bottom_mm)

    width = page_rect.width - left - right
    if width <= 0:
        raise ValueError("Margins leave no horizontal space for page numbers")

    box_height = config.font_size * 1.5
    if config.position.startswith("top"):
        y0 = top
        y1 = y0 + box_height
    else:
        y1 = page_rect.height - bottom
        y0 = y1 - box_height

    if y0 < 0 or y1 > page_rect.height or y1 <= y0:
        raise ValueError("Margins leave no vertical space for page numbers")

    return fitz.Rect(left, y0, page_rect.width - right, y1)


def _enumerate_output_pdf(output_pdf: Path, config: PageNumberingConfig) -> None:
    temp_path = output_pdf.with_name(f"{output_pdf.stem}_temp_enumerating{output_pdf.suffix}")
    shutil.copy2(output_pdf, temp_path)

    doc = fitz.open(str(temp_path))
    try:
        align = _POSITION_ALIGNMENTS[config.position]
        font_kwargs: Dict[str, object]
        if config.font_path is not None:
            font_kwargs = {"fontfile": str(config.font_path)}
        else:
            font_kwargs = {"fontname": "helv"}

        for index, page in enumerate(doc, start=1):
            rect = _numbering_rect(page.rect, config)
            page.insert_textbox(
                rect,
                str(index),
                fontsize=config.font_size,
                align=align,
                **font_kwargs,
            )

        doc.save(str(output_pdf))
    finally:
        doc.close()
        if temp_path.exists():
            temp_path.unlink()

