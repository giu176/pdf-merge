"""Windows oriented GUI for the PDF merge executable."""

from __future__ import annotations

from pathlib import Path

from pdf_processing import (
    MergeConfig,
    PageNumberingOptions,
    list_available_fonts,
    merge_pdfs,
)

try:  # pragma: no cover - tkinter availability depends on the host OS
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    tk = None
    filedialog = None
    messagebox = None
    ttk = None


_PAGE_POSITION_CHOICES = [
    "Top left",
    "Top center",
    "Top right",
    "Bottom left",
    "Bottom center",
    "Bottom right",
]


class WindowsPDFMergeApp:
    """Tk/ttk based user interface tailored for Windows users."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF Merge for Windows")
        self.root.resizable(False, False)

        self.template_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.scale_var = tk.DoubleVar(value=85.0)
        self.scale_display_var = tk.StringVar(
            value=f"{int(self.scale_var.get())}%"
        )
        self.remove_first_page_var = tk.BooleanVar(value=True)
        self.delete_template_var = tk.BooleanVar(value=False)
        self.append_only_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Select the PDF files to merge")

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

        self._page_number_widgets: list[tk.Widget] = []

        self._build_layout()
        self._wire_events()

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        padding = (10, 6)

        container = ttk.Frame(self.root, padding=padding)
        container.grid(column=0, row=0, sticky="nsew")

        self._page_number_widgets.clear()

        self._add_file_row(
            container,
            row=0,
            label="Template PDF",
            variable=self.template_var,
            command=self._choose_template,
        )
        self._add_file_row(
            container,
            row=1,
            label="Input PDF",
            variable=self.input_var,
            command=self._choose_input,
        )
        self._add_file_row(
            container,
            row=2,
            label="Output PDF",
            variable=self.output_var,
            command=self._choose_output,
        )

        ttk.Label(container, text="Scale (%)").grid(column=0, row=3, sticky="w")
        ttk.Label(container, textvariable=self.scale_display_var).grid(
            column=1, row=3, sticky="w"
        )
        scale = ttk.Scale(
            container,
            variable=self.scale_var,
            from_=10,
            to=100,
            orient="horizontal",
            length=280,
        )
        scale.grid(column=0, row=4, columnspan=3, sticky="we")

        options = ttk.LabelFrame(container, text="Options")
        options.grid(column=0, row=5, columnspan=3, sticky="we", pady=(10, 0))

        ttk.Checkbutton(
            options,
            text="Remove first page from input",
            variable=self.remove_first_page_var,
        ).grid(column=0, row=0, sticky="w", padx=6, pady=3)
        ttk.Checkbutton(
            options,
            text="Append input without scaling",
            variable=self.append_only_var,
        ).grid(column=0, row=1, sticky="w", padx=6, pady=3)
        self.delete_template_check = ttk.Checkbutton(
            options,
            text="Delete template after merge",
            variable=self.delete_template_var,
        )
        self.delete_template_check.grid(column=0, row=2, sticky="w", padx=6, pady=3)

        numbering = ttk.LabelFrame(container, text="Page numbering")
        numbering.grid(column=0, row=6, columnspan=3, sticky="we", pady=(10, 0))

        ttk.Checkbutton(
            numbering,
            text="Add page numbers",
            variable=self.enumerate_pages_var,
            command=self._update_page_numbering_state,
        ).grid(column=0, row=0, columnspan=4, sticky="w", padx=6, pady=(3, 0))

        ttk.Label(numbering, text="Position:").grid(
            column=0, row=1, sticky="w", padx=6, pady=(6, 0)
        )
        position_combo = ttk.Combobox(
            numbering,
            textvariable=self.enumerate_position_var,
            values=_PAGE_POSITION_CHOICES,
            state="readonly",
            width=18,
        )
        position_combo.grid(column=1, row=1, sticky="w", padx=(0, 6), pady=(6, 0))
        self._page_number_widgets.append(position_combo)

        ttk.Label(numbering, text="Font:").grid(
            column=2, row=1, sticky="w", padx=(6, 0), pady=(6, 0)
        )
        font_combo = ttk.Combobox(
            numbering,
            textvariable=self.enumerate_font_var,
            values=list(self._font_options.keys()),
            state="readonly",
            width=18,
        )
        font_combo.grid(column=3, row=1, sticky="w", padx=(0, 6), pady=(6, 0))
        self._page_number_widgets.append(font_combo)

        ttk.Label(numbering, text="Size (pt):").grid(
            column=0, row=2, sticky="w", padx=6, pady=(6, 0)
        )
        size_entry = ttk.Entry(
            numbering, textvariable=self.enumerate_font_size_var, width=10
        )
        size_entry.grid(column=1, row=2, sticky="w", padx=(0, 6), pady=(6, 0))
        self._page_number_widgets.append(size_entry)

        ttk.Label(numbering, text="Margins (mm):").grid(
            column=0, row=3, sticky="w", padx=6, pady=(6, 0)
        )
        margin_frame = ttk.Frame(numbering)
        margin_frame.grid(column=0, row=4, columnspan=4, sticky="w", padx=6, pady=(3, 6))

        ttk.Label(margin_frame, text="Top:").grid(column=0, row=0, sticky="w")
        top_entry = ttk.Entry(
            margin_frame, textvariable=self.enumerate_margin_top_var, width=10
        )
        top_entry.grid(column=1, row=0, sticky="w", padx=(0, 12))
        self._page_number_widgets.append(top_entry)

        ttk.Label(margin_frame, text="Bottom:").grid(column=2, row=0, sticky="w")
        bottom_entry = ttk.Entry(
            margin_frame, textvariable=self.enumerate_margin_bottom_var, width=10
        )
        bottom_entry.grid(column=3, row=0, sticky="w", padx=(0, 12))
        self._page_number_widgets.append(bottom_entry)

        ttk.Label(margin_frame, text="Left:").grid(column=0, row=1, sticky="w", pady=(6, 0))
        left_entry = ttk.Entry(
            margin_frame, textvariable=self.enumerate_margin_left_var, width=10
        )
        left_entry.grid(column=1, row=1, sticky="w", padx=(0, 12), pady=(6, 0))
        self._page_number_widgets.append(left_entry)

        ttk.Label(margin_frame, text="Right:").grid(column=2, row=1, sticky="w", pady=(6, 0))
        right_entry = ttk.Entry(
            margin_frame, textvariable=self.enumerate_margin_right_var, width=10
        )
        right_entry.grid(column=3, row=1, sticky="w", pady=(6, 0))
        self._page_number_widgets.append(right_entry)

        action = ttk.Frame(container)
        action.grid(column=0, row=7, columnspan=3, sticky="we", pady=(12, 0))
        ttk.Button(action, text="Merge PDFs", command=self._on_merge).grid(
            column=0, row=0, padx=5
        )

        status = ttk.Label(container, textvariable=self.status_var, foreground="#555555")
        status.grid(column=0, row=8, columnspan=3, sticky="we", pady=(12, 0))

        for column in range(3):
            container.columnconfigure(column, weight=1)

        numbering.columnconfigure(1, weight=1)
        numbering.columnconfigure(3, weight=1)

        self._update_page_numbering_state()

    def _add_file_row(
        self,
        parent: ttk.Frame,
        *,
        row: int,
        label: str,
        variable: tk.StringVar,
        command,
    ) -> None:
        ttk.Label(parent, text=label).grid(column=0, row=row, sticky="w")
        entry = ttk.Entry(parent, textvariable=variable, width=50)
        entry.grid(column=1, row=row, sticky="we", padx=(6, 6))
        ttk.Button(parent, text="Browse…", command=command).grid(column=2, row=row)

    def _wire_events(self) -> None:
        self.template_var.trace_add("write", self._update_delete_template_state)
        self.output_var.trace_add("write", self._update_delete_template_state)
        self.scale_var.trace_add("write", self._on_scale_changed)

    def _load_font_options(self) -> dict[str, Path | None]:
        fonts = list_available_fonts()
        converted: dict[str, Path | None] = {}
        for name, path in fonts.items():
            if isinstance(path, str):
                converted[name] = Path(path)
            else:
                converted[name] = path

        if "Helvetica" not in converted:
            converted["Helvetica"] = None

        return converted

    # ------------------------------------------------------------------
    # Dialog helpers
    # ------------------------------------------------------------------
    def _choose_template(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select template PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if file_path:
            path = Path(file_path).expanduser()
            self.template_var.set(str(path))
            if not self.output_var.get().strip():
                self.output_var.set(str(path))
            self.status_var.set("Template selected. Choose the input PDF.")

    def _choose_input(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select input PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if file_path:
            path = Path(file_path).expanduser()
            self.input_var.set(str(path))
            self.status_var.set("Input selected. Ready to merge once output is set.")

    def _choose_output(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Select output PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if file_path:
            path = Path(file_path).expanduser()
            self.output_var.set(str(path))
            self.status_var.set("Output file chosen. Click Merge when ready.")

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------
    def _on_scale_changed(self, *_) -> None:
        value = int(round(float(self.scale_var.get())))
        self.scale_display_var.set(f"{value}%")

    def _update_page_numbering_state(self, *_) -> None:
        enabled = self.enumerate_pages_var.get()
        for widget in self._page_number_widgets:
            if isinstance(widget, ttk.Combobox):
                widget.configure(state="readonly" if enabled else "disabled")
            else:
                widget.configure(state="normal" if enabled else "disabled")

    def _update_delete_template_state(self, *_) -> None:
        template = self.template_var.get().strip()
        output = self.output_var.get().strip()

        same = False
        if template and output:
            try:
                same = Path(template).expanduser().resolve(strict=False) == Path(output).expanduser().resolve(strict=False)
            except OSError:
                same = Path(template).expanduser() == Path(output).expanduser()

        if same:
            self.delete_template_var.set(True)
            self.delete_template_check.state(["disabled"])
        else:
            self.delete_template_check.state(["!disabled"])

    def _validate(self) -> MergeConfig:
        enumerate_pages = self.enumerate_pages_var.get()
        page_numbering: PageNumberingOptions | None = None
        if enumerate_pages:
            page_numbering = self._collect_page_numbering_options()

        try:
            config = MergeConfig(
                template_path=Path(self.template_var.get()).expanduser(),
                input_path=Path(self.input_var.get()).expanduser(),
                output_path=Path(self.output_var.get()).expanduser(),
                scale_percent=float(self.scale_var.get()),
                remove_first_page=self.remove_first_page_var.get(),
                delete_template=self.delete_template_var.get(),
                append_only=self.append_only_var.get(),
                enumerate_pages=enumerate_pages,
                page_numbering=page_numbering,
            )
        except Exception as exc:  # pragma: no cover - GUI feedback
            raise ValueError(str(exc)) from exc

        if not config.template_path.exists():
            raise ValueError("Template file does not exist")
        if not config.input_path.exists():
            raise ValueError("Input file does not exist")
        return config

    def _collect_page_numbering_options(self) -> PageNumberingOptions:
        try:
            font_size = float(self.enumerate_font_size_var.get())
            margin_top = float(self.enumerate_margin_top_var.get())
            margin_bottom = float(self.enumerate_margin_bottom_var.get())
            margin_left = float(self.enumerate_margin_left_var.get())
            margin_right = float(self.enumerate_margin_right_var.get())
        except tk.TclError as exc:
            raise ValueError("Page numbering values must be numeric") from exc

        font_choice = self.enumerate_font_var.get()
        if font_choice not in self._font_options:
            raise ValueError("Selected font is not available")
        font_path = self._font_options.get(font_choice)

        return PageNumberingOptions(
            position=self.enumerate_position_var.get(),
            font_name=font_choice,
            font_file=font_path,
            font_size=font_size,
            margin_top_mm=margin_top,
            margin_bottom_mm=margin_bottom,
            margin_left_mm=margin_left,
            margin_right_mm=margin_right,
        )

    def _on_merge(self) -> None:
        try:
            config = self._validate()
        except ValueError as exc:  # pragma: no cover - GUI feedback
            messagebox.showerror("Invalid configuration", str(exc))
            return

        self.status_var.set("Merging documents…")
        self.root.update_idletasks()

        try:
            merge_pdfs(config)
        except Exception as exc:  # pragma: no cover - GUI feedback
            messagebox.showerror("Merge failed", str(exc))
            self.status_var.set("Merge failed. See the error message for details.")
            return

        messagebox.showinfo("Success", f"PDF created at\n{config.output_path}")
        self.status_var.set("Merge completed successfully.")


def launch_gui() -> None:
    if tk is None:
        raise RuntimeError(
            "Tkinter is required for the graphical interface but is not available"
        )

    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:  # pragma: no cover - depends on platform themes
        pass
    WindowsPDFMergeApp(root)
    root.mainloop()


__all__ = ["WindowsPDFMergeApp", "launch_gui"]
