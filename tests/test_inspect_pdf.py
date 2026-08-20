from __future__ import annotations

import base64
from pathlib import Path
import tempfile
import unittest

from scripts.inspect_pdf import PdfDependencyError, _fitz_module, inspect_pdf, validate_pdf_privacy


class InspectPdfTests(unittest.TestCase):
    def _make_pdf(self, path: Path, *, metadata_title: str = "Synthetic report", attachment: bytes | None = None, image: bool = False) -> None:
        try:
            fitz = _fitz_module()
        except PdfDependencyError:
            self.skipTest("PyMuPDF unavailable")
        document = fitz.open()
        page = document.new_page(width=612, height=792)
        page.insert_text((72, 72), "Punchlist contributors synthetic report", fontsize=12, color=(0.06, 0.14, 0.24))
        page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(72, 80, 180, 100), "uri": "https://github.com/xenstalker02/punchlist"})
        if image:
            pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
            page.insert_image(fitz.Rect(200, 72, 220, 92), stream=pixel)
        document.set_metadata({"title": metadata_title, "author": "Punchlist contributors"})
        if attachment is not None:
            document.embfile_add("notes.txt", attachment, filename="notes.txt", ufilename="notes.txt", desc="Synthetic note")
        document.save(path)
        document.close()

    def test_inspection_includes_layout_links_metadata_attachments_and_image_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            self._make_pdf(path, attachment=b"Synthetic attachment")
            inspection = inspect_pdf(path)
        self.assertEqual([[612.0, 792.0]], inspection["page_dimensions"])
        self.assertEqual(1, len(inspection["page_layout_sha256"]))
        self.assertEqual(64, len(inspection["page_layout_sha256"][0]))
        self.assertGreater(inspection["page_text_block_count"][0], 0)
        self.assertIn(12.0, inspection["page_font_sizes"][0])
        self.assertTrue(inspection["page_text_colors"][0])
        self.assertEqual(0, inspection["image_count"])
        self.assertEqual([0], inspection["page_image_count"])
        self.assertEqual("https://github.com/xenstalker02/punchlist", inspection["link_annotations"][0]["target"])
        self.assertEqual("Synthetic report", inspection["metadata"]["title"])
        self.assertEqual(["notes.txt"], inspection["attachment_names"])

    def test_page_text_inventory_is_stable_when_extraction_order_changes(self) -> None:
        try:
            fitz = _fitz_module()
        except PdfDependencyError:
            self.skipTest("PyMuPDF unavailable")
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / "first.pdf", Path(directory) / "second.pdf"]
            for path, lines in zip(paths, (("Alpha ·", "Beta"), ("Beta", "Alpha")), strict=True):
                document = fitz.open()
                page = document.new_page(width=612, height=792)
                for index, line in enumerate(lines):
                    page.insert_text((72, 72 + index * 24), line, fontsize=12)
                document.save(path)
                document.close()
            first, second = (inspect_pdf(path) for path in paths)

        self.assertNotEqual(first["page_text_sha256"], second["page_text_sha256"])
        self.assertNotEqual(first["page_layout_sha256"], second["page_layout_sha256"])
        self.assertEqual(first["page_text_inventory_sha256"], second["page_text_inventory_sha256"])

    def test_privacy_inspection_scans_metadata_link_and_attachment_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            self._make_pdf(path, metadata_title=r"C:\Users\person\private", attachment=b"secret@example.com")
            errors = validate_pdf_privacy(path, "report.pdf")
        self.assertIn("report.pdf.metadata.title: absolute local path", errors)
        self.assertIn("report.pdf.attachment[0].content: email address", errors)

    def test_privacy_inspection_fails_closed_on_unregistered_pdf_images(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            self._make_pdf(path, image=True)
            inspection = inspect_pdf(path)
            errors = validate_pdf_privacy(path, "report.pdf")
        self.assertEqual(1, inspection["image_count"])
        self.assertIn("report.pdf.page[1]: PDF images are not registered for inspection", errors)


if __name__ == "__main__":
    unittest.main()
