"""Utility functions for merging PDF files with templates.

This module centralises the core logic used by both the command line
interface and the GUI so that future features can re-use the same
implementation.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator, List, Optional, Set, Tuple

import fitz  # PyMuPDF


_MM_TO_POINTS = 72.0 / 25.4

_POSITION_SETTINGS = {
    "top_left": ("top", fitz.TEXT_ALIGN_LEFT),
    "top_center": ("top", fitz.TEXT_ALIGN_CENTER),
    "top_right": ("top", fitz.TEXT_ALIGN_RIGHT),
    "bottom_left": ("bottom", fitz.TEXT_ALIGN_LEFT),
    "bottom_center": ("bottom", fitz.TEXT_ALIGN_CENTER),
    "bottom_right": ("bottom", fitz.TEXT_ALIGN_RIGHT),
}

_FONT_EXTENSIONS = (".ttf", ".otf", ".ttc", ".otc")

_ALLEGATO_PATTERN: re.Pattern[str] = re.compile(r"^allegato\s+([A-Za-z0-9]+)", re.IGNORECASE)


@dataclass
class PageNumberingOptions:
    """Configuration controlling how page numbers are added to PDFs."""

    position: str = "bottom_right"
    font_name: str = "Helvetica"
    font_file: Path | None = None
    font_size: float = 11.0
    margin_top_mm: float = 10.0
    margin_bottom_mm: float = 10.0
    margin_left_mm: float = 10.0
    margin_right_mm: float = 10.0

    def __post_init__(self) -> None:
        if isinstance(self.font_file, str):
            self.font_file = Path(self.font_file)

        if self.font_size <= 0:
            raise ValueError("font_size must be greater than zero")

        for attr in (
            "margin_top_mm",
            "margin_bottom_mm",
            "margin_left_mm",
            "margin_right_mm",
        ):
            value = getattr(self, attr)
            if value < 0:
                raise ValueError(f"{attr} must be greater than or equal to zero")

        normalized = self.position.strip().lower().replace(" ", "_")
        if normalized not in _POSITION_SETTINGS:
            valid = ", ".join(sorted(name.replace("_", " ") for name in _POSITION_SETTINGS))
            raise ValueError(f"position must be one of: {valid}")
        self.position = normalized


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
    page_numbering: PageNumberingOptions | None = None

    def __post_init__(self) -> None:
        if self.scale_percent <= 0:
            raise ValueError("scale_percent must be greater than zero")

        if self.enumerate_pages:
            if self.page_numbering is None:
                self.page_numbering = PageNumberingOptions()
            elif not isinstance(self.page_numbering, PageNumberingOptions):
                raise TypeError("page_numbering must be a PageNumberingOptions instance")


@dataclass
class RoipamOptions:
    """Settings that control ROIPAM batch processing."""

    scale_percent: float = 85.0
    remove_first_page: bool = True
    append_only: bool = False
    enumerate_pages: bool = False
    page_numbering: PageNumberingOptions | None = None

    def __post_init__(self) -> None:
        if self.scale_percent <= 0:
            raise ValueError("scale_percent must be greater than zero")

        if self.enumerate_pages:
            if self.page_numbering is None:
                self.page_numbering = PageNumberingOptions()
            elif not isinstance(self.page_numbering, PageNumberingOptions):
                raise TypeError("page_numbering must be a PageNumberingOptions instance")


@dataclass
class RoipamMergeResult:
    """Outcome of a single ROIPAM merge operation."""

    allegato_id: str
    input_path: Path
    template_path: Path
    output_path: Path
    success: bool
    message: str = ""


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


def _extract_allegato_id(path: Path) -> str | None:
    match = _ALLEGATO_PATTERN.match(path.name)
    if not match:
        return None
    return match.group(1).strip()


def _is_roipam_annex(path: Path) -> bool:
    return bool(_extract_allegato_id(path))


def _iter_cover_candidates(folder: Path, annex_path: Path) -> Iterator[Path]:
    for candidate in folder.glob("*.[Pp][Dd][Ff]"):
        if candidate == annex_path:
            continue
        if _is_roipam_annex(candidate):
            continue
        if candidate.stem.lower().endswith("_temp"):
            continue
        yield candidate


def _find_roipam_cover(folder: Path, annex_path: Path, allegato_id: str) -> Path | None:
    preferred = f" - allegato {allegato_id} - ".lower()
    fallback = f"allegato {allegato_id}".lower()

    candidates = list(_iter_cover_candidates(folder, annex_path))

    for candidate in candidates:
        if preferred in candidate.name.lower():
            return candidate

    for candidate in candidates:
        if fallback in candidate.name.lower():
            return candidate

    return None


def _copy_with_duplicate_first_page(input_pdf: Path, destination: Path) -> None:
    source = fitz.open(str(input_pdf))
    duplicated = fitz.open()
    try:
        if len(source) == 0:
            raise ValueError(f"Input PDF is empty: {input_pdf}")

        duplicated.insert_pdf(source, from_page=0, to_page=0)
        duplicated.insert_pdf(source)
        duplicated.save(str(destination))
    finally:
        duplicated.close()
        source.close()


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

        if config.enumerate_pages and config.page_numbering is not None:
            _apply_page_numbers(output_path, config.page_numbering)
    finally:
        # Always remove any temporary templates we created.
        for temp_path in temporary_paths:
            if temp_path.exists():
                temp_path.unlink()

        if config.delete_template and template_path.exists():
            if not needs_temp_copy:
                template_path.unlink()


def process_roipam_folder(folder: Path, options: RoipamOptions) -> List[RoipamMergeResult]:
    """Merge all ROIPAM attachments within ``folder``.

    The function mirrors the legacy automation script: it pairs each
    ``Allegato X`` PDF with the corresponding cover, applies special
    handling for Allegato D and E, and writes the merged output inside a
    ``MERGED`` subdirectory. Source files are never deleted.
    """

    if not folder.is_dir():
        raise ValueError("ROIPAM folder must be an existing directory")

    merged_dir = folder / "MERGED"
    merged_dir.mkdir(parents=True, exist_ok=True)

    results: List[RoipamMergeResult] = []
    annexes = sorted(
        path for path in folder.glob("*.[Pp][Dd][Ff]") if _is_roipam_annex(path)
    )

    for annex_path in annexes:
        allegato_id = _extract_allegato_id(annex_path)
        if not allegato_id:
            results.append(
                RoipamMergeResult(
                    allegato_id="",
                    input_path=annex_path,
                    template_path=annex_path,
                    output_path=merged_dir / annex_path.name,
                    success=False,
                    message="Unable to extract allegato ID",
                )
            )
            continue

        cover_path = _find_roipam_cover(folder, annex_path, allegato_id)
        if cover_path is None:
            results.append(
                RoipamMergeResult(
                    allegato_id=allegato_id,
                    input_path=annex_path,
                    template_path=annex_path,
                    output_path=merged_dir / annex_path.name,
                    success=False,
                    message="No matching cover found",
                )
            )
            continue

        output_path = merged_dir / cover_path.name
        input_for_merge = annex_path
        temporary_paths: List[Path] = []
        append_only = options.append_only

        try:
            allegato_tag = allegato_id.upper()
            if allegato_tag == "E":
                append_only = True
            elif allegato_tag == "D":
                duplicate_path = folder / f"{annex_path.stem}_roipam_temp{annex_path.suffix}"
                _copy_with_duplicate_first_page(annex_path, duplicate_path)
                temporary_paths.append(duplicate_path)
                input_for_merge = duplicate_path

            config = MergeConfig(
                template_path=cover_path,
                input_path=input_for_merge,
                output_path=output_path,
                scale_percent=options.scale_percent,
                remove_first_page=options.remove_first_page,
                delete_template=False,
                append_only=append_only,
                enumerate_pages=options.enumerate_pages,
                page_numbering=options.page_numbering,
            )

            merge_pdfs(config)
        except Exception as exc:  # pragma: no cover - guarded per-attachment
            results.append(
                RoipamMergeResult(
                    allegato_id=allegato_id,
                    input_path=annex_path,
                    template_path=cover_path,
                    output_path=output_path,
                    success=False,
                    message=str(exc),
                )
            )
        else:
            results.append(
                RoipamMergeResult(
                    allegato_id=allegato_id,
                    input_path=annex_path,
                    template_path=cover_path,
                    output_path=output_path,
                    success=True,
                    message="Merged",
                )
            )
        finally:
            for temp_path in temporary_paths:
                temp_path.unlink(missing_ok=True)

    return results


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


def _apply_page_numbers(output_pdf: Path, options: PageNumberingOptions) -> None:
    """Add page numbers to ``output_pdf`` based on ``options``."""

    temp_path = output_pdf.with_name(f"{output_pdf.stem}_temp_enumerating{output_pdf.suffix}")
    shutil.copy2(output_pdf, temp_path)

    try:
        document = fitz.open(str(temp_path))
        try:
            for index, page in enumerate(document, start=1):
                _insert_page_number(page, index, options)
            document.save(str(output_pdf), incremental=False)
        finally:
            document.close()
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _insert_page_number(page: fitz.Page, number: int, options: PageNumberingOptions) -> None:
    vertical, alignment = _POSITION_SETTINGS[options.position]
    rect = page.rect

    left_margin = options.margin_left_mm * _MM_TO_POINTS
    right_margin = options.margin_right_mm * _MM_TO_POINTS
    top_margin = options.margin_top_mm * _MM_TO_POINTS
    bottom_margin = options.margin_bottom_mm * _MM_TO_POINTS

    available_width = rect.width - left_margin - right_margin
    if available_width <= 0:
        raise ValueError("Margins leave no horizontal space for page numbers")

    fontname, fontfile, font_obj = _resolve_font_specification(options)
    text = str(number)
    text_width = font_obj.text_length(text, options.font_size)

    if text_width > available_width:
        raise ValueError("Page number text does not fit within the specified margins")

    if alignment == fitz.TEXT_ALIGN_LEFT:
        x = rect.x0 + left_margin
    elif alignment == fitz.TEXT_ALIGN_CENTER:
        x = rect.x0 + left_margin + (available_width - text_width) / 2
    else:
        x = rect.x1 - right_margin - text_width

    if vertical == "top":
        baseline = rect.y0 + top_margin + font_obj.ascender * options.font_size
    else:
        baseline = rect.y1 - bottom_margin + font_obj.descender * options.font_size

    if baseline <= rect.y0:
        raise ValueError("Margins leave no vertical space for page numbers")

    page.insert_text(
        (x, baseline),
        text,
        fontsize=options.font_size,
        fontname=fontname,
        fontfile=fontfile,
    )


def _resolve_font_specification(
    options: PageNumberingOptions,
) -> Tuple[str, Optional[str], fitz.Font]:
    if options.font_file:
        font_path = Path(options.font_file)
        sanitized = _sanitize_font_name(options.font_name or font_path.stem)
        try:
            font_obj = fitz.Font(fontfile=str(font_path))
        except RuntimeError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unable to load font file: {font_path}") from exc
        return sanitized, str(font_path), font_obj

    fontname = options.font_name or "Helvetica"
    font_obj = fitz.Font(fontname=fontname)
    return fontname, None, font_obj


def _sanitize_font_name(name: str) -> str:
    cleaned = "".join(ch for ch in name if ch.isalnum())
    return cleaned or "CustomFont"


def _font_search_directories() -> List[Path]:
    system = platform.system().lower()
    candidates: List[Path] = []

    if system == "windows":
        windir = Path(os.environ.get("WINDIR", "C:\\Windows"))
        candidates.append(windir / "Fonts")
    elif system == "darwin":
        candidates.extend(
            [
                Path("/System/Library/Fonts"),
                Path("/Library/Fonts"),
                Path.home() / "Library" / "Fonts",
            ]
        )
    else:
        candidates.extend(
            [
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                Path.home() / ".fonts",
            ]
        )

    existing: List[Path] = []
    for candidate in candidates:
        if candidate.exists():
            existing.append(candidate)
    return existing


def _iter_font_files() -> Iterator[Path]:
    seen: Set[Path] = set()
    for directory in _font_search_directories():
        for suffix in _FONT_EXTENSIONS:
            for path in directory.rglob(f"*{suffix}"):
                try:
                    resolved = path.resolve()
                except OSError:
                    continue
                if resolved in seen:
                    continue
                seen.add(resolved)
                yield resolved


@lru_cache(maxsize=1)
def list_available_fonts() -> dict[str, Optional[Path]]:
    """Return a mapping of available font names to optional file paths."""

    fonts: dict[str, Optional[Path]] = {name: None for name in fitz.Base14_fontnames}

    for font_path in _iter_font_files():
        try:
            font = fitz.Font(fontfile=str(font_path))
        except (RuntimeError, ValueError):
            continue

        display_name = font.name.strip() or font_path.stem
        fonts.setdefault(display_name, font_path)

    return dict(sorted(fonts.items(), key=lambda item: item[0].lower()))


__all__ = [
    "MergeConfig",
    "PageNumberingOptions",
    "RoipamMergeResult",
    "RoipamOptions",
    "merge_pdfs",
    "process_roipam_folder",
    "list_available_fonts",
]

