import copy
from pathlib import Path
import unittest

from scripts.report_model import (
    canonical_surface,
    computed_counts,
    finding_fingerprint,
    load_document,
    merge_platform_accent,
    privacy_errors,
    validate_audit_bundle,
    validate_report_projection,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_ROOT = REPO_ROOT / "examples" / "synthetic"


class ReportModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = load_document(SYNTHETIC_ROOT / "audit.json")
        self.report = load_document(SYNTHETIC_ROOT / "report.json")
        self.theme = load_document(REPO_ROOT / "themes" / "punchlist-default.json")
        self.accent = load_document(REPO_ROOT / "themes" / "platform-accent.example.json")

    def test_synthetic_bundle_is_valid(self) -> None:
        self.assertEqual([], validate_audit_bundle(REPO_ROOT, self.audit))
        self.assertEqual([], validate_report_projection(self.audit, self.report, self.theme))

    def test_theme_rejects_css_control_syntax_in_color_and_font_tokens(self) -> None:
        theme = copy.deepcopy(self.theme)
        theme["colors"]["canvas"] = "white;} body { display: none"
        theme["typography"]["body_family"] = "Space Grotesk; } body { display: none"

        errors = validate_report_projection(self.audit, self.report, theme)

        self.assertTrue(errors)
        self.assertTrue(any("theme" in error for error in errors))

    def test_theme_rejects_css_control_characters_in_font_tokens(self) -> None:
        theme = copy.deepcopy(self.theme)
        theme["typography"]["body_family"] = "Space Grotesk\n"

        self.assertTrue(validate_report_projection(self.audit, self.report, theme))

    def test_default_theme_uses_portfolio_font_roles_and_spacing_scale(self) -> None:
        self.assertEqual("Editorial New", self.theme["typography"]["display_family"])
        self.assertEqual("Space Grotesk", self.theme["typography"]["body_family"])
        self.assertEqual([4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 96], self.theme["spacing"])

    def test_frame_limited_final_finding_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["verified_how"] = "frame-limited"
        errors = validate_audit_bundle(REPO_ROOT, audit)
        self.assertIn("audit.findings[0].verified_how: must be one of allowed values", errors)

    def test_severity_zero_final_finding_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["severity"] = 0
        errors = validate_audit_bundle(REPO_ROOT, audit)
        self.assertTrue(any("severity must be above zero" in error for error in errors))

    def test_unknown_defect_and_also_match_are_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["also_matches"] = ["unknown-defect"]
        errors = validate_audit_bundle(REPO_ROOT, audit)
        self.assertTrue(any("unknown defect" in error for error in errors))

    def test_unknown_primary_defect_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["defect"] = "unknown-defect"
        errors = validate_audit_bundle(REPO_ROOT, audit)
        self.assertTrue(any("unknown defect" in error for error in errors))

    def test_vetoed_final_decision_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["decision"] = "vetoed"
        errors = validate_audit_bundle(REPO_ROOT, audit)
        self.assertIn("audit.findings[0].decision: must be one of allowed values", errors)

    def test_incomplete_eligible_ledger_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["ledger"] = audit["ledger"][:-1]
        errors = validate_audit_bundle(REPO_ROOT, audit)
        self.assertTrue(any("incomplete eligible ledger" in error for error in errors))

    def test_eligible_ledger_row_requires_a_critic_assignment(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["critics"][0]["ledger_ids"] = audit["critics"][0]["ledger_ids"][:-1]

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("unassigned eligible ledger row" in error for error in errors))

    def test_critic_assignment_requires_a_known_ledger_id(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["critics"][0]["ledger_ids"].append("ledger-not-present")

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("unknown ledger ID" in error for error in errors))

    def test_eligible_ledger_row_requires_closure_evidence(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["ledger"][0].pop("closure_evidence", None)

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("closure_evidence" in error for error in errors))

    def test_ineligible_ledger_row_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["capabilities"]["supported_inputs"] = ["screenshot"]
        audit["ledger"].append(
            {
                "ledger_id": "ledger-ineligible",
                "defect": "silent-curfew",
                "disposition": "checked_absent",
                "eligibility_evidence": "Synthetic screenshot fixture.",
                "probe": "Inspect the synthetic screenshot.",
                "closure_evidence": "No condition is visible in the synthetic screenshot.",
            }
        )

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("ineligible ledger defect" in error for error in errors))

    def test_equivalent_input_order_has_same_fingerprints_and_counts(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"] = list(reversed(audit["findings"]))
        original_fingerprints = sorted(finding_fingerprint(finding) for finding in self.audit["findings"])
        reordered_fingerprints = sorted(finding_fingerprint(finding) for finding in audit["findings"])
        self.assertEqual(original_fingerprints, reordered_fingerprints)
        self.assertEqual(computed_counts(self.audit), computed_counts(audit))
        self.assertEqual("options|comparison", canonical_surface({"b": "comparison", "a": "options"}))
        self.assertEqual([], validate_audit_bundle(REPO_ROOT, audit))

    def test_fingerprint_normalizes_case_and_whitespace(self) -> None:
        finding = copy.deepcopy(self.audit["findings"][0])
        variant = copy.deepcopy(finding)
        variant["surface"] = "  DECISION   SCREEN "
        variant["locator"] = " PRIMARY   comparison CARD "

        self.assertEqual(finding_fingerprint(finding), finding_fingerprint(variant))

    def test_superseded_finding_requires_existing_current_successor_and_acyclic_graph(self) -> None:
        audit = copy.deepcopy(self.audit)
        first, second = audit["findings"]
        first["lifecycle"] = "superseded"
        first["resweep"] = {
            "superseded_by": "f-deadbeefcafe",
            "evidence": "A canonical successor replaces this historical record.",
        }

        missing_errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("superseded_by: must reference an existing current finding" in error for error in missing_errors))
        first["resweep"]["superseded_by"] = second["finding_id"]
        second["lifecycle"] = "superseded"
        second["resweep"] = {
            "superseded_by": first["finding_id"],
            "evidence": "The historical records incorrectly point at each other.",
        }

        cycle_errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("supersession graph must be acyclic" in error for error in cycle_errors))
        self.assertTrue(any("superseded_by: must reference an existing current finding" in error for error in cycle_errors))

    def test_historical_findings_cannot_close_current_ledger_or_projection(self) -> None:
        audit = copy.deepcopy(self.audit)
        report = copy.deepcopy(self.report)
        historical_id = audit["findings"][0]["finding_id"]
        audit["findings"][0]["lifecycle"] = "fixed"
        audit["findings"][0]["resweep"] = {
            "status": "verified-fixed",
            "verified_how": "rendered",
            "verified_at": "2026-08-20T00:00:00Z",
            "verified_by": "Synthetic critic",
            "evidence": "The corrected rendered state no longer exhibits the condition.",
        }

        audit_errors = validate_audit_bundle(REPO_ROOT, audit)
        report_errors = validate_report_projection(audit, report, self.theme)

        self.assertTrue(any("found row has no canonical finding" in error for error in audit_errors))
        self.assertNotIn("vanishing-ink", computed_counts(audit))
        self.assertTrue(any("unknown canonical finding" in error for error in report_errors))
        self.assertIn(historical_id, report["lead_findings"])

    def test_fixed_finding_requires_structured_resweep_verification(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["lifecycle"] = "fixed"

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("fixed finding requires structured verification evidence" in error for error in errors))

    def test_verification_methods_require_declared_capabilities_and_live_rendering(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["capabilities"]["supported_inputs"] = ["screenshot"]

        unsupported = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("verification method is not supported by capabilities" in error for error in unsupported))
        audit = copy.deepcopy(self.audit)
        audit["capabilities"]["rendered_surface_proven_live"] = False

        not_live = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("rendered verification requires a proven-live surface" in error for error in not_live))

    def test_evidence_type_and_verification_method_must_be_compatible(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["evidence"][0]["type"] = "source"

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("evidence type is incompatible with verified_how" in error for error in errors))

    def test_screenshot_only_audit_can_confirm_visible_presence(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["capabilities"] = {
            "rendered_surface_proven_live": False,
            "supported_inputs": ["screenshot"],
        }
        for finding in audit["findings"]:
            finding["verified_how"] = "screenshot"
            for evidence in finding["evidence"]:
                evidence["type"] = "screenshot"
                evidence["verified_how"] = "screenshot"
                evidence["alt"] = "Synthetic screenshot showing the visible condition."
        for strength in audit["strengths"]:
            for evidence in strength["evidence"]:
                evidence["verified_how"] = "screenshot"
                evidence["alt"] = "Synthetic screenshot showing the visible strength."

        self.assertEqual([], validate_audit_bundle(REPO_ROOT, audit))

    def test_screenshot_evidence_rejects_rendered_method_mismatch(self) -> None:
        audit = copy.deepcopy(self.audit)
        evidence = audit["findings"][0]["evidence"][0]
        evidence["type"] = "screenshot"
        evidence["alt"] = "Synthetic screenshot showing the visible condition."

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("evidence type is incompatible with verified_how" in error for error in errors))

    def test_screenshot_evidence_requires_alt_text(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["capabilities"] = {
            "rendered_surface_proven_live": False,
            "supported_inputs": ["screenshot"],
        }
        finding = audit["findings"][0]
        finding["verified_how"] = "screenshot"
        evidence = finding["evidence"][0]
        evidence["type"] = "screenshot"
        evidence["verified_how"] = "screenshot"
        evidence.pop("alt", None)

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("unapproved screenshot evidence" in error for error in errors))

    def test_report_theme_is_theme_id_only(self) -> None:
        report = copy.deepcopy(self.report)
        report["theme"]["platform_overrides"] = {"platform_name": "Inline override"}

        errors = validate_report_projection(self.audit, report, self.theme)

        self.assertTrue(any("report.theme: unexpected property" in error for error in errors))

    def test_found_ledger_row_must_close_to_a_final_finding(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"] = [finding for finding in audit["findings"] if finding["defect"] != "recall-tax"]

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("found row has no canonical finding" in error for error in errors))

    def test_not_assessed_ledger_row_requires_canonical_link_and_valid_blocker(self) -> None:
        audit = copy.deepcopy(self.audit)
        row = audit["ledger"][0]
        row["disposition"] = "not_assessed"
        audit["not_assessed"][0]["blocker"] = "Token budget ran out."
        audit["not_assessed"][0]["escalation_required"] = False

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("not_assessed_id" in error for error in errors))
        self.assertTrue(any("invalid operational blocker" in error for error in errors))
        self.assertTrue(any("escalation_required" in error for error in errors))

    def test_confirmed_finding_votes_match_declared_critics_and_mean(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["severity_votes"] = [
            {"critic_id": "undeclared", "severity": 4},
            {"critic_id": "undeclared", "severity": 2},
        ]
        audit["findings"][0]["severity"] = 4

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("must match declared critics exactly" in error for error in errors))
        self.assertTrue(any("duplicate critic vote" in error for error in errors))
        self.assertTrue(any("must equal severity vote mean" in error for error in errors))

    def test_confirmed_finding_rejects_zero_vote_veto(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["severity_votes"][0]["severity"] = 0

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("zero-vote veto" in error for error in errors))

    def test_evidence_requires_known_approved_provenance(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["evidence"][0]["provenance_id"] = "prov-unknown"
        audit["findings"][0]["evidence"][0]["publication_approved"] = False

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("unknown provenance ID" in error for error in errors))
        self.assertTrue(any("publication approval" in error for error in errors))

    def test_restricted_projection_requires_explicit_authorization_and_approvals(self) -> None:
        audit = copy.deepcopy(self.audit)
        report = copy.deepcopy(self.report)
        audit["target"] = {"classification": "authorized-restricted"}
        report["publication"] = "authorized-restricted"
        report["redaction"]["attested"] = False
        report["review"]["status"] = "pending"
        report["publication_approval"] = {
            "approved": False,
            "approved_by": "Restricted recipient",
            "scope": "Named recipients only",
        }

        errors = validate_report_projection(audit, report, self.theme)

        self.assertTrue(any("restricted target requires authorization" in error for error in errors))
        self.assertTrue(any("redaction must be attested" in error for error in errors))
        self.assertTrue(any("review must be approved" in error for error in errors))
        self.assertTrue(any("publication must be separately approved" in error for error in errors))

    def test_every_projection_requires_redaction_review_and_publication_approval(self) -> None:
        report = copy.deepcopy(self.report)
        report["redaction"]["attested"] = False
        report["review"]["status"] = "pending"
        report["publication_approval"] = {
            "approved": False,
            "approved_by": "",
            "scope": "",
        }

        errors = validate_report_projection(self.audit, report, self.theme)

        self.assertTrue(any("report redaction must be attested" in error for error in errors))
        self.assertTrue(any("report review must be approved" in error for error in errors))
        self.assertTrue(any("report publication must be approved" in error for error in errors))
        self.assertTrue(any("publication approver is required" in error for error in errors))
        self.assertTrue(any("publication scope is required" in error for error in errors))

    def test_restricted_projection_binds_audience_and_scope_to_authorization(self) -> None:
        audit = copy.deepcopy(self.audit)
        report = copy.deepcopy(self.report)
        authorization_id = "authorization-recipient-review"
        audit["target"] = {
            "classification": "authorized-restricted",
            "authorization": {
                "authorization_id": authorization_id,
                "basis": "Owner-authorized evaluation",
                "scope": "One named-recipient report",
                "recipients": ["Named review team"],
                "publication_approved": True,
            },
        }
        audit["redaction"] = {"status": "complete", "reviewer": "Reviewer", "attested": True}
        for provenance in audit["provenance"]:
            provenance["classification"] = "authorized-restricted"
            provenance["authorization_id"] = authorization_id
        evidence_records = [
            evidence for finding in audit["findings"] for evidence in finding["evidence"]
        ] + [
            evidence for strength in audit["strengths"] for evidence in strength["evidence"]
        ]
        for evidence in evidence_records:
            evidence["classification"] = "authorized-restricted"
            evidence["authorization_id"] = authorization_id
        report["publication"] = "authorized-restricted"
        report["audience"] = "Public Internet"
        report["publication_approval"] = {
            "approved": True,
            "approved_by": "Authorized reviewer",
            "scope": "Unrelated public scope",
        }

        errors = validate_report_projection(audit, report, self.theme)

        self.assertTrue(any("audience must be an authorized recipient" in error for error in errors))
        self.assertTrue(any("scope must match audit authorization" in error for error in errors))

    def test_fully_authorized_restricted_projection_is_valid(self) -> None:
        audit = copy.deepcopy(self.audit)
        report = copy.deepcopy(self.report)
        authorization_id = "authorization-recipient-review"
        audit["target"] = {
            "classification": "authorized-restricted",
            "authorization": {
                "authorization_id": authorization_id,
                "basis": "Owner-authorized evaluation",
                "scope": "One recipient-facing report",
                "recipients": ["Named review team"],
                "publication_approved": True,
            },
        }
        audit["redaction"] = {
            "status": "complete",
            "reviewer": "Authorized reviewer",
            "attested": True,
        }
        for provenance in audit["provenance"]:
            provenance["classification"] = "authorized-restricted"
            provenance["authorization_id"] = authorization_id
        evidence_records = [
            evidence
            for finding in audit["findings"]
            for evidence in finding["evidence"]
        ] + [
            evidence
            for strength in audit["strengths"]
            for evidence in strength["evidence"]
        ]
        for evidence in evidence_records:
            evidence["classification"] = "authorized-restricted"
            evidence["authorization_id"] = authorization_id
        report["publication"] = "authorized-restricted"
        report["audience"] = "Named review team"
        report["publication_approval"] = {
            "approved": True,
            "approved_by": "Authorized reviewer",
            "scope": "One recipient-facing report",
        }

        self.assertEqual([], validate_audit_bundle(REPO_ROOT, audit))
        self.assertEqual([], validate_report_projection(audit, report, self.theme))

    def test_restricted_evidence_requires_matching_authorization(self) -> None:
        audit = copy.deepcopy(self.audit)
        authorization_id = "authorization-recipient-review"
        audit["target"] = {
            "classification": "authorized-restricted",
            "authorization": {
                "authorization_id": authorization_id,
                "basis": "Owner-authorized evaluation",
                "scope": "One recipient-facing report",
                "recipients": ["Named review team"],
                "publication_approved": True,
            },
        }
        audit["redaction"] = {"status": "complete", "reviewer": "Reviewer", "attested": True}
        audit["provenance"][0]["classification"] = "authorized-restricted"
        audit["provenance"][0]["authorization_id"] = authorization_id
        audit["findings"][0]["evidence"][0]["classification"] = "authorized-restricted"

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertTrue(any("restricted evidence requires target authorization" in error for error in errors))

    def test_lead_headlines_keys_must_exactly_match_leads_and_be_nonempty(self) -> None:
        report = copy.deepcopy(self.report)
        report["lead_headlines"] = {report["lead_findings"][0]: ""}

        errors = validate_report_projection(self.audit, report, self.theme)

        self.assertTrue(any("must match lead_findings exactly" in error for error in errors))
        self.assertTrue(any("headline must be nonempty" in error for error in errors))

    def test_strength_projection_uses_known_canonical_strength_ids(self) -> None:
        report = copy.deepcopy(self.report)
        report["strengths"] = ["s-unknown"]

        errors = validate_report_projection(self.audit, report, self.theme)

        self.assertTrue(any("unknown canonical strength" in error for error in errors))

    def test_privacy_paths_cover_unc_tilde_and_absolute_posix_but_allow_urls(self) -> None:
        unsafe = privacy_errors(
            {
                "unc": r"\\server\share\evidence.png",
                "tilde": "~/private/evidence.png",
                "posix": "/etc/private.conf",
                "public": "https://example.com/etc/private.conf",
            }
        )

        self.assertEqual(3, sum("absolute local path" in error for error in unsafe))
        self.assertFalse(any("public" in error for error in unsafe))

    def test_report_reference_to_unknown_finding_is_rejected(self) -> None:
        report = copy.deepcopy(self.report)
        report["lead_findings"] = ["f-does-not-exist"]
        errors = validate_report_projection(self.audit, report, self.theme)
        self.assertIn("report.lead_findings[0]: unknown canonical finding", errors)

    def test_public_projection_rejects_windows_home_path(self) -> None:
        report = copy.deepcopy(self.report)
        report["cover"]["statement"] = r"Evidence saved at C:\\Users\\person\\private.txt"
        errors = validate_report_projection(self.audit, report, self.theme)
        self.assertTrue(any("absolute local path" in error for error in errors))

    def test_public_projection_rejects_posix_home_path(self) -> None:
        report = copy.deepcopy(self.report)
        report["cover"]["statement"] = "Evidence saved at /home/person/private.txt"
        errors = validate_report_projection(self.audit, report, self.theme)
        self.assertTrue(any("absolute local path" in error for error in errors))

    def test_public_projection_rejects_secret_shaped_values_and_email_addresses(self) -> None:
        report = copy.deepcopy(self.report)
        report["cover"]["statement"] = "Use token=abc123456789 and analyst@example.com."
        errors = validate_report_projection(self.audit, report, self.theme)
        self.assertTrue(any("credential-shaped assignment" in error for error in errors))
        self.assertTrue(any("email address" in error for error in errors))
        self.assertFalse(any("abc123456789" in error for error in errors))

    def test_public_projection_rejects_private_ip_urls(self) -> None:
        report = copy.deepcopy(self.report)
        report["cover"]["statement"] = (
            "Synthetic links: http://127.0.0.1/x http://10.0.0.1/x "
            "http://169.254.1.1/x http://0.0.0.0/x http://[::1]/x "
            "http://localhost/x http://sample.internal/x"
        )
        errors = validate_report_projection(self.audit, report, self.theme)
        self.assertTrue(any("private or local URL" in error for error in errors))
        self.assertFalse(any("127.0.0.1" in error for error in errors))

    def test_public_projection_rejects_normalized_private_hosts(self) -> None:
        report = copy.deepcopy(self.report)
        report["cover"]["statement"] = (
            "Synthetic links: http://127.1/x http://2130706433/x http://localhost./x"
        )
        errors = validate_report_projection(self.audit, report, self.theme)
        self.assertTrue(any("private or local URL" in error for error in errors))
        self.assertFalse(any("2130706433" in error for error in errors))

    def test_public_projection_allows_public_hostname(self) -> None:
        report = copy.deepcopy(self.report)
        report["cover"]["statement"] = "Read the synthetic guide at https://sample-platform.example/help."
        self.assertEqual([], validate_report_projection(self.audit, report, self.theme))

    def test_malformed_report_theme_returns_errors(self) -> None:
        report = copy.deepcopy(self.report)
        report["theme"] = None
        errors = validate_report_projection(self.audit, report, self.theme)
        self.assertTrue(any("report.theme: expected object" in error for error in errors))

    def test_platform_accent_merges_to_a_full_valid_theme(self) -> None:
        merged = merge_platform_accent(self.theme, self.accent)
        self.assertEqual(self.accent["accent"], merged["accent"])
        self.assertEqual(self.theme["typography"], merged["typography"])
        self.assertEqual(self.theme["spacing"], merged["spacing"])
        self.assertEqual(self.theme["page"], merged["page"])
        self.assertEqual(self.theme["page"]["grid"], merged["page"]["grid"])
        self.assertEqual(self.theme["attribution"], merged["attribution"])
        self.assertEqual([], validate_report_projection(self.audit, self.report, merged))

    def test_incomplete_platform_accent_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "platform accent failed schema validation"):
            merge_platform_accent(self.theme, {"accent": "#000000"})

    def test_generated_report_adapter_rejects_unimplemented_logo_and_motif_fields(self) -> None:
        for field in ("logo", "motif"):
            adapter = copy.deepcopy(self.accent)
            adapter[field] = "unimplemented"
            with self.assertRaisesRegex(ValueError, "platform accent contains an unapproved key"):
                merge_platform_accent(self.theme, adapter)

    def test_unapproved_screenshot_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"][0]["evidence"][0]["type"] = "screenshot"
        audit["findings"][0]["evidence"][0].pop("publication_approved")
        audit["findings"][0]["evidence"][0].pop("alt", None)
        errors = validate_audit_bundle(REPO_ROOT, audit)
        self.assertTrue(any("unapproved screenshot" in error for error in errors))

    def test_report_reference_to_unknown_gap_is_rejected(self) -> None:
        report = copy.deepcopy(self.report)
        report["appendix"]["gap_ids"] = ["g-does-not-exist"]
        errors = validate_report_projection(self.audit, report, self.theme)
        self.assertTrue(any("unknown audit gap ID" in error for error in errors))

    def test_report_reference_to_unknown_not_assessed_id_is_rejected(self) -> None:
        report = copy.deepcopy(self.report)
        report["appendix"]["not_assessed_ids"] = ["na-does-not-exist"]
        errors = validate_report_projection(self.audit, report, self.theme)
        self.assertTrue(any("unknown audit not-assessed ID" in error for error in errors))

    def test_duplicate_gap_id_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["gaps"] = audit["gaps"] + [{"gap_id": "g-synthetic-recovery", "summary": "A distinct synthetic gap."}]
        errors = validate_audit_bundle(REPO_ROOT, audit)
        self.assertTrue(any("duplicate gap_id" in error for error in errors))

    def test_duplicate_not_assessed_id_is_rejected(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["not_assessed"] = audit["not_assessed"] + [
            {
                "not_assessed_id": "na-tint-on-tint-trap",
                "check_id": "alternate-small-screen-comparison",
                "blocker": "A distinct synthetic blocker.",
                "probe": "Use another synthetic render.",
                "escalation_required": False,
            }
        ]
        errors = validate_audit_bundle(REPO_ROOT, audit)
        self.assertTrue(any("duplicate not_assessed_id" in error for error in errors))

    def test_duplicate_finding_id_is_rejected_before_rendering_lookup(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"] = [
            audit["findings"][1],
            audit["findings"][0],
            copy.deepcopy(audit["findings"][0]),
        ]

        errors = validate_audit_bundle(REPO_ROOT, audit)

        self.assertIn("audit.findings[2].finding_id: duplicate finding_id", errors)


if __name__ == "__main__":
    unittest.main()
