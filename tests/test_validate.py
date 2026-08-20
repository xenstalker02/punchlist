import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.inspect_pdf import PdfDependencyError
from scripts.validate import (
    GENERIC_BRIEF_CONTRACT,
    validate_public_safety,
    validate_schema,
    validate_source_reference,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate.py"


class ValidatorSchemaTests(unittest.TestCase):
    def final_finding(self) -> dict[str, object]:
        return {
            "finding_id": "f-0123456789ab",
            "defect": "vanishing-ink",
            "surface": "sample-screen",
            "locator": "main heading",
            "fingerprint": "0" * 64,
            "manifestation": "consistent",
            "symptom": "The heading cannot be read.",
            "evidence": [
                {
                    "type": "rendered",
                    "provenance_id": "prov-synthetic",
                    "classification": "synthetic",
                    "source": "synthetic measurement",
                    "summary": "The contrast check failed.",
                    "verified_how": "rendered",
                    "publication_approved": True,
                }
            ],
            "verified_how": "rendered",
            "severity_basis": "task completion impact",
            "severity_votes": [{"critic_id": "critic-a", "severity": 2}],
            "severity": 2,
            "decision": "confirmed",
            "fix": "Increase contrast.",
            "fix_tier": "mechanical",
            "fixed_how": "proposed",
            "lifecycle": "open",
        }

    def test_schema_constraints_are_enforced(self) -> None:
        schema = {
            "type": "object",
            "required": ["name", "ids"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "ids": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
            },
        }

        errors = validate_schema({"name": "", "ids": ["x", "x"], "extra": True}, schema, "fixture")

        self.assertTrue(any("minLength" in error for error in errors))
        self.assertTrue(any("unique" in error for error in errors))
        self.assertTrue(any("unexpected property" in error for error in errors))

    def test_taxonomy_uses_non_evidentiary_illustrations_not_unproven_instances(self) -> None:
        defect_schema = json.loads(
            (REPO_ROOT / "schema" / "defect.schema.json").read_text(encoding="utf-8")
        )
        self.assertIn("illustration", defect_schema["required"])
        self.assertNotIn("example", defect_schema["properties"])
        for category in ("interface", "content", "behavior"):
            records = json.loads(
                (REPO_ROOT / "taxonomy" / f"{category}.json").read_text(encoding="utf-8")
            )
            for record in records:
                self.assertNotIn("example", record)
                self.assertTrue(record["illustration"].startswith("Non-evidentiary illustration: "))

    def test_url_pattern_uses_json_schema_search_semantics(self) -> None:
        errors = validate_schema(
            {"source_url": "https://sample-platform.example"},
            {"type": "object", "properties": {"source_url": {"type": "string", "pattern": "^https://"}}},
            "theme",
        )

        self.assertEqual([], errors)

    def test_source_reference_requires_known_source_and_single_matcher(self) -> None:
        catalog = {
            "wcag-2.2": {
                "citation_patterns": [
                    r"^1\.4\.3 .+$",
                    r"^1\.4\.3 Contrast Minimum \(AA\)$",
                ]
            }
        }

        unknown_errors = validate_source_reference(
            {"source_id": "unknown", "citation": "1.4.3 Contrast Minimum (AA)"}, catalog
        )
        ambiguous_errors = validate_source_reference(
            {"source_id": "wcag-2.2", "citation": "1.4.3 Contrast Minimum (AA)"}, catalog
        )
        unmatched_errors = validate_source_reference(
            {"source_id": "wcag-2.2", "citation": "2.1.1 Keyboard (A)"}, catalog
        )
        malformed_errors = validate_source_reference(
            {"source_id": [], "citation": "1.4.3 Contrast Minimum (AA)"}, catalog
        )

        self.assertTrue(any("unknown source_id" in error for error in unknown_errors))
        self.assertTrue(any("exactly one permitted pattern" in error for error in ambiguous_errors))
        self.assertTrue(any("exactly one permitted pattern" in error for error in unmatched_errors))
        self.assertTrue(any("source_id must be a string" in error for error in malformed_errors))

    def test_source_reference_rejects_invalid_matcher(self) -> None:
        errors = validate_source_reference(
            {"source_id": "invalid", "citation": "anything"},
            {"invalid": {"citation_patterns": ["["]}},
        )

        self.assertTrue(any("invalid citation matcher" in error for error in errors))

    def test_audit_findings_reject_nonfinal_lifecycle_values(self) -> None:
        audit_schema = json.loads(
            (REPO_ROOT / "schema" / "audit.schema.json").read_text(encoding="utf-8")
        )
        frame_limited = self.final_finding()
        frame_limited["verified_how"] = "frame-limited"
        severity_zero = self.final_finding()
        severity_zero["severity"] = 0
        vetoed = self.final_finding()
        vetoed["decision"] = "vetoed"

        frame_errors = validate_schema({"findings": [frame_limited]}, audit_schema, "audit")
        zero_errors = validate_schema({"findings": [severity_zero]}, audit_schema, "audit")
        veto_errors = validate_schema({"findings": [vetoed]}, audit_schema, "audit")

        self.assertIn("audit.findings[0].verified_how: must be one of allowed values", frame_errors)
        self.assertTrue(any("below minimum" in error for error in zero_errors))
        self.assertIn("audit.findings[0].decision: must be one of allowed values", veto_errors)

    def test_report_recommendations_require_canonical_finding_ids(self) -> None:
        report_schema = json.loads(
            (REPO_ROOT / "schema" / "report.schema.json").read_text(encoding="utf-8")
        )
        errors = validate_schema(
            {
                "recommendations": [
                    {
                        "recommendation_id": "recommendation-1",
                        "canonical_ids": ["gap-not-a-finding"],
                        "summary": "Use the canonical finding.",
                    }
                ]
            },
            report_schema,
            "report",
        )

        self.assertIn(
            "report.recommendations[0].canonical_ids[0]: does not match required pattern",
            errors,
        )


class ValidatorIntegrationTests(unittest.TestCase):
    def copy_repo(self, destination: Path) -> Path:
        root = destination / "punchlist"
        shutil.copytree(
            REPO_ROOT,
            root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "tmp"),
        )
        return root

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_repository_passes_validation(self) -> None:
        result = self.run_validator(REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("50 defects", result.stdout)

    def test_fresh_autocrlf_checkout_preserves_generated_and_registered_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = self.copy_repo(temp_root)
            subprocess.run(["git", "init", str(source)], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(source), "add", "--all"], check=True, capture_output=True, text=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(source),
                    "-c",
                    "user.name=Punchlist Test",
                    "-c",
                    "user.email=punchlist-test@example.invalid",
                    "commit",
                    "-m",
                    "fixture",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            checkout = temp_root / "autocrlf-checkout"
            subprocess.run(
                ["git", "-c", "core.autocrlf=true", "clone", "--no-local", str(source), str(checkout)],
                check=True,
                capture_output=True,
                text=True,
            )

            result = self.run_validator(checkout)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("50 defects", result.stdout)

    def test_public_report_docs_and_governance_are_available(self) -> None:
        required_paths = (
            "README.md",
            "SECURITY.md",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "CODE_OF_CONDUCT.md",
            "SUPPORT.md",
            "RELEASING.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            "examples/synthetic/report.html",
            "examples/synthetic/report.pdf",
        )
        for relative in required_paths:
            self.assertTrue((REPO_ROOT / relative).is_file(), relative)

        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        required_surfaces = (
            GENERIC_BRIEF_CONTRACT,
            "examples/synthetic/report.html",
            "examples/synthetic/report.pdf",
            "punchlist-default",
            "Punchlist · Independent experience review",
            "Capability matrix",
            "public and logged-out",
            "v0.1 production-ready",
        )
        for surface in required_surfaces:
            self.assertIn(surface, readme)
        self.assertNotIn("development preview", readme.lower())
        for relative in ("CHANGELOG.md", "SECURITY.md", "RELEASING.md", "docs/handoffs/figma-cover-report-alignment.md"):
            public_text = (REPO_ROOT / relative).read_text(encoding="utf-8").lower()
            self.assertNotIn("development preview", public_text, relative)
        contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        pull_request_template = (REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
        skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        taxonomy_text = "\n".join(
            (REPO_ROOT / "taxonomy" / f"{category}.json").read_text(encoding="utf-8")
            for category in ("interface", "content", "behavior")
        )
        self.assertIn("non-evidentiary illustration", contributing)
        self.assertNotIn("documented real instance", contributing)
        self.assertIn("non-evidentiary illustration", pull_request_template)
        self.assertNotIn("documented real instance", pull_request_template)
        self.assertIn("canonical Not assessed", skill)
        self.assertNotIn("verified_how: frame-limited", skill)
        self.assertNotIn("kbqs", taxonomy_text)

    def test_broken_entry_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            taxonomy_path = root / "taxonomy" / "behavior.json"
            entries = json.loads(taxonomy_path.read_text(encoding="utf-8"))
            entries[0].pop("illustration")
            entries[0]["refs"] = {"wcag": [], "other": []}
            taxonomy_path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("illustration", result.stdout)
        self.assertIn("public-standard reference", result.stdout)

    def test_wrong_category_count_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            taxonomy_path = root / "taxonomy" / "content.json"
            entries = json.loads(taxonomy_path.read_text(encoding="utf-8"))
            taxonomy_path.write_text(json.dumps(entries[:-1], indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected 16 entries", result.stdout)

    def test_unknown_source_reference_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            taxonomy_path = root / "taxonomy" / "interface.json"
            entries = json.loads(taxonomy_path.read_text(encoding="utf-8-sig"))
            entries[0]["refs"]["wcag"][0]["source_id"] = "unknown"
            taxonomy_path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown source_id", result.stdout)

    def test_missing_internal_reference_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            readme_path = root / "README.md"
            readme_path.write_text(
                readme_path.read_text(encoding="utf-8")
                + "\nSee [`missing.json`](examples/missing.json).\n",
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("examples/missing.json", result.stdout)

    def test_synthetic_audit_with_unknown_defect_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            audit_path = root / "examples" / "synthetic" / "audit.json"
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            audit["findings"][0]["defect"] = "unknown-defect"
            audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown defect", result.stdout)

    def test_synthetic_audit_with_incomplete_ledger_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            audit_path = root / "examples" / "synthetic" / "audit.json"
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            audit["ledger"].pop()
            audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete eligible ledger", result.stdout)

    def test_synthetic_report_with_forbidden_theme_key_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            report_path = root / "examples" / "synthetic" / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["theme"]["platform_overrides"] = {"motif": "unapproved"}
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("report.theme: unexpected property", result.stdout)

    def test_stale_synthetic_html_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            html_path = root / "examples" / "synthetic" / "report.html"
            html_path.write_text(html_path.read_text(encoding="utf-8") + "stale", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale generated HTML", result.stdout)

    def test_candidate_template_change_returns_stale_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            template_path = root / "templates" / "report" / "report.html"
            template_path.write_text(
                template_path.read_text(encoding="utf-8") + "\n<!-- candidate template -->\n",
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale generated HTML", result.stdout)

    def test_public_safety_failures_return_location_only_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            fixture_path = root / "examples" / "synthetic" / "public-safety.json"
            fixture_path.write_text(
                json.dumps(
                    {
                        "path": "C:\\Users\\me\\private",
                        "credential": "api_key=topsecret",
                        "email": "person@example.com",
                        "url": "http://localhost:3000/private",
                        "evidence": {"type": "screenshot", "source": "fixture"},
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public-safety.json.path: absolute local path", result.stdout)
        self.assertIn("public-safety.json.credential: credential-shaped assignment", result.stdout)
        self.assertIn("public-safety.json.email: email address", result.stdout)
        self.assertIn("public-safety.json.url: private or local URL", result.stdout)
        self.assertIn("public-safety.json.evidence: unapproved screenshot evidence", result.stdout)
        self.assertNotIn("topsecret", result.stdout)

    def test_public_pdf_with_secret_shaped_text_returns_nonzero(self) -> None:
        import fitz

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            fixture_path = root / "docs" / "unsafe-public.pdf"
            fixture_path.parent.mkdir(exist_ok=True)
            document = fitz.open()
            document.new_page().insert_text((72, 72), "api_key=topsecret")
            document.save(fixture_path)
            document.close()

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("docs/unsafe-public.pdf.page[1]: credential-shaped assignment", result.stdout)
        self.assertNotIn("topsecret", result.stdout)

    def test_public_pdf_requires_pymupdf_instead_of_skipping_validation(self) -> None:
        with patch(
            "scripts.inspect_pdf.validate_pdf_privacy",
            side_effect=PdfDependencyError("PyMuPDF is unavailable"),
        ):
            errors = validate_public_safety(REPO_ROOT)

        self.assertIn(
            "examples/synthetic/report.pdf: PDF validation requires PyMuPDF from requirements-dev.txt",
            errors,
        )

    def test_domain_specific_readme_brief_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            readme_path = root / "README.md"
            readme_path.write_text(
                readme_path.read_text(encoding="utf-8")
                .replace(
                    "A `[user]`, in `[state]` on `[device]`, starts at `[entry point]` and tries to "
                    "`[complete task]`; `[profile]` profile. Severity basis: `[basis]`.",
                    "A first-time vinyl buyer, signed out on desktop, starts from a known album "
                    "and tries to choose one edition to buy; experience profile. Severity basis: "
                    "first-time purchase.",
                ),
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("generic placeholder brief contract", result.stdout)

    def test_additive_domain_specific_readme_brief_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            readme_path = root / "README.md"
            readme_path.write_text(
                readme_path.read_text(encoding="utf-8")
                + "\nA first-time vinyl buyer starts from a known album and chooses one edition to buy. "
                "Severity basis: first-time purchase.\n",
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("domain-specific brief marker", result.stdout)

    def test_public_doc_forbidden_marker_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            changelog_path = root / "CHANGELOG.md"
            changelog_path.write_text(
                changelog_path.read_text(encoding="utf-8")
                + "\nCompass collections audit\n",
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CHANGELOG.md: public forbidden marker", result.stdout)
        self.assertNotIn("Compass collections audit", result.stdout)

    def test_named_company_and_pharma_markers_are_rejected_anywhere_public(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            fixture = root / "eval" / "unsafe.md"
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_text("A Compass workflow in pharma commercial analytics.\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("eval/unsafe.md: public forbidden marker", result.stdout)
        self.assertNotIn("pharma commercial analytics", result.stdout.lower())

    def test_unregistered_public_media_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            (root / "assets" / "unregistered.svg").write_text("<svg/>", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("assets/unregistered.svg: unregistered public media", result.stdout)

    def test_public_svg_and_yaml_are_privacy_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            workflow = root / ".github" / "unsafe.yml"
            workflow.write_text("note: token=topsecret\n", encoding="utf-8")
            svg = root / "assets" / "social-preview.svg"
            svg.write_text(svg.read_text(encoding="utf-8") + "<!-- token=topsecret -->", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".github/unsafe.yml: credential-shaped assignment", result.stdout)
        self.assertIn("assets/social-preview.svg: credential-shaped assignment", result.stdout)
        self.assertNotIn("topsecret", result.stdout)

    def test_public_media_manifest_hash_mismatch_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            png = root / "assets" / "social-preview.png"
            png.write_bytes(png.read_bytes() + b"changed")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("assets/social-preview.png: public media hash mismatch", result.stdout)

    def test_schema_error_does_not_echo_secret_shaped_target_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            audit_path = root / "examples" / "synthetic" / "audit.json"
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            audit["target"]["classification"] = "api_key=topsecret"
            audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("api_key", result.stdout)
        self.assertNotIn("topsecret", result.stdout)

    def test_semantic_unknown_report_id_does_not_echo_candidate_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            report_path = root / "examples" / "synthetic" / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            secret_finding_id = "f-deadbeefcafe"
            report["lead_findings"] = [secret_finding_id]
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(secret_finding_id, result.stdout)
        self.assertNotIn("deadbeefcafe", result.stdout)

    def test_public_docs_are_scanned_for_secret_shaped_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            docs_path = root / "docs" / "public.md"
            docs_path.parent.mkdir(exist_ok=True)
            docs_path.write_text("token=topsecret\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("docs/public.md: credential-shaped assignment", result.stdout)
        self.assertNotIn("topsecret", result.stdout)

    def test_unregistered_synthetic_json_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            fixture_path = root / "examples" / "synthetic" / "extra.json"
            fixture_path.write_text("{}\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("examples/synthetic/extra.json: unregistered synthetic JSON", result.stdout)

    def test_present_governance_file_with_broken_reference_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            support_path = root / "SUPPORT.md"
            support_path.write_text("See [missing policy](missing-policy.md).\n", encoding="utf-8")

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SUPPORT.md: internal reference does not resolve", result.stdout)

    def test_releasing_file_with_broken_reference_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            releasing_path = root / "RELEASING.md"
            releasing_path.write_text(
                releasing_path.read_text(encoding="utf-8").replace(
                    "[README](README.md)", "[README](missing-policy.md)"
                ),
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RELEASING.md: internal reference does not resolve", result.stdout)

    def test_security_requires_the_report_data_handling_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            security_path = root / "SECURITY.md"
            security_path.write_text(
                security_path.read_text(encoding="utf-8").replace(
                    "## Handle audit data separately\n\n", ""
                ),
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECURITY.md: missing governance section: report-data handling", result.stdout)

    def test_releasing_requires_fresh_separate_publish_authorization_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_repo(Path(temp_dir))
            releasing_path = root / "RELEASING.md"
            releasing_path.write_text(
                releasing_path.read_text(encoding="utf-8").replace(
                    "<!-- governance: fresh-separate-publish-authorization -->\n", ""
                ),
                encoding="utf-8",
            )

            result = self.run_validator(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RELEASING.md: missing governance checkpoint: publish authorization", result.stdout)


if __name__ == "__main__":
    unittest.main()
