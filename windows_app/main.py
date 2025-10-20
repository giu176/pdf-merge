"""Entry point for the Windows specific GUI wrapper."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from pdf_processing import MergeConfig, merge_pdfs


class WindowsMergeApp:
    """Simple Tkinter based GUI tailored for the Windows build."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF Merge Utility (Windows)")

        self.template_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.scale_var = tk.DoubleVar(value=85.0)
        self.remove_cover_var = tk.BooleanVar(value=True)
        self.delete_template_var = tk.BooleanVar(value=False)
        self.append_only_var = tk.BooleanVar(value=False)

        self._build_layout()

    def _build_layout(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        self._add_file_selector(
            frame,
            row=0,
            label="Template PDF",
            variable=self.template_var,
            command=self._select_template,
        )
        self._add_file_selector(
            frame,
            row=1,
            label="Input PDF",
            variable=self.input_var,
            command=self._select_input,
        )
        self._add_file_selector(
            frame,
            row=2,
            label="Output PDF",
            variable=self.output_var,
            command=self._select_output,
        )

        scale_frame = tk.Frame(frame)
        scale_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        tk.Label(scale_frame, text="Scale (%)").pack(anchor="w")
        tk.Spinbox(
            scale_frame,
            from_=10,
            to=100,
            increment=1,
            textvariable=self.scale_var,
            width=5,
        ).pack(anchor="w")

        options_frame = tk.Frame(frame)
        options_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky="w")
        tk.Checkbutton(
            options_frame,
            text="Remove first page from input",
            variable=self.remove_cover_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            options_frame,
            text="Append without scaling",
            variable=self.append_only_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            options_frame,
            text="Delete template after merge",
            variable=self.delete_template_var,
        ).pack(anchor="w")

        action_frame = tk.Frame(frame)
        action_frame.grid(row=5, column=0, columnspan=3, pady=(15, 0))
        tk.Button(action_frame, text="Merge", command=self._on_merge).pack()

        for column in range(3):
            frame.columnconfigure(column, weight=1)

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
        tk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=5)
        tk.Button(parent, text="Browse", command=command).grid(row=row, column=2)

    def _select_template(self) -> None:
        path = filedialog.askopenfilename(
            title="Select template PDF",
            filetypes=[("PDF files", ("*.pdf", "*.PDF")), ("All files", "*.*")],
        )
        if path:
            self.template_var.set(path)
            self.output_var.set(path)

    def _select_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select input PDF",
            filetypes=[("PDF files", ("*.pdf", "*.PDF")), ("All files", "*.*")],
        )
        if path:
            self.input_var.set(path)

    def _select_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Select output PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", ("*.pdf", "*.PDF")), ("All files", "*.*")],
        )
        if path:
            self.output_var.set(path)

    def _on_merge(self) -> None:
        try:
            config = MergeConfig(
                template_path=Path(self.template_var.get()).expanduser(),
                input_path=Path(self.input_var.get()).expanduser(),
                output_path=Path(self.output_var.get()).expanduser(),
                scale_percent=float(self.scale_var.get()),
                remove_first_page=self.remove_cover_var.get(),
                delete_template=self.delete_template_var.get(),
                append_only=self.append_only_var.get(),
            )
        except Exception as exc:  # pragma: no cover - UI feedback path
            messagebox.showerror("Invalid configuration", str(exc))
            return

        try:
            merge_pdfs(config)
        except Exception as exc:  # pragma: no cover - UI feedback path
            messagebox.showerror("Merge failed", str(exc))
            return

        messagebox.showinfo("Success", "PDFs merged successfully!")


def main() -> None:
    """Launch the Windows specific GUI."""

    root = tk.Tk()
    WindowsMergeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
