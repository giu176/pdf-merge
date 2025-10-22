import pytest

from pdf_processing import PageNumberingOptions
from windows_app.gui import WindowsPDFMergeApp


def test_windows_gui_passes_page_numbering_to_merge(monkeypatch, tmp_path):
    tk = pytest.importorskip("tkinter")

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display is not available")
    root.withdraw()
    try:
        app = WindowsPDFMergeApp(root)

        template_path = tmp_path / "template.pdf"
        input_path = tmp_path / "input.pdf"
        output_path = tmp_path / "output.pdf"
        template_path.write_bytes(b"%PDF-1.4\n")
        input_path.write_bytes(b"%PDF-1.4\n")

        app.template_var.set(str(template_path))
        app.input_var.set(str(input_path))
        app.output_var.set(str(output_path))

        app.enumerate_pages_var.set(True)
        app.enumerate_position_var.set("Bottom left")
        available_fonts = list(app._font_options.keys())
        if available_fonts:
            app.enumerate_font_var.set(available_fonts[0])
        app.enumerate_font_size_var.set(13.5)
        app.enumerate_margin_top_var.set(5.0)
        app.enumerate_margin_bottom_var.set(6.0)
        app.enumerate_margin_left_var.set(7.0)
        app.enumerate_margin_right_var.set(8.0)

        captured_config = {}

        def fake_merge(config):
            captured_config["config"] = config

        monkeypatch.setattr("windows_app.gui.merge_pdfs", fake_merge)
        monkeypatch.setattr("windows_app.gui.messagebox.showinfo", lambda *args, **kwargs: None)
        monkeypatch.setattr("windows_app.gui.messagebox.showerror", lambda *args, **kwargs: None)

        app._on_merge()
    finally:
        root.destroy()

    config = captured_config["config"]
    assert config.enumerate_pages is True
    assert isinstance(config.page_numbering, PageNumberingOptions)
    assert config.page_numbering.position == "bottom_left"
    assert config.page_numbering.margin_top_mm == pytest.approx(5.0)
    assert config.page_numbering.margin_right_mm == pytest.approx(8.0)
