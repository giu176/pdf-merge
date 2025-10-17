"""Tkinter based GUI for the PDF merge tool."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from pdf_processing import MergeConfig, merge_pdfs


class PDFMergeApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("PDF Merge Utility")

        self.template_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.scale_var = tk.DoubleVar(value=85.0)
        self.remove_cover_var = tk.BooleanVar(value=True)
        self.delete_template_var = tk.BooleanVar(value=False)

        self._build_layout()

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
            text="Delete template after merge",
            variable=self.delete_template_var,
        ).pack(anchor="w")

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

    def _select_template(self) -> None:
        path = filedialog.askopenfilename(
            title="Select template PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self.template_var.set(path)
            output_path = Path(path)
            self.output_var.set(str(output_path))

    def _select_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select input PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self.input_var.set(path)

    def _select_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Select output PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self.output_var.set(path)

    def _on_merge(self) -> None:
        try:
            config = MergeConfig(
                template_path=Path(self.template_var.get()).expanduser(),
                input_path=Path(self.input_var.get()).expanduser(),
                output_path=Path(self.output_var.get()).expanduser(),
                scale_percent=self.scale_var.get(),
                remove_first_page=self.remove_cover_var.get(),
                delete_template=self.delete_template_var.get(),
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


def launch_gui() -> None:
    root = tk.Tk()
    PDFMergeApp(root)
    root.mainloop()


__all__ = ["launch_gui", "PDFMergeApp"]

