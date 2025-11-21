import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz

from pdf_processing import (
    MergeConfig,
    PageNumberingOptions,
    RoipamOptions,
    merge_pdfs,
    process_roipam_folder,
)


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

    def test_process_roipam_merges_into_subdirectory(self) -> None:
        base_dir = Path(self._temp_dir.name)
        cover_path = base_dir / "Project - Allegato A - cover.pdf"
        annex_path = base_dir / "Allegato A.pdf"

        self._create_pdf(cover_path, ["Cover A"])
        self._create_pdf(annex_path, ["Annex A"])

        options = RoipamOptions(
            scale_percent=100.0,
            remove_first_page=False,
            append_only=True,
            enumerate_pages=False,
        )

        results = process_roipam_folder(base_dir, options)

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertTrue(result.success)

        merged_path = base_dir / "MERGED" / cover_path.name
        self.assertEqual(result.output_path, merged_path)
        self.assertTrue(merged_path.exists())

        # Ensure originals remain untouched
        self.assertTrue(cover_path.exists())
        self.assertTrue(annex_path.exists())

        merged_doc = fitz.open(str(merged_path))
        try:
            self.assertEqual(len(merged_doc), 2)
            texts = "".join(page.get_text() for page in merged_doc)
            self.assertIn("Cover A", texts)
            self.assertIn("Annex A", texts)
        finally:
            merged_doc.close()

    def test_process_roipam_duplicates_page_for_allegato_d(self) -> None:
        base_dir = Path(self._temp_dir.name)
        cover_path = base_dir / "Cover Allegato D.pdf"
        annex_path = base_dir / "Allegato D.pdf"

        self._create_pdf(cover_path, ["Cover D"])
        self._create_pdf(annex_path, ["First", "Second"])

        options = RoipamOptions(
            scale_percent=100.0,
            remove_first_page=False,
            append_only=True,
            enumerate_pages=False,
        )

        results = process_roipam_folder(base_dir, options)

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertTrue(result.success)

        merged_doc = fitz.open(str(result.output_path))
        try:
            # Cover + duplicated first page + original pages
            self.assertEqual(len(merged_doc), 4)
            merged_text = [merged_doc[i].get_text() for i in range(len(merged_doc))]
            self.assertEqual(merged_text.count(merged_text[1]), 2)
            self.assertIn("Second", " ".join(merged_text))
        finally:
            merged_doc.close()

        # The original annex should remain unchanged
        original_annex = fitz.open(str(annex_path))
        try:
            self.assertEqual(len(original_annex), 2)
        finally:
            original_annex.close()

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

    def test_process_roipam_removes_first_page_for_allegato_e(self) -> None:
        base_dir = Path(self._temp_dir.name)
        cover_path = base_dir / "Cover Allegato E.pdf"
        annex_path = base_dir / "Allegato E.pdf"

        self._create_pdf(cover_path, ["Cover E"])
        self._create_pdf(annex_path, ["Front E", "Content E"])

        options = RoipamOptions(
            scale_percent=100.0,
            remove_first_page=False,
            append_only=True,
            enumerate_pages=False,
        )

        results = process_roipam_folder(base_dir, options)

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertTrue(result.success)

        merged_doc = fitz.open(str(result.output_path))
        try:
            self.assertEqual(len(merged_doc), 1)
            merged_text = merged_doc[0].get_text()
            self.assertNotIn("Front E", merged_text)
            self.assertIn("Content E", merged_text)
        finally:
            merged_doc.close()


if __name__ == "__main__":
    unittest.main()
