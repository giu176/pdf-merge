"""Tkinter based GUI for the PDF merge tool."""

from __future__ import annotations

import os
import platform
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from pdf_processing import (
    MergeConfig,
    PageNumberingOptions,
    list_available_fonts,
    merge_pdfs,
)


_IS_WSL = "microsoft" in platform.release().lower() or bool(os.environ.get("WSL_DISTRO_NAME"))


_PAGE_POSITION_CHOICES = [
    "Top left",
    "Top center",
    "Top right",
    "Bottom left",
    "Bottom center",
    "Bottom right",
]


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


class PDFMergeApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("PDF Merge Utility")

        self._last_dialog_dir: Path | None = None

        self.template_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.scale_var = tk.DoubleVar(value=85.0)
        self.remove_cover_var = tk.BooleanVar(value=True)
        self.delete_template_var = tk.BooleanVar(value=False)
        self.append_only_var = tk.BooleanVar(value=False)

        self.enumerate_pages_var = tk.BooleanVar(value=False)
        self.enumerate_position_var = tk.StringVar(value=_PAGE_POSITION_CHOICES[-1])
        self.enumerate_font_size_var = tk.DoubleVar(value=11.0)
        self.enumerate_margin_top_var = tk.DoubleVar(value=10.0)
        self.enumerate_margin_bottom_var = tk.DoubleVar(value=10.0)
        self.enumerate_margin_left_var = tk.DoubleVar(value=10.0)
        self.enumerate_margin_right_var = tk.DoubleVar(value=10.0)

        self._font_options = self._load_font_options()
        default_font = "Helvetica"
        if default_font not in self._font_options and self._font_options:
            default_font = next(iter(self._font_options))
        self.enumerate_font_var = tk.StringVar(value=default_font)

        self._enumerate_widgets: list[tk.Widget] = []

        self._build_layout()

        self.template_var.trace_add("write", self._update_delete_template_state)
        self.output_var.trace_add("write", self._update_delete_template_state)
        self._update_delete_template_state()

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
        numbering_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="ew")

        tk.Checkbutton(
            numbering_frame,
            text="Add page numbers",
            variable=self.enumerate_pages_var,
            command=self._update_enumerate_controls,
        ).grid(row=0, column=0, columnspan=4, sticky="w")

        tk.Label(numbering_frame, text="Position:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        position_menu = tk.OptionMenu(
            numbering_frame,
            self.enumerate_position_var,
            *_PAGE_POSITION_CHOICES,
        )
        position_menu.grid(row=1, column=1, sticky="w", pady=(5, 0))
        self._enumerate_widgets.append(position_menu)

        tk.Label(numbering_frame, text="Font:").grid(row=1, column=2, sticky="w", pady=(5, 0), padx=(10, 0))
        font_menu = tk.OptionMenu(
            numbering_frame,
            self.enumerate_font_var,
            *self._font_options.keys(),
        )
        font_menu.grid(row=1, column=3, sticky="w", pady=(5, 0))
        self._enumerate_widgets.append(font_menu)

        tk.Label(numbering_frame, text="Size (pt):").grid(row=2, column=0, sticky="w", pady=(5, 0))
        size_entry = tk.Entry(numbering_frame, textvariable=self.enumerate_font_size_var, width=8)
        size_entry.grid(row=2, column=1, sticky="w", pady=(5, 0))
        self._enumerate_widgets.append(size_entry)

        tk.Label(numbering_frame, text="Margins (mm):").grid(row=3, column=0, sticky="w", pady=(5, 0))
        margin_frame = tk.Frame(numbering_frame)
        margin_frame.grid(row=4, column=0, columnspan=4, sticky="w")

        tk.Label(margin_frame, text="Top:").grid(row=0, column=0, sticky="w")
        top_entry = tk.Entry(margin_frame, textvariable=self.enumerate_margin_top_var, width=8)
        top_entry.grid(row=0, column=1, sticky="w", padx=(0, 10))
        self._enumerate_widgets.append(top_entry)

        tk.Label(margin_frame, text="Bottom:").grid(row=0, column=2, sticky="w")
        bottom_entry = tk.Entry(margin_frame, textvariable=self.enumerate_margin_bottom_var, width=8)
        bottom_entry.grid(row=0, column=3, sticky="w", padx=(0, 10))
        self._enumerate_widgets.append(bottom_entry)

        tk.Label(margin_frame, text="Left:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        left_entry = tk.Entry(margin_frame, textvariable=self.enumerate_margin_left_var, width=8)
        left_entry.grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(5, 0))
        self._enumerate_widgets.append(left_entry)

        tk.Label(margin_frame, text="Right:").grid(row=1, column=2, sticky="w", pady=(5, 0))
        right_entry = tk.Entry(margin_frame, textvariable=self.enumerate_margin_right_var, width=8)
        right_entry.grid(row=1, column=3, sticky="w", padx=(0, 10), pady=(5, 0))
        self._enumerate_widgets.append(right_entry)

        action_frame = tk.Frame(main_frame)
        action_frame.grid(row=6, column=0, columnspan=3, pady=(15, 0))
        tk.Button(action_frame, text="Merge", command=self._on_merge).pack()

        for i in range(3):
            main_frame.columnconfigure(i, weight=1)

        self._update_enumerate_controls()

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

    def _load_font_options(self) -> dict[str, Path | None]:
        fonts = list_available_fonts()
        converted: dict[str, Path | None] = {}
        for name, path in fonts.items():
            if isinstance(path, str):
                converted[name] = Path(path)
            else:
                converted[name] = path

        if not converted:
            converted["Helvetica"] = None

        return converted

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

    def _collect_page_numbering_options(self) -> PageNumberingOptions:
        try:
            font_size = self.enumerate_font_size_var.get()
            top = self.enumerate_margin_top_var.get()
            bottom = self.enumerate_margin_bottom_var.get()
            left = self.enumerate_margin_left_var.get()
            right = self.enumerate_margin_right_var.get()
        except tk.TclError as exc:
            raise ValueError("Page numbering values must be numeric") from exc

        font_choice = self.enumerate_font_var.get()
        font_path = self._font_options.get(font_choice)

        return PageNumberingOptions(
            position=self.enumerate_position_var.get(),
            font_name=font_choice,
            font_file=font_path,
            font_size=font_size,
            margin_top_mm=top,
            margin_bottom_mm=bottom,
            margin_left_mm=left,
            margin_right_mm=right,
        )

    def _on_merge(self) -> None:
        page_numbering = None
        if self.enumerate_pages_var.get():
            try:
                page_numbering = self._collect_page_numbering_options()
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
                page_numbering=page_numbering,
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

    def _update_enumerate_controls(self, *_: object) -> None:
        state = tk.NORMAL if self.enumerate_pages_var.get() else tk.DISABLED
        for widget in self._enumerate_widgets:
            widget.config(state=state)
            if isinstance(widget, tk.OptionMenu):
                menu = widget["menu"]
                end_index = menu.index("end")
                if end_index is not None:
                    for idx in range(end_index + 1):
                        menu.entryconfig(idx, state="normal" if state == tk.NORMAL else "disabled")


def launch_gui() -> None:
    root = tk.Tk()
    PDFMergeApp(root)
    root.mainloop()


__all__ = ["launch_gui", "PDFMergeApp"]
