"""Render a recipient-safe Punchlist report as deterministic standalone HTML."""

from __future__ import annotations

import argparse
from html import escape
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.report_model import (
    computed_counts,
    load_document,
    merge_platform_accent,
    validate_audit_bundle,
    validate_report_projection,
)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "report" / "report.html"
CSS_PATH = ROOT / "templates" / "report" / "report.css"
DEFAULT_THEME_PATH = ROOT / "themes" / "punchlist-default.json"
TEMPLATE_PLACEHOLDERS = {"{{DOCUMENT_TITLE}}", "{{ROOT_TOKENS}}", "{{REPORT_CSS}}", "{{REPORT_BODY}}"}
TEMPLATE_MARKER = re.compile(r"{{[^{}]+}}")


def _text(value: Any) -> str:
    """Escape a scalar for text or quoted-attribute HTML contexts."""
    return escape(str(value), quote=True)


def _css_string(value: Any) -> str:
    """Return a CSS string token without allowing declaration injection."""
    return json.dumps(str(value), ensure_ascii=False)


def _hex_luminance(value: str) -> float:
    channels = [int(value[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    brighter, darker = sorted((_hex_luminance(first), _hex_luminance(second)), reverse=True)
    return (brighter + 0.05) / (darker + 0.05)


def _assert_theme_contrast(theme: dict[str, Any]) -> None:
    pairs = (
        (theme["accent"], theme["colors"]["canvas"]),
        (theme["evidence_label"], theme["evidence_background"]),
        (theme["colors"]["ink"], theme["evidence_background"]),
    )
    if any(_contrast(first, second) < 4.5 for first, second in pairs):
        raise ValueError("theme: platform accent has insufficient contrast")


def _public_https_url(value: Any) -> str:
    if not isinstance(value, str) or any(character.isspace() for character in value):
        raise ValueError("theme: platform source must be a public HTTPS URL")
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        raise ValueError("theme: platform source must be a public HTTPS URL") from None
    if parsed.scheme.lower() != "https" or not hostname or parsed.username or parsed.password:
        raise ValueError("theme: platform source must be a public HTTPS URL")
    host = hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".local", ".internal")):
        raise ValueError("theme: platform source must be a public HTTPS URL")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return value
    if address.is_private or address.is_loopback or address.is_unspecified or address.is_link_local:
        raise ValueError("theme: platform source must be a public HTTPS URL")
    return value


def _sorted_findings(audit: dict[str, Any]) -> list[dict[str, Any]]:
    findings = audit.get("findings", [])
    records = [finding for finding in findings if isinstance(finding, dict)] if isinstance(findings, list) else []
    return sorted(records, key=lambda finding: (-float(finding.get("severity", 0)), str(finding.get("finding_id", ""))))


def _records_by_id(audit: dict[str, Any], field: str, collection: str) -> dict[str, dict[str, Any]]:
    records = audit.get(collection, [])
    if not isinstance(records, list):
        return {}
    return {
        record[field]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get(field), str)
    }


def _canonical_finding_records(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        finding["finding_id"]: finding
        for finding in _sorted_findings(audit)
        if isinstance(finding.get("finding_id"), str)
    }


def _ids(records: dict[str, dict[str, Any]], identifiers: Any) -> list[dict[str, Any]]:
    if not isinstance(identifiers, list):
        return []
    return [records[identifier] for identifier in identifiers if identifier in records]


def _root_tokens(theme: dict[str, Any]) -> str:
    colors = theme["colors"]
    typography = theme["typography"]
    spacing = theme["spacing"]
    page = theme["page"]
    grid = page["grid"]
    tokens = [
        ("--color-canvas", colors["canvas"]),
        ("--color-ink", colors["ink"]),
        ("--color-muted", colors["muted"]),
        ("--color-accent", theme["accent"]),
        ("--color-supporting", theme["supporting"]),
        ("--color-evidence-background", theme["evidence_background"]),
        ("--color-evidence-label", theme["evidence_label"]),
        ("--font-display", f"{typography['display_family']}, Georgia, serif"),
        ("--font-body", f"{typography['body_family']}, Arial, sans-serif"),
        ("--report-footer", _css_string(f"{theme['platform_name']} · {theme['attribution']['label']}")),
    ]
    tokens.extend((f"--space-{index}", f"{value}px") for index, value in enumerate(spacing, start=1))
    tokens.extend(
        [
            ("--page-margin", f"{page['margin']}px"),
            ("--page-columns", grid["columns"]),
            ("--page-gutter", f"{grid['gutter']}px"),
        ]
    )
    return "\n".join(f"  {name}: {value};" for name, value in tokens)


def _section(name: str, content: str) -> str:
    return f'<article class="report-page" data-section="{name}">{content}</article>'


def _render_cover(audit: dict[str, Any], report: dict[str, Any], theme: dict[str, Any]) -> str:
    cover = report["cover"]
    brief = audit["brief"]
    verified_methods = sorted(
        {
            str(finding.get("verified_how"))
            for finding in audit.get("findings", [])
            if isinstance(finding, dict) and finding.get("verified_how")
        }
    )
    supported_inputs = audit.get("capabilities", {}).get("supported_inputs", [])
    evidence_scope = ", ".join(str(value) for value in supported_inputs) if isinstance(supported_inputs, list) else "Declared evidence"
    method = ", ".join(verified_methods) or "Declared review protocol"
    audit_date = str(audit["created_at"]).split("T", 1)[0]
    platform_reference = ""
    if theme.get("source_url") is not None:
        source_url = _public_https_url(theme["source_url"])
        platform_reference = f'<p class="platform-reference"><a href="{_text(source_url)}">Platform design reference</a></p>'
    return _section(
        "cover",
        """<div class="cover-grid"><div><p class="eyebrow">Independent experience review</p>"""
        f"<h1>{_text(cover['statement'])}</h1><p class=\"task\">{_text(cover['task'])}</p>"
        f"</div><div><p class=\"eyebrow\">Prepared for</p><p>{_text(report['audience'])}</p>"
        f"<p class=\"metadata\">{_text(theme['platform_name'])} · {_text(report['publication'])} · {_text(audit_date)}</p>{platform_reference}"
        f"</div></div><dl class=\"cover-facts\"><div><dt>User</dt><dd>{_text(brief['user'])}</dd></div>"
        f"<div><dt>Context</dt><dd>{_text(brief['state'])} · {_text(brief['device'])} · {_text(brief['profile'])}</dd></div>"
        f"<div><dt>Entry point</dt><dd>{_text(brief['entry_point'])}</dd></div>"
        f"<div><dt>Method</dt><dd>{_text(method)}</dd></div>"
        f"<div><dt>Evidence scope</dt><dd>{_text(evidence_scope)}</dd></div>"
        f"<div><dt>Severity basis</dt><dd>{_text(brief['severity_basis'])}</dd></div></dl>"
        f'<p class="byline">{_text(theme["attribution"]["label"])}</p>'
        f"<p class=\"metadata\">{_text(report['report_id'])}</p>",
    )


def _render_journey(report: dict[str, Any]) -> str:
    moments = "".join(
        f'<li class="journey-item"><span class="journey-step">{index:02d} · {_text(moment["moment_id"])}</span><p>{_text(moment["summary"])}</p></li>'
        for index, moment in enumerate(report["journey"], start=1)
    )
    return _section("journey", f"<p class=\"eyebrow\">Journey</p><h2>From arrival to action</h2><ol class=\"journey-list\">{moments}</ol>")


def _render_evidence(finding: dict[str, Any]) -> str:
    evidence = finding.get("evidence", [])
    if not isinstance(evidence, list):
        return ""
    fragments: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        label = f"{_text(item.get('verified_how', 'declared'))} evidence note"
        details = [item.get("type"), item.get("classification"), item.get("provenance_id")]
        metadata = " · ".join(_text(detail) for detail in details if isinstance(detail, str) and detail)
        alt = item.get("alt")
        alt_note = f'<p class="evidence-alt">Description: {_text(alt)}</p>' if isinstance(alt, str) and alt.strip() else ""
        fragments.append(
            f'<aside class="evidence-summary"><p class="evidence-label">{label}</p>'
            f'<p>{_text(item.get("summary", ""))}</p>'
            f'{alt_note}<p class="evidence-meta">{metadata}</p></aside>'
        )
    return "".join(fragments)


def _render_lead_findings(audit: dict[str, Any], report: dict[str, Any], findings: dict[str, dict[str, Any]]) -> str:
    headlines = report["lead_headlines"]
    cards = "".join(
        f'<li class="finding-card"><div class="finding-heading"><h3>{_text(headlines[finding["finding_id"]])}</h3>'
        f'<span class="finding-id">{_text(finding["finding_id"])}</span></div>'
        f'<p>{_text(finding["symptom"])}</p><p><strong>{_text(finding["defect"])}</strong> · {_text(finding["surface"] if isinstance(finding["surface"], str) else "{} → {}".format(finding["surface"]["a"], finding["surface"]["b"]))}</p>'
        f"{_render_evidence(finding)}</li>"
        for finding in _ids(findings, report["lead_findings"])
    )
    counts = "".join(f"<dt>{_text(defect)}</dt><dd>{count}</dd>" for defect, count in computed_counts(audit).items())
    return _section("lead-findings", f"<p class=\"eyebrow\">Lead findings</p><h2>What most affects the journey</h2><ol class=\"finding-list\">{cards}</ol><dl class=\"count-list\">{counts}</dl>")


def _render_strengths(audit: dict[str, Any], report: dict[str, Any]) -> str:
    records = _records_by_id(audit, "strength_id", "strengths")
    summaries: list[str] = []
    for value in report["strengths"]:
        if isinstance(value, str) and value in records:
            summaries.append(str(records[value].get("summary", value)))
        elif isinstance(value, str):
            summaries.append(value)
        elif isinstance(value, dict) and isinstance(value.get("summary"), str):
            summaries.append(value["summary"])
    strengths = "".join(f"<li>{_text(summary)}</li>" for summary in summaries)
    return _section("strengths", f"<p class=\"eyebrow\">Strengths</p><h2>What supports progress</h2><ul class=\"strength-list\">{strengths}</ul>")


def _render_recommendations(report: dict[str, Any], findings: dict[str, dict[str, Any]]) -> str:
    recommendations = "".join(
        f'<li class="recommendation"><p class="recommendation-label">{_text(recommendation["recommendation_id"])} · {_text(", ".join(finding["defect"] for finding in _ids(findings, recommendation["canonical_ids"])))}</p>'
        f'<p>{_text(recommendation["summary"])}</p></li>'
        for recommendation in report["recommendations"]
    )
    next_test = report["next_test"]
    linked_defects = ", ".join(finding["defect"] for finding in _ids(findings, next_test["canonical_ids"]))
    return _section(
        "recommendations",
        f"<p class=\"eyebrow\">Recommendations</p><h2>Make the next comparison easier</h2><ol class=\"recommendation-list\">{recommendations}</ol>"
        f"<div class=\"next-test\"><p class=\"eyebrow\">Next test</p><p>{_text(next_test['summary'])}</p><p class=\"metadata\">Covers: {_text(linked_defects)}</p></div>",
    )


def _taxonomy_records(root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for category in ("interface", "content", "behavior"):
        try:
            values = json.loads((root / "taxonomy" / f"{category}.json").read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        for value in values if isinstance(values, list) else []:
            if isinstance(value, dict) and isinstance(value.get("id"), str):
                records[value["id"]] = value
    return records


def _reference_labels(finding: dict[str, Any], taxonomy: dict[str, Any]) -> list[str]:
    refs = finding.get("refs", taxonomy.get("refs", {}))
    values: list[Any] = []
    if isinstance(refs, dict):
        for key in sorted(refs):
            if isinstance(refs[key], list):
                values.extend(refs[key])
    elif isinstance(refs, list):
        values.extend(refs)
    labels: list[str] = []
    for value in values:
        if isinstance(value, dict):
            label = value.get("citation") or value.get("source_id")
            if isinstance(label, str):
                labels.append(label)
        elif isinstance(value, str):
            labels.append(value)
    return labels


def _appendix_finding(finding: dict[str, Any], taxonomy: dict[str, Any]) -> str:
    standard = finding.get("standard") or taxonomy.get("standard") or "Not declared"
    references = _reference_labels(finding, taxonomy)
    reference_text = "; ".join(references) if references else "No external reference declared"
    surface = finding["surface"] if isinstance(finding["surface"], str) else f'{finding["surface"]["a"]} → {finding["surface"]["b"]}'
    evidence = "".join(
        f'<li><span class="evidence-label">{_text(item.get("verified_how", finding.get("verified_how", "declared")))}</span>: '
        f'{_text(item.get("summary", ""))} <span class="evidence-meta">{_text(item.get("source", item.get("provenance_id", "source not declared")))}</span></li>'
        for item in finding.get("evidence", [])
        if isinstance(item, dict)
    )
    return (
        f'<li class="appendix-item"><div class="finding-heading"><h3>{_text(finding["defect"])}</h3>'
        f'<span class="finding-id">{_text(finding["finding_id"])}</span></div>'
        f'<dl class="trace-list"><div><dt>Symptom</dt><dd>{_text(finding["symptom"])}</dd></div>'
        f'<div><dt>Surface</dt><dd>{_text(surface)}</dd></div><div><dt>Locator</dt><dd>{_text(finding["locator"])}</dd></div>'
        f'<div><dt>Verified</dt><dd>{_text(finding.get("verified_how", "declared"))}</dd></div>'
        f'<div><dt>Standard</dt><dd>{_text(standard)}</dd></div><div><dt>References</dt><dd>{_text(reference_text)}</dd></div></dl>'
        f'<p class="evidence-label">Evidence</p><ul class="evidence-list">{evidence}</ul></li>'
    )


def _render_appendix(report: dict[str, Any], findings: dict[str, dict[str, Any]], gaps: dict[str, dict[str, Any]], not_assessed: dict[str, dict[str, Any]], taxonomy: dict[str, dict[str, Any]]) -> str:
    appendix = report["appendix"]
    finding_items = "".join(_appendix_finding(finding, taxonomy.get(finding["defect"], {})) for finding in _ids(findings, appendix["finding_ids"]))
    gap_items = "".join(f'<li class="appendix-item"><h3>{_text(gap["gap_id"])}</h3><p>{_text(gap["summary"])}</p></li>' for gap in _ids(gaps, appendix["gap_ids"]))
    unassessed_items = "".join(f'<li class="appendix-item"><h3>{_text(record["check_id"])}</h3><p>{_text(record["blocker"])}</p><p>{_text(record["probe"])}</p></li>' for record in _ids(not_assessed, appendix["not_assessed_ids"]))
    return _section(
        "appendix",
        f"<p class=\"eyebrow\">Appendix</p><h2>Canonical records and limits</h2>"
        f"<section class=\"appendix-group\"><h3>Findings</h3><ul class=\"appendix-list\">{finding_items}</ul></section>"
        f"<section class=\"appendix-group\"><h3>Evidence gaps</h3><ul class=\"appendix-list\">{gap_items}</ul></section>"
        f"<section class=\"appendix-group\"><h3>Not assessed</h3><ul class=\"appendix-list\">{unassessed_items}</ul></section>",
    )


def render_report(
    audit: dict[str, Any],
    report: dict[str, Any],
    theme: dict[str, Any],
    repository_root: Path | None = None,
) -> str:
    """Return a deterministic, escaped HTML rendering of a valid report projection."""
    root = (repository_root or ROOT).resolve()
    normalized_audit = dict(audit)
    normalized_audit["findings"] = _sorted_findings(audit)
    errors = validate_audit_bundle(root, normalized_audit)
    errors.extend(validate_report_projection(normalized_audit, report, theme, root))
    errors = list(dict.fromkeys(errors))
    if errors:
        raise ValueError("\n".join(errors))
    findings = _canonical_finding_records(normalized_audit)
    gaps = _records_by_id(normalized_audit, "gap_id", "gaps")
    not_assessed = _records_by_id(normalized_audit, "not_assessed_id", "not_assessed")
    taxonomy = _taxonomy_records(root)
    body = "\n".join(
        (
            _render_cover(normalized_audit, report, theme),
            _render_journey(report),
            _render_lead_findings(normalized_audit, report, findings),
            _render_strengths(normalized_audit, report),
            _render_recommendations(report, findings),
            _render_appendix(report, findings, gaps, not_assessed, taxonomy),
        )
    )
    template = (root / "templates" / "report" / "report.html").read_text(encoding="utf-8")
    if (
        set(TEMPLATE_MARKER.findall(template)) != TEMPLATE_PLACEHOLDERS
        or template.count("{{") != len(TEMPLATE_PLACEHOLDERS)
        or template.count("}}") != len(TEMPLATE_PLACEHOLDERS)
    ):
        raise ValueError("template: unexpected placeholder")
    css = (root / "templates" / "report" / "report.css").read_text(encoding="utf-8")
    replacements = {
        "{{DOCUMENT_TITLE}}": _text(f"{theme['platform_name']} experience review"),
        "{{ROOT_TOKENS}}": _root_tokens(theme),
        "{{REPORT_CSS}}": css,
        "{{REPORT_BODY}}": body,
    }
    return TEMPLATE_MARKER.sub(lambda match: replacements[match.group()], template)


def _location_only(errors: list[str]) -> str:
    return "\n".join(error.rsplit(" ", 1)[0] if "unknown canonical finding " in error else error for error in errors)


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("invalid command")


def _same_existing_file(output_path: Path, source_path: Path) -> bool:
    try:
        return output_path.exists() and source_path.exists() and output_path.samefile(source_path)
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = _SafeArgumentParser(description="Render a recipient-safe Punchlist HTML report.")
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--theme", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    try:
        arguments = parser.parse_args(argv)
    except ValueError:
        print("arguments: invalid command", file=sys.stderr)
        return 1
    audit_path = arguments.audit.resolve()
    report_path = arguments.report.resolve()
    theme_path = DEFAULT_THEME_PATH.resolve()
    adapter_path = arguments.theme.resolve() if arguments.theme else None
    if arguments.output.is_symlink():
        print("output: existing symlink is not allowed", file=sys.stderr)
        return 1
    output_path = arguments.output.resolve()
    inputs = tuple(path for path in (audit_path, report_path, theme_path, adapter_path) if path is not None)
    if output_path in inputs or any(
        _same_existing_file(output_path, source_path)
        for source_path in inputs
    ):
        print("output: must not alias an input", file=sys.stderr)
        return 1
    try:
        audit = load_document(audit_path)
    except ValueError:
        print("audit: could not load JSON", file=sys.stderr)
        return 1
    try:
        report = load_document(report_path)
    except ValueError:
        print("report: could not load JSON", file=sys.stderr)
        return 1
    try:
        theme = load_document(theme_path)
    except ValueError:
        print("theme: could not load JSON", file=sys.stderr)
        return 1
    if adapter_path is not None:
        try:
            adapter = load_document(adapter_path)
            theme = merge_platform_accent(theme, adapter)
        except ValueError:
            print("theme: invalid platform accent", file=sys.stderr)
            return 1
    try:
        _assert_theme_contrast(theme)
    except (KeyError, TypeError, ValueError):
        print("theme: platform accent has insufficient contrast", file=sys.stderr)
        return 1
    try:
        html = render_report(audit, report, theme)
        output_path.parent.mkdir(parents=False, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", delete=False,
            dir=output_path.parent, prefix=f".{output_path.name}.", suffix=".tmp",
        ) as temporary:
            temporary.write(html)
            temporary_path = Path(temporary.name)
        if arguments.output.is_symlink() or any(_same_existing_file(output_path, source_path) for source_path in inputs):
            temporary_path.unlink(missing_ok=True)
            print("output: must not alias an input", file=sys.stderr)
            return 1
        os.replace(temporary_path, output_path)
    except (OSError, ValueError) as error:
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)
        print("output: could not render report" if isinstance(error, OSError) else str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
