import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz

from pdf_processing import MergeConfig, PageNumberingOptions, merge_pdfs


class MergeSinglePageTemplateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.base_path = Path(self._temp_dir.name)

    def _create_pdf(self, path: Path, contents: list[str]) -> None:
        doc = fitz.open()
        try:
            for text in contents:
                page = doc.new_page()
                page.insert_text((72, 72), text)
            doc.save(str(path))
        finally:
            doc.close()

    def test_merge_drops_leading_template_page_for_single_page_template(self) -> None:
        template_path = self.base_path / "template.pdf"
        input_path = self.base_path / "input.pdf"
        output_path = self.base_path / "output.pdf"

        self._create_pdf(template_path, ["Template background"])
        self._create_pdf(input_path, ["Page 1", "Page 2"])

        config = MergeConfig(
            template_path=template_path,
            input_path=input_path,
            output_path=output_path,
            remove_first_page=False,
            append_only=False,
        )

        merge_pdfs(config)

        result_doc = fitz.open(str(output_path))
        try:
            self.assertEqual(len(result_doc), 2)
            first_page_text = result_doc[0].get_text()
            self.assertIn("Page 1", first_page_text)
        finally:
            result_doc.close()

    def test_merge_can_add_page_numbers(self) -> None:
        template_path = self.base_path / "template.pdf"
        input_path = self.base_path / "input.pdf"
        output_path = self.base_path / "output.pdf"

        self._create_pdf(template_path, ["Template background"])
        self._create_pdf(input_path, ["Alpha", "Beta"])

        numbering = PageNumberingOptions(
            position="Bottom right",
            font_name="Helvetica",
            font_size=12.0,
            margin_top_mm=10.0,
            margin_bottom_mm=10.0,
            margin_left_mm=10.0,
            margin_right_mm=10.0,
        )

        config = MergeConfig(
            template_path=template_path,
            input_path=input_path,
            output_path=output_path,
            remove_first_page=False,
            append_only=False,
            enumerate_pages=True,
            page_numbering=numbering,
        )

        merge_pdfs(config)

        result_doc = fitz.open(str(output_path))
        try:
            self.assertEqual(len(result_doc), 2)
            first_page_text = result_doc[0].get_text()
            second_page_text = result_doc[1].get_text()
            self.assertIn("Alpha", first_page_text)
            self.assertIn("Beta", second_page_text)
            self.assertIn("1", first_page_text)
            self.assertIn("2", second_page_text)
        finally:
            result_doc.close()


if __name__ == "__main__":
    unittest.main()
