"""Tkinter based GUI for the PDF merge tool."""

from __future__ import annotations

import os
import platform
import subprocess
import tkinter as tk
import tkinter.ttk as ttk
from collections import OrderedDict
from pathlib import Path
from tkinter import filedialog, messagebox

from pdf_processing import MergeConfig, PageNumberingConfig, merge_pdfs


_IS_WSL = "microsoft" in platform.release().lower() or bool(os.environ.get("WSL_DISTRO_NAME"))


def _initial_browse_dir() -> Path:
    """Return a sensible starting directory for file dialogs."""
    if _IS_WSL:
        mnt_root = Path("/mnt")
        if mnt_root.exists():
            return mnt_root
        windows_home = Path("/mnt/c/Users")
        if windows_home.exists():
            return windows_home
    return Path.home()


_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
_DEFAULT_FONT_LABEL = "Helvetica (built-in)"


def _candidate_font_dirs() -> list[Path]:
    system = platform.system().lower()
    home = Path.home()

    directories: list[Path] = []

    if system == "windows":
        windows_dir = Path(os.environ.get("WINDIR", "C:\\Windows"))
        directories.append(windows_dir / "Fonts")
    elif system == "darwin":
        directories.extend(
            [
                Path("/System/Library/Fonts"),
                Path("/Library/Fonts"),
                home / "Library/Fonts",
            ]
        )
    else:
        directories.extend(
            [
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                home / ".fonts",
                home / ".local/share/fonts",
            ]
        )

    if _IS_WSL:
        directories.append(Path("/mnt/c/Windows/Fonts"))

    seen = set()
    ordered_dirs: list[Path] = []
    for directory in directories:
        resolved = directory.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered_dirs.append(resolved)
    return ordered_dirs


def _discover_system_fonts() -> list[tuple[str, Path]]:
    fonts: list[tuple[str, Path]] = []
    seen_paths: set[Path] = set()

    for directory in _candidate_font_dirs():
        if not directory.exists():
            continue
        try:
            candidates = sorted(directory.rglob("*"))
        except (OSError, PermissionError):
            continue
        for path in candidates:
            if path.suffix.lower() not in _FONT_EXTENSIONS or not path.is_file():
                continue
            resolved = path.resolve(strict=False)
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            fonts.append((path.stem, resolved))

    fonts.sort(key=lambda item: item[0].lower())
    return fonts


def _build_font_choice_map() -> OrderedDict[str, Path | None]:
    choices: OrderedDict[str, Path | None] = OrderedDict()
    choices[_DEFAULT_FONT_LABEL] = None

    for label, path in _discover_system_fonts():
        display_label = label
        suffix = 2
        while display_label in choices:
            display_label = f"{label} ({suffix})"
            suffix += 1
        choices[display_label] = path

    return choices


class PDFMergeApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("PDF Merge Utility")

        self._last_dialog_dir: Path | None = None

        self._position_options = [
            ("Top left", "top_left"),
            ("Top center", "top_center"),
            ("Top right", "top_right"),
            ("Bottom left", "bottom_left"),
            ("Bottom center", "bottom_center"),
            ("Bottom right", "bottom_right"),
        ]
        self._font_choice_map = _build_font_choice_map()
        self._enumeration_controls: list[tuple[tk.Widget, dict[str, str | int]]] = []

        self.template_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.scale_var = tk.DoubleVar(value=85.0)
        self.remove_cover_var = tk.BooleanVar(value=True)
        self.delete_template_var = tk.BooleanVar(value=False)
        self.append_only_var = tk.BooleanVar(value=False)
        self.enumerate_pages_var = tk.BooleanVar(value=False)
        default_position_label = self._position_options[-1][0]
        self.page_position_var = tk.StringVar(value=default_position_label)

        initial_font_label = next(iter(self._font_choice_map)) if self._font_choice_map else _DEFAULT_FONT_LABEL
        self.font_var = tk.StringVar(value=initial_font_label)
        self.font_size_var = tk.DoubleVar(value=11.0)
        self.margin_top_var = tk.DoubleVar(value=10.0)
        self.margin_bottom_var = tk.DoubleVar(value=10.0)
        self.margin_left_var = tk.DoubleVar(value=10.0)
        self.margin_right_var = tk.DoubleVar(value=10.0)

        self._build_layout()

        self.template_var.trace_add("write", self._update_delete_template_state)
        self.output_var.trace_add("write", self._update_delete_template_state)
        self.enumerate_pages_var.trace_add("write", self._update_numbering_controls)
        self._update_delete_template_state()
        self._update_numbering_controls()

    def _build_layout(self) -> None:
        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._add_file_selector(
            main_frame,
            row=0,
            label="Template PDF:",
            variable=self.template_var,
            command=self._select_template,
        )
        self._add_file_selector(
            main_frame,
            row=1,
            label="Input PDF:",
            variable=self.input_var,
            command=self._select_input,
        )
        self._add_file_selector(
            main_frame,
            row=2,
            label="Output PDF:",
            variable=self.output_var,
            command=self._select_output,
        )

        scale_frame = tk.Frame(main_frame)
        scale_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        tk.Label(scale_frame, text="Scale (% for both axes):").pack(anchor="w")
        scale_slider = tk.Scale(
            scale_frame,
            from_=10,
            to=100,
            orient=tk.HORIZONTAL,
            resolution=1,
            variable=self.scale_var,
        )
        scale_slider.pack(fill=tk.X)

        options_frame = tk.Frame(main_frame)
        options_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky="w")
        tk.Checkbutton(
            options_frame,
            text="Remove first page from input",
            variable=self.remove_cover_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            options_frame,
            text="Append input without modifications",
            variable=self.append_only_var,
        ).pack(anchor="w")
        self.delete_template_checkbutton = tk.Checkbutton(
            options_frame,
            text="Delete template after merge",
            variable=self.delete_template_var,
        )
        self.delete_template_checkbutton.pack(anchor="w")

        numbering_frame = tk.LabelFrame(main_frame, text="Page numbering", padx=10, pady=10)
        numbering_frame.grid(row=5, column=0, columnspan=3, pady=(15, 0), sticky="ew")
        numbering_frame.columnconfigure(1, weight=1)

        tk.Checkbutton(
            numbering_frame,
            text="Enumerate pages",
            variable=self.enumerate_pages_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        tk.Label(numbering_frame, text="Position:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        position_values = [label for label, _ in self._position_options]
        position_combo = ttk.Combobox(
            numbering_frame,
            textvariable=self.page_position_var,
            values=position_values,
            state="readonly",
        )
        position_combo.grid(row=1, column=1, sticky="ew", pady=(5, 0))
        self._enumeration_controls.append(
            (position_combo, {"enabled": "readonly", "disabled": "disabled"})
        )

        tk.Label(numbering_frame, text="Font:").grid(row=2, column=0, sticky="w", pady=(5, 0))
        font_values = list(self._font_choice_map.keys())
        font_combo = ttk.Combobox(
            numbering_frame,
            textvariable=self.font_var,
            values=font_values,
            state="readonly",
        )
        font_combo.grid(row=2, column=1, sticky="ew", pady=(5, 0))
        self._enumeration_controls.append(
            (font_combo, {"enabled": "readonly", "disabled": "disabled"})
        )

        tk.Label(numbering_frame, text="Size:").grid(row=3, column=0, sticky="w", pady=(5, 0))
        size_entry = tk.Entry(numbering_frame, textvariable=self.font_size_var, width=10)
        size_entry.grid(row=3, column=1, sticky="w", pady=(5, 0))
        self._enumeration_controls.append(
            (size_entry, {"enabled": tk.NORMAL, "disabled": tk.DISABLED})
        )

        margins_frame = tk.Frame(numbering_frame)
        margins_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        margins_frame.columnconfigure(1, weight=1)
        margins_frame.columnconfigure(3, weight=1)

        margin_specs = [
            ("Top (mm):", self.margin_top_var),
            ("Bottom (mm):", self.margin_bottom_var),
            ("Left (mm):", self.margin_left_var),
            ("Right (mm):", self.margin_right_var),
        ]

        for index, (label_text, variable) in enumerate(margin_specs):
            row = index // 2
            column = (index % 2) * 2
            tk.Label(margins_frame, text=label_text).grid(row=row, column=column, sticky="w")
            entry = tk.Entry(margins_frame, textvariable=variable, width=10)
            entry.grid(row=row, column=column + 1, sticky="w", padx=(5, 10))
            self._enumeration_controls.append(
                (entry, {"enabled": tk.NORMAL, "disabled": tk.DISABLED})
            )

        action_frame = tk.Frame(main_frame)
        action_frame.grid(row=6, column=0, columnspan=3, pady=(15, 0))
        tk.Button(action_frame, text="Merge", command=self._on_merge).pack()

        for i in range(3):
            main_frame.columnconfigure(i, weight=1)

    def _add_file_selector(
        self,
        parent: tk.Widget,
        *,
        row: int,
        label: str,
        variable: tk.StringVar,
        command,
    ) -> None:
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
        entry = tk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=(5, 5))
        tk.Button(parent, text="Browse", command=command).grid(row=row, column=2)

    def _update_numbering_controls(self, *_: object) -> None:
        enabled = self.enumerate_pages_var.get()
        state_key = "enabled" if enabled else "disabled"
        for widget, states in self._enumeration_controls:
            widget.config(state=states[state_key])

    def _build_page_numbering_config(self) -> PageNumberingConfig:
        selected_position = self.page_position_var.get()
        try:
            position_value = next(
                value for label, value in self._position_options if label == selected_position
            )
        except StopIteration as exc:
            raise ValueError("Select a valid page number position.") from exc

        try:
            font_size = float(self.font_size_var.get())
            margin_top = float(self.margin_top_var.get())
            margin_bottom = float(self.margin_bottom_var.get())
            margin_left = float(self.margin_left_var.get())
            margin_right = float(self.margin_right_var.get())
        except (tk.TclError, ValueError) as exc:
            raise ValueError("Page numbering size and margins must be numeric values.") from exc

        font_label = self.font_var.get()
        if font_label not in self._font_choice_map:
            raise ValueError("Select a valid font for page numbering.")

        font_path = self._font_choice_map[font_label]

        try:
            return PageNumberingConfig(
                position=position_value,
                font_path=font_path,
                font_size=font_size,
                margin_top_mm=margin_top,
                margin_bottom_mm=margin_bottom,
                margin_left_mm=margin_left,
                margin_right_mm=margin_right,
            )
        except Exception as exc:
            raise ValueError(str(exc)) from exc

    def _dialog_initialdir(self) -> str:
        if self._last_dialog_dir and self._last_dialog_dir.exists():
            return str(self._last_dialog_dir)
        return str(_initial_browse_dir())

    def _normalize_dialog_path(self, path: str) -> str:
        if _IS_WSL and len(path) >= 2 and path[1] == ":":
            try:
                completed = subprocess.run(
                    ["wslpath", "-a", path],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except Exception:
                return path
            converted = completed.stdout.strip()
            if converted:
                return converted
        return path

    def _cache_dialog_dir(self, path: str) -> None:
        directory = Path(path).expanduser()
        if not directory.is_dir():
            directory = directory.parent
        self._last_dialog_dir = directory

    def _select_template(self) -> None:
        path = filedialog.askopenfilename(
            title="Select template PDF",
            filetypes=[("PDF files", ("*.pdf", "*.PDF")), ("All files", "*.*")],
            initialdir=self._dialog_initialdir(),
        )
        if path:
            normalized = self._normalize_dialog_path(path)
            self._cache_dialog_dir(normalized)
            self.template_var.set(normalized)
            output_path = Path(normalized)
            self.output_var.set(str(output_path))

    def _select_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select input PDF",
            filetypes=[("PDF files", ("*.pdf", "*.PDF")), ("All files", "*.*")],
            initialdir=self._dialog_initialdir(),
        )
        if path:
            normalized = self._normalize_dialog_path(path)
            self._cache_dialog_dir(normalized)
            self.input_var.set(normalized)

    def _select_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Select output PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", ("*.pdf", "*.PDF")), ("All files", "*.*")],
            initialdir=self._dialog_initialdir(),
        )
        if path:
            normalized = self._normalize_dialog_path(path)
            self._cache_dialog_dir(normalized)
            self.output_var.set(normalized)

    def _on_merge(self) -> None:
        numbering_config: PageNumberingConfig | None = None
        if self.enumerate_pages_var.get():
            try:
                numbering_config = self._build_page_numbering_config()
            except ValueError as exc:
                messagebox.showerror("Invalid page numbering", str(exc))
                return

        try:
            config = MergeConfig(
                template_path=Path(self.template_var.get()).expanduser(),
                input_path=Path(self.input_var.get()).expanduser(),
                output_path=Path(self.output_var.get()).expanduser(),
                scale_percent=self.scale_var.get(),
                remove_first_page=self.remove_cover_var.get(),
                delete_template=self.delete_template_var.get(),
                append_only=self.append_only_var.get(),
                enumerate_pages=self.enumerate_pages_var.get(),
                page_numbering=numbering_config,
            )
        except Exception as exc:
            messagebox.showerror("Invalid configuration", str(exc))
            return

        if not config.template_path.exists():
            messagebox.showerror("Missing file", "Template file does not exist.")
            return
        if not config.input_path.exists():
            messagebox.showerror("Missing file", "Input file does not exist.")
            return

        try:
            merge_pdfs(config)
        except Exception as exc:  # pragma: no cover - GUI feedback
            messagebox.showerror("Merge failed", str(exc))
            return

        messagebox.showinfo("Success", f"PDF created at\n{config.output_path}")

    def _update_delete_template_state(self, *_) -> None:
        template_raw = self.template_var.get().strip()
        output_raw = self.output_var.get().strip()

        if template_raw and output_raw:
            template_path = Path(template_raw).expanduser()
            output_path = Path(output_raw).expanduser()
            try:
                same_file = template_path.resolve(strict=False) == output_path.resolve(strict=False)
            except Exception:
                same_file = str(template_path) == str(output_path)
        else:
            same_file = False

        if same_file:
            self.delete_template_var.set(True)
            self.delete_template_checkbutton.config(state=tk.DISABLED)
        else:
            self.delete_template_checkbutton.config(state=tk.NORMAL)


def launch_gui() -> None:
    root = tk.Tk()
    PDFMergeApp(root)
    root.mainloop()


__all__ = ["launch_gui", "PDFMergeApp"]
