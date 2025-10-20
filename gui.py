"""Tkinter based GUI for the PDF merge tool."""

from __future__ import annotations

import os
import platform
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from pdf_processing import MergeConfig, merge_pdfs


_IS_WSL = "microsoft" in platform.release().lower() or bool(os.environ.get("WSL_DISTRO_NAME"))


def _initial_browse_dir() -> Path:
    """Return a sensible starting directory for file dialogs."""
    if _IS_WSL:
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

        action_frame = tk.Frame(main_frame)
        action_frame.grid(row=5, column=0, columnspan=3, pady=(15, 0))
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
        try:
            config = MergeConfig(
                template_path=Path(self.template_var.get()).expanduser(),
                input_path=Path(self.input_var.get()).expanduser(),
                output_path=Path(self.output_var.get()).expanduser(),
                scale_percent=self.scale_var.get(),
                remove_first_page=self.remove_cover_var.get(),
                delete_template=self.delete_template_var.get(),
                append_only=self.append_only_var.get(),
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
