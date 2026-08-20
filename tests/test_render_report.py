import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from scripts.report_model import load_document
from scripts.render_report import render_report


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_ROOT = REPO_ROOT / "examples" / "synthetic"
THEME_PATH = REPO_ROOT / "themes" / "punchlist-default.json"


class RenderReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = load_document(SYNTHETIC_ROOT / "audit.json")
        self.report = load_document(SYNTHETIC_ROOT / "report.json")
        self.theme = load_document(THEME_PATH)

    def test_rendered_report_has_the_six_recipient_sections_and_derived_counts(self) -> None:
        html = render_report(self.audit, self.report, self.theme)
        self.assertEqual(6, html.count('<article class="report-page"'))
        for section in ("cover", "journey", "lead-findings", "strengths", "recommendations", "appendix"):
            self.assertIn(f'data-section="{section}"', html)
        self.assertIn('<dt>recall-tax</dt><dd>1</dd>', html)
        self.assertIn('<dt>vanishing-ink</dt><dd>1</dd>', html)

    def test_renderer_escapes_report_and_evidence_strings_including_alt_text(self) -> None:
        audit, report = copy.deepcopy(self.audit), copy.deepcopy(self.report)
        report["cover"]["statement"] = '<script>alert("cover")</script>'
        report["journey"][0]["summary"] = '<b onclick="journey()">journey</b>'
        report["lead_headlines"]["f-fc11114007df"] = '<img src=x onerror="headline()">'
        audit["strengths"][0]["summary"] = '<svg onload="strength()">'
        report["recommendations"][0]["summary"] = '<a href="javascript:recommend()">recommend</a>'
        report["next_test"]["summary"] = '<em onclick="test()">next</em>'
        audit["findings"][0]["evidence"][0] = {
            "type": "rendered", "source": "synthetic rendered probe",
            "summary": "Synthetic comparison screenshot.", "verified_how": "rendered",
            "publication_approved": True, "alt": '<img src=x onerror="alt()">',
            "provenance_id": "prov-synthetic-surface", "classification": "synthetic",
        }
        html = render_report(audit, report, self.theme)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<b onclick=', html)
        self.assertNotIn('<img src=x onerror=', html)
        self.assertIn('&lt;script&gt;alert(&quot;cover&quot;)&lt;/script&gt;', html)
        self.assertIn('&lt;img src=x onerror=&quot;alt()&quot;&gt;', html)
        self.assertNotIn('role="img"', html)
        self.assertNotIn("<img", html)

    def test_cover_is_standalone_and_uses_immutable_project_attribution(self) -> None:
        report = copy.deepcopy(self.report)
        report["author"] = "Untrusted author label"
        html = render_report(self.audit, report, self.theme)
        self.assertIn('<p class="byline">Punchlist · Independent experience review</p>', html)
        self.assertNotIn('<a href=', html)
        self.assertIn("Independent experience review", html)
        self.assertIn("2026-08-20", html)
        self.assertIn("First visit", html)
        self.assertIn("Desktop", html)
        self.assertIn("experience", html)
        self.assertIn("rendered", html)
        self.assertNotIn("Untrusted author label", html)

    def test_appendix_contains_traceable_finding_and_evidence_details(self) -> None:
        html = render_report(self.audit, self.report, self.theme)
        self.assertIn("f-fc11114007df", html)
        self.assertIn("primary comparison card", html)
        self.assertIn("rendered", html)
        self.assertIn("A rendered comparison probe confirms that the detail text remains visually indistinct from its card background.", html)
        self.assertIn("Legible", html)
        self.assertIn("1.4.3 Contrast Minimum (AA)", html)
        self.assertEqual(3, html.count('<section class="appendix-group">'))
        self.assertIn('.appendix-group { break-inside: avoid-page; }', html)

    def test_renderer_resolves_canonical_records_and_rejects_unknown_ids(self) -> None:
        report = copy.deepcopy(self.report)
        report["lead_findings"] = ["f-does-not-exist"]
        with self.assertRaisesRegex(ValueError, "unknown canonical finding"):
            render_report(self.audit, report, self.theme)

    def test_renderer_is_deterministic_when_json_keys_and_findings_are_reordered(self) -> None:
        reordered_audit = json.loads(json.dumps(self.audit, sort_keys=True))
        reordered_audit["findings"].reverse()
        reordered_report = json.loads(json.dumps(self.report, sort_keys=True))
        self.assertEqual(render_report(self.audit, self.report, self.theme), render_report(reordered_audit, reordered_report, self.theme))

    def test_direct_api_rejects_reversed_duplicate_findings_with_stable_location_errors(self) -> None:
        first = copy.deepcopy(self.audit["findings"][0])
        duplicate = copy.deepcopy(first)
        duplicate["symptom"] = "A distinct but equally confirmed duplicate record."
        errors = []
        for pair in ((first, duplicate), (duplicate, first)):
            audit = copy.deepcopy(self.audit)
            audit["findings"] = [pair[0], pair[1], audit["findings"][1]]
            with self.assertRaisesRegex(ValueError, r"^audit\.findings\[1\]\.finding_id: duplicate finding_id") as raised:
                render_report(audit, self.report, self.theme)
            errors.append(str(raised.exception))

        self.assertEqual(errors[0], errors[1])

    def test_renderer_inlines_only_theme_derived_semantic_variables_and_no_template_markers(self) -> None:
        html = render_report(self.audit, self.report, self.theme)
        root_block = html.split(":root {", 1)[1].split("}", 1)[0]
        variables = {line.strip().split(":", 1)[0] for line in root_block.splitlines() if line.strip().startswith("--")}
        self.assertEqual({"--color-canvas", "--color-ink", "--color-muted", "--color-accent", "--color-supporting", "--color-evidence-background", "--color-evidence-label", "--font-display", "--font-body", "--report-footer", "--space-1", "--space-2", "--space-3", "--space-4", "--space-5", "--space-6", "--space-7", "--space-8", "--space-9", "--space-10", "--space-11", "--page-margin", "--page-columns", "--page-gutter"}, variables)
        self.assertNotIn("{{", html)
        self.assertNotIn("}}", html)

    def test_report_marker_text_is_literal_after_template_placeholders_are_resolved(self) -> None:
        report = copy.deepcopy(self.report)
        report["cover"]["statement"] = "Keep {{TOKEN}} visible for the evaluator."
        self.assertIn("Keep {{TOKEN}} visible for the evaluator.", render_report(self.audit, report, self.theme))

    def test_rendered_print_css_allows_unbounded_report_content_to_split(self) -> None:
        html = render_report(self.audit, self.report, self.theme)
        self.assertNotIn(".report-page + .report-page { break-before: page; }", html)
        self.assertNotIn('.report-page[data-section="strengths"] { break-after: avoid; }', html)
        self.assertIn(
            '.report-page[data-section="lead-findings"], .report-page[data-section="recommendations"], .report-page[data-section="appendix"] { break-before: page; }',
            html,
        )
        self.assertIn('@media screen and (max-width: 42rem)', html)

    def test_running_footer_uses_css_text_instead_of_a_literal_unicode_escape(self) -> None:
        html = render_report(self.audit, self.report, self.theme)
        self.assertIn('Sample Platform · Punchlist · Independent experience review', html)
        self.assertNotIn(r"\u00b7", html)

    def test_cli_applies_only_a_safe_contrasting_platform_accent_adapter(self) -> None:
        adapter = load_document(REPO_ROOT / "themes" / "platform-accent.example.json")
        adapter["platform_name"] = "Adapted Platform"
        adapter["accent"] = "#1746A2"
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            adapter_path = directory_path / "adapter.json"
            output = directory_path / "report.html"
            adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
            result = self._cli(
                "--audit", str(SYNTHETIC_ROOT / "audit.json"),
                "--report", str(SYNTHETIC_ROOT / "report.json"),
                "--theme", str(adapter_path),
                "--output", str(output),
            )
            self.assertEqual(0, result.returncode, result.stderr)
            html = output.read_text(encoding="utf-8")
            self.assertIn("--color-accent: #1746A2", html)
            self.assertIn("Adapted Platform", html)
            self.assertIn("--font-display: Editorial New", html)
            self.assertIn("--page-columns: 12", html)
            self.assertIn("Punchlist · Independent experience review", html)
            self.assertIn('<a href="https://sample-platform.example">Platform design reference</a>', html)
            self.assertIn(".byline { border-left: 3px solid var(--color-supporting);", html)
            self.assertEqual(1, html.count('<p class="byline">Punchlist · Independent experience review</p>'))

    def test_default_theme_has_no_platform_reference_and_adapter_cannot_replace_attribution(self) -> None:
        default_html = render_report(self.audit, self.report, self.theme)
        self.assertNotIn("Platform design reference", default_html)
        self.assertIn('<p class="byline">Punchlist · Independent experience review</p>', default_html)
        self.assertNotIn('<a href=', default_html)

    def test_renderer_rejects_nonpublic_platform_source_url_without_echoing_it(self) -> None:
        unsafe_theme = copy.deepcopy(self.theme)
        unsafe_theme["source_url"] = "https://localhost/private-design"
        with self.assertRaisesRegex(ValueError, r"^theme: platform source must be a public HTTPS URL$"):
            render_report(self.audit, self.report, unsafe_theme)

    def test_cli_rejects_low_contrast_and_protected_theme_adapter_values(self) -> None:
        adapter = load_document(REPO_ROOT / "themes" / "platform-accent.example.json")
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            output = directory_path / "report.html"
            cases = (
                ({**adapter, "accent": "#FFFFFF"}, "theme: platform accent has insufficient contrast"),
                ({**adapter, "evidence_background": "#FFFFFF", "evidence_label": "#FFFFFF"}, "theme: platform accent has insufficient contrast"),
                ({**adapter, "typography": {"display_family": "Other", "body_family": "Other"}}, "theme: invalid platform accent"),
            )
            for index, (value, expected) in enumerate(cases):
                adapter_path = directory_path / f"adapter-{index}.json"
                adapter_path.write_text(json.dumps(value), encoding="utf-8")
                result = self._cli(
                    "--audit", str(SYNTHETIC_ROOT / "audit.json"),
                    "--report", str(SYNTHETIC_ROOT / "report.json"),
                    "--theme", str(adapter_path),
                    "--output", str(output),
                )
                self.assertEqual(1, result.returncode)
                self.assertEqual(f"{expected}\n", result.stderr)
                self.assertFalse(output.exists())

    def test_cli_rejects_existing_output_symlink_and_writes_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            destination = directory_path / "destination.html"
            destination.write_text("unchanged", encoding="utf-8")
            output = directory_path / "report.html"
            try:
                os.symlink(destination.name, output)
            except OSError as error:
                self.skipTest(f"symlinks unsupported: {error.__class__.__name__}")
            result = self._cli("--audit", str(SYNTHETIC_ROOT / "audit.json"), "--report", str(SYNTHETIC_ROOT / "report.json"), "--output", str(output))
            self.assertEqual(1, result.returncode)
            self.assertEqual("output: existing symlink is not allowed\n", result.stderr)
            self.assertEqual("unchanged", destination.read_text(encoding="utf-8"))
            self.assertEqual([], list(directory_path.glob(".report.html.*.tmp")))

    def test_cli_writes_a_recipient_safe_synthetic_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.html"
            result = self._cli("--audit", str(SYNTHETIC_ROOT / "audit.json"), "--report", str(SYNTHETIC_ROOT / "report.json"), "--output", str(output))
            self.assertEqual(0, result.returncode, result.stderr)
            html = output.read_text(encoding="utf-8")
            self.assertIn("Sample Platform", html)
            self.assertNotIn("C:\\Users\\", html)
            self.assertIsNone(re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", html, re.IGNORECASE))
            self.assertNotIn("{{", html)

    def test_cli_returns_location_only_errors_for_invalid_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            audit_path, report_path = directory_path / "audit.json", directory_path / "report.json"
            invalid_report = copy.deepcopy(self.report)
            invalid_report["cover"]["statement"] = r"C:\\Users\\person\\private.txt"
            audit_path.write_text(json.dumps(self.audit), encoding="utf-8")
            report_path.write_text(json.dumps(invalid_report), encoding="utf-8")
            result = self._cli("--audit", str(audit_path), "--report", str(report_path), "--output", str(directory_path / "report.html"))
            self.assertEqual(1, result.returncode)
            self.assertIn("report.cover.statement: absolute local path", result.stderr)
            self.assertNotIn("C:\\Users\\person", result.stderr)

    def test_cli_does_not_echo_an_unreadable_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_audit = Path(directory) / "private-input.json"
            result = self._cli("--audit", str(missing_audit), "--report", str(SYNTHETIC_ROOT / "report.json"), "--output", str(Path(directory) / "report.html"))
            self.assertEqual(1, result.returncode)
            self.assertEqual("audit: could not load JSON\n", result.stderr)
            self.assertNotIn(str(missing_audit), result.stderr)

    def test_cli_rejects_output_aliases_without_changing_any_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            audit_path, report_path = directory_path / "audit.json", directory_path / "report.json"
            audit_path.write_text(json.dumps(self.audit), encoding="utf-8")
            report_path.write_text(json.dumps(self.report), encoding="utf-8")
            for output in (audit_path, report_path, THEME_PATH):
                before = output.read_bytes()
                result = self._cli("--audit", str(audit_path), "--report", str(report_path), "--output", str(output))
                self.assertEqual(1, result.returncode)
                self.assertEqual("output: must not alias an input\n", result.stderr)
                self.assertEqual(before, output.read_bytes())

    def test_cli_rejects_hard_link_output_alias_without_changing_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            audit_path, report_path = directory_path / "audit.json", directory_path / "report.json"
            output_path = directory_path / "audit-hard-link.html"
            audit_path.write_text(json.dumps(self.audit), encoding="utf-8")
            report_path.write_text(json.dumps(self.report), encoding="utf-8")
            try:
                os.link(audit_path, output_path)
            except OSError as error:
                self.skipTest(f"hard links unsupported: {error.__class__.__name__}")
            before = audit_path.read_bytes()

            result = self._cli("--audit", str(audit_path), "--report", str(report_path), "--output", str(output_path))

            self.assertEqual(1, result.returncode)
            self.assertEqual("output: must not alias an input\n", result.stderr)
            self.assertEqual(before, audit_path.read_bytes())

    def test_cli_argument_errors_are_safe_and_use_exit_code_one(self) -> None:
        for arguments in ((), ("--not-an-option",)):
            result = self._cli(*arguments)
            self.assertEqual(1, result.returncode)
            self.assertEqual("arguments: invalid command\n", result.stderr)
            self.assertNotIn("usage:", result.stderr.lower())

    @staticmethod
    def _cli(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "scripts/render_report.py", *arguments], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
