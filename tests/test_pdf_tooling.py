from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_ROOT = REPO_ROOT / "examples" / "synthetic"
PDF_HELPER = REPO_ROOT / "scripts" / "print_report.mjs"
PDF_INSPECTOR = REPO_ROOT / "scripts" / "inspect_pdf.py"
INPUT_HTML = SYNTHETIC_ROOT / "report.html"
OUTPUT_PDF = SYNTHETIC_ROOT / "report.pdf"


class PdfToolingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.paths: list[Path] = []
        self.input_before = INPUT_HTML.read_bytes()

    def tearDown(self) -> None:
        for path in reversed(self.paths):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        self.assertEqual(self.input_before, INPUT_HTML.read_bytes())

    def test_inspector_reports_meaningful_pages_layout_and_author_link(self) -> None:
        result = self._inspect(OUTPUT_PDF)
        self.assertEqual(0, result.returncode, result.stderr)
        inspection = json.loads(result.stdout)
        self.assertGreaterEqual(inspection["page_count"], 4)
        self.assertEqual(inspection["page_count"], len(inspection["page_text_characters"]))
        self.assertTrue(all(characters >= 200 for characters in inspection["page_text_characters"]))
        self.assertEqual(inspection["page_count"], len(inspection["page_text_sha256"]))
        self.assertTrue(all(len(digest) == 64 for digest in inspection["page_text_sha256"]))
        self.assertEqual(inspection["page_count"], len(inspection["page_text_inventory_sha256"]))
        self.assertTrue(all(len(digest) == 64 for digest in inspection["page_text_inventory_sha256"]))
        self.assertEqual(inspection["page_count"], len(inspection["page_layout_sha256"]))
        self.assertTrue(all(len(digest) == 64 for digest in inspection["page_layout_sha256"]))
        self.assertEqual([[612.0, 792.0]] * inspection["page_count"], inspection["page_dimensions"])
        self.assertEqual([0] * inspection["page_count"], inspection["page_image_count"])
        self.assertEqual(0, inspection["image_count"])
        self.assertTrue(
            any(link["target"].rstrip("/") == "https://github.com/xenstalker02/punchlist" for link in inspection["link_annotations"])
        )

    def test_inspector_error_is_location_safe(self) -> None:
        result = self._inspect(REPO_ROOT / "private-candidate.pdf")
        self.assertEqual(1, result.returncode)
        self.assertEqual("pdf: could not inspect\n", result.stderr)
        self.assertNotIn("private-candidate", result.stderr)

    def test_helper_rejects_non_pdf_output_without_creating_it(self) -> None:
        output = SYNTHETIC_ROOT / ".task5-invalid-suffix.txt"
        self.paths.append(output)
        result = self._export(output)
        self.assertEqual(1, result.returncode)
        self.assertEqual("output: must end in .pdf\n", result.stderr)
        self.assertFalse(output.exists())

    def test_helper_rejects_existing_output_symlink_when_supported(self) -> None:
        output = SYNTHETIC_ROOT / ".task5-output-link.pdf"
        destination = SYNTHETIC_ROOT / ".task5-link-destination.pdf"
        destination.write_bytes(b"unchanged")
        self.paths.extend((output, destination))
        try:
            os.symlink(destination.name, output)
        except (NotImplementedError, OSError) as error:
            self.skipTest(f"symlinks unavailable: {error.__class__.__name__}")
        result = self._export(output)
        self.assertEqual(1, result.returncode)
        self.assertEqual("output: existing symlink is not allowed\n", result.stderr)
        self.assertEqual(b"unchanged", destination.read_bytes())

    def test_helper_failed_output_leaves_no_temporary_pdf(self) -> None:
        output = SYNTHETIC_ROOT / ".task5-blocked.pdf"
        output.mkdir()
        self.paths.append(output)
        result = self._export(output)
        self.assertEqual(1, result.returncode)
        self.assertEqual("pdf: could not export report\n", result.stderr)
        self.assertTrue(output.is_dir())
        self.assertEqual([], list(SYNTHETIC_ROOT.glob(".task5-blocked.pdf.*.tmp")))

    @staticmethod
    def _export(output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["node", str(PDF_HELPER), "--input", str(INPUT_HTML), "--output", str(output)], cwd=REPO_ROOT, text=True, capture_output=True, check=False)

    @staticmethod
    def _inspect(input_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(PDF_INSPECTOR), "--input", str(input_path)], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
