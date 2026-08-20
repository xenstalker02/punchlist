from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.inspect_pdf import inspect_pdf


REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / "scripts" / "print_report.mjs"
CANONICAL_INPUT = REPO_ROOT / "examples" / "synthetic" / "report.html"
SYNTHETIC_AUDIT = REPO_ROOT / "examples" / "synthetic" / "audit.json"
SYNTHETIC_REPORT = REPO_ROOT / "examples" / "synthetic" / "report.json"
ACCENT_THEME = REPO_ROOT / "themes" / "platform-accent.example.json"
TEMP_ROOT = REPO_ROOT / "tmp"
TEMP_ROOT.mkdir(exist_ok=True)


class PrintReportBoundaryTests(unittest.TestCase):
    def test_rejects_any_noncanonical_html_even_inside_synthetic_directory(self) -> None:
        alternate = CANONICAL_INPUT.parent / ".alternate-report.html"
        alternate.write_text(CANONICAL_INPUT.read_text(encoding="utf-8"), encoding="utf-8")
        try:
            with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
                result = self._run(alternate, Path(directory) / "report.pdf")
            self.assertEqual(1, result.returncode)
            self.assertEqual("input: must be canonical synthetic HTML\n", result.stderr)
        finally:
            alternate.unlink(missing_ok=True)

    def test_rejects_symlink_alias_to_canonical_input(self) -> None:
        alias = CANONICAL_INPUT.parent / ".report-alias.html"
        try:
            os.symlink(CANONICAL_INPUT.name, alias)
        except OSError as error:
            self.skipTest(f"symlinks unsupported: {error.__class__.__name__}")
        try:
            with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
                result = self._run(alias, Path(directory) / "report.pdf")
            self.assertEqual(1, result.returncode)
            self.assertEqual("input: must be canonical synthetic HTML\n", result.stderr)
        finally:
            alias.unlink(missing_ok=True)

    def test_parser_rejects_mixed_partial_duplicate_and_unknown_modes_without_echoing_values(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            output = Path(directory) / "report.pdf"
            private_value = r"C:\Users\person\private-audit.json"
            cases = (
                ["--input", str(CANONICAL_INPUT), "--audit", private_value, "--report", str(SYNTHETIC_REPORT), "--output", str(output)],
                ["--audit", private_value, "--output", str(output)],
                ["--theme", str(ACCENT_THEME), "--output", str(output)],
                ["--input", str(CANONICAL_INPUT), "--input", str(CANONICAL_INPUT), "--output", str(output)],
                ["--unknown", private_value, "--output", str(output)],
            )
            for arguments in cases:
                result = self._arguments(arguments)
                self.assertEqual(1, result.returncode)
                self.assertEqual("arguments: invalid command\n", result.stderr)
                self.assertNotIn(private_value, result.stderr)
                self.assertFalse(output.exists())

    def test_data_mode_renders_validated_inputs_to_an_actual_pdf_and_cleans_temporary_html(self) -> None:
        TEMP_ROOT.mkdir(exist_ok=True)
        before = {path.name for path in TEMP_ROOT.glob("punchlist-pdf-*")}
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            output = Path(directory) / "report.pdf"
            result = self._arguments(
                [
                    "--audit", str(SYNTHETIC_AUDIT),
                    "--report", str(SYNTHETIC_REPORT),
                    "--theme", str(ACCENT_THEME),
                    "--output", str(output),
                ]
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(output.read_bytes().startswith(b"%PDF"))
            inspection = inspect_pdf(output)
            self.assertGreaterEqual(inspection["page_count"], 4)
            self.assertEqual(
                ["https://sample-platform.example/"],
                [link["target"] for link in inspection["link_annotations"]],
            )
        after = {path.name for path in TEMP_ROOT.glob("punchlist-pdf-*")}
        self.assertEqual(before, after)

    def test_data_mode_suppresses_renderer_paths_and_values_on_failure_and_cleans_up(self) -> None:
        TEMP_ROOT.mkdir(exist_ok=True)
        before = {path.name for path in TEMP_ROOT.glob("punchlist-pdf-*")}
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            directory_path = Path(directory)
            private_audit = directory_path / "private-customer-audit.json"
            private_audit.write_text('{"secret":"do-not-print"}', encoding="utf-8")
            output = directory_path / "report.pdf"
            result = self._arguments(
                ["--audit", str(private_audit), "--report", str(SYNTHETIC_REPORT), "--output", str(output)]
            )
            self.assertEqual(1, result.returncode)
            self.assertEqual("data: could not render validated report\n", result.stderr)
            self.assertNotIn("private-customer", result.stderr)
            self.assertNotIn("do-not-print", result.stderr)
            self.assertFalse(output.exists())
        after = {path.name for path in TEMP_ROOT.glob("punchlist-pdf-*")}
        self.assertEqual(before, after)

    def test_data_mode_rejects_symlink_input_and_output_alias(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            directory_path = Path(directory)
            audit_alias = directory_path / "audit.json"
            try:
                os.symlink(SYNTHETIC_AUDIT, audit_alias)
            except OSError as error:
                self.skipTest(f"symlinks unsupported: {error.__class__.__name__}")
            output = directory_path / "report.pdf"
            result = self._arguments(
                ["--audit", str(audit_alias), "--report", str(SYNTHETIC_REPORT), "--output", str(output)]
            )
            self.assertEqual(1, result.returncode)
            self.assertEqual("data: could not read report inputs\n", result.stderr)
            self.assertFalse(output.exists())

    def test_data_mode_rejects_hard_link_output_alias_without_changing_input(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            output = Path(directory) / "report.pdf"
            try:
                os.link(SYNTHETIC_AUDIT, output)
            except OSError as error:
                self.skipTest(f"hard links unsupported: {error.__class__.__name__}")
            before = SYNTHETIC_AUDIT.read_bytes()
            result = self._arguments(
                ["--audit", str(SYNTHETIC_AUDIT), "--report", str(SYNTHETIC_REPORT), "--output", str(output)]
            )
            self.assertEqual(1, result.returncode)
            self.assertEqual("output: must not alias input\n", result.stderr)
            self.assertEqual(before, SYNTHETIC_AUDIT.read_bytes())

    def test_data_mode_rejects_aliased_data_inputs(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            output = Path(directory) / "report.pdf"
            result = self._arguments(
                ["--audit", str(SYNTHETIC_AUDIT), "--report", str(SYNTHETIC_AUDIT), "--output", str(output)]
            )
            self.assertEqual(1, result.returncode)
            self.assertEqual("data: report inputs must not alias\n", result.stderr)
            self.assertFalse(output.exists())

    @staticmethod
    def _run(input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
        return PrintReportBoundaryTests._arguments(
            ["--input", str(input_path), "--output", str(output_path)]
        )

    @staticmethod
    def _arguments(arguments: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["node", str(HELPER), *arguments],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
