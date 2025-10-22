import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz

from pdf_processing import MergeConfig, PageNumberingConfig, merge_pdfs


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

    def test_merge_adds_page_numbers_when_requested(self) -> None:
        template_path = self.base_path / "template.pdf"
        input_path = self.base_path / "input.pdf"
        output_path = self.base_path / "output.pdf"

        self._create_pdf(template_path, ["Template background"])
        self._create_pdf(input_path, ["Alpha", "Bravo"])

        numbering = PageNumberingConfig(
            position="bottom_right",
            font_path=None,
            font_size=12,
            margin_top_mm=10,
            margin_bottom_mm=10,
            margin_left_mm=10,
            margin_right_mm=10,
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
            for index, page in enumerate(result_doc, start=1):
                page_text = page.get_text()
                self.assertIn(str(index), page_text)
        finally:
            result_doc.close()

        temp_enumerated = output_path.with_name(
            f"{output_path.stem}_temp_enumerating{output_path.suffix}"
        )
        self.assertFalse(temp_enumerated.exists())


if __name__ == "__main__":
    unittest.main()
