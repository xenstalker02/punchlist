"""Canonical validation and normalization for Punchlist audit reports."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scripts.validate import validate_schema


APPROVED_PLATFORM_ADAPTER_KEYS = {
    "platform_name",
    "accent",
    "supporting",
    "evidence_background",
    "evidence_label",
}
APPROVED_PLATFORM_ACCENT_KEYS = APPROVED_PLATFORM_ADAPTER_KEYS | {"source_url"}
SYNTHETIC_EMAIL_ALLOWLIST = {"sample.user@example.test", "synthetic@example.test"}
WINDOWS_PATH = re.compile(r"\b[A-Za-z]:\\+")
POSIX_HOME_PATH = re.compile(r"/(?:Users|home)/")
UNC_PATH = re.compile(r"(?<![A-Za-z0-9])\\\\[^\\\s]+\\[^\s]+")
TILDE_PATH = re.compile(r"(?<![A-Za-z0-9])~/(?:[^\s]+)")
ABSOLUTE_POSIX_PATH = re.compile(
    r"(?<![:/A-Za-z0-9~<])/(?!/)(?:[^/\s<>]+/[^\s<>]+|[^/\s<>]+\.[A-Za-z0-9]+)"
)
INVALID_BLOCKER = re.compile(
    r"\b(?:time\s+(?:limit|budget|ran\s+out)|timed?\s+out|deadline|token(?:s)?\s+(?:limit|budget|exhausted|remaining|constraint)|budget|not\s+completed|critic\s+scope)\b",
    re.IGNORECASE,
)
# Canonical verification methods map to the atomic capability needed to make
# that claim. Evidence types additionally require their own input capability.
VERIFICATION_CAPABILITY = {
    "screenshot": "screenshot",
    "rendered": "rendered",
    "source": "source",
    "interaction": "interaction",
    "content": "content-text",
}
EVIDENCE_TYPE_CAPABILITY = {
    "screenshot": "screenshot",
    "rendered": "rendered",
    "source": "source",
    "interaction": "interaction",
    "content": "content-text",
}
EVIDENCE_TYPE_VERIFICATION = {
    "screenshot": {"screenshot"},
    "rendered": {"rendered"},
    "source": {"source"},
    "interaction": {"interaction"},
    "content": {"content"},
}
CREDENTIAL_ASSIGNMENT = re.compile(
    r"\b(?:api[_-]?key|token|secret|password|passwd|authorization)\s*[:=]\s*[^\s,;]+",
    re.IGNORECASE,
)
EMAIL_ADDRESS = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
FILE_URL = re.compile(r"file://", re.IGNORECASE)
HTTP_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def load_document(path: Path) -> dict[str, Any]:
    """Load a JSON object, rejecting arrays and scalar documents."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.as_posix()}: could not load JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path.as_posix()}: expected a JSON object")
    return value


def canonical_surface(surface: str | dict[str, str]) -> str:
    """Normalize one surface or a directed a-to-b comparison surface."""
    if isinstance(surface, str):
        return _normalize_identity_text(surface)
    if isinstance(surface, dict) and set(surface) == {"a", "b"}:
        a, b = surface["a"], surface["b"]
        if isinstance(a, str) and isinstance(b, str):
            return f"{_normalize_identity_text(a)}|{_normalize_identity_text(b)}"
    raise ValueError("surface must be a string or an object with string a and b fields")


def merge_platform_accent(base_theme: dict[str, Any], accent: dict[str, Any]) -> dict[str, Any]:
    """Apply the bounded platform adapter while retaining the complete base theme."""
    if not isinstance(base_theme, dict) or not isinstance(accent, dict):
        raise ValueError("theme and platform accent must be objects")
    unapproved = sorted(set(accent) - APPROVED_PLATFORM_ACCENT_KEYS)
    if unapproved:
        raise ValueError("platform accent contains an unapproved key")
    root = Path(__file__).resolve().parents[1]
    if _schema_errors(root, base_theme, "theme.schema.json", "theme"):
        raise ValueError("base theme failed schema validation")
    if _schema_errors(root, accent, "theme.schema.json", "platform accent"):
        raise ValueError("platform accent failed schema validation")
    merged = dict(base_theme)
    for key in APPROVED_PLATFORM_ACCENT_KEYS:
        if key in accent:
            merged[key] = accent[key]
    return merged


def _canonical_fragment(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _normalize_identity_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def finding_fingerprint(finding: dict[str, Any]) -> str:
    """Return the stable full SHA-256 fingerprint for a canonical finding."""
    identity = {
        "defect": _normalize_identity_text(finding["defect"]),
        "surface": canonical_surface(finding["surface"]),
        "locator": _normalize_identity_text(finding["locator"]),
        "manifestation": finding.get("manifestation", "consistent"),
    }
    return hashlib.sha256(_canonical_fragment(identity).encode("ascii")).hexdigest()


def _load_schema(root: Path, filename: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        schema = load_document(root / "schema" / filename)
    except ValueError:
        return None, [f"schema/{filename}: could not load schema"]
    return schema, []


def _taxonomy_entries(root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    entries_by_id: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for category in ("interface", "content", "behavior"):
        path = root / "taxonomy" / f"{category}.json"
        try:
            entries = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            errors.append(f"taxonomy/{category}.json: could not load taxonomy")
            continue
        if not isinstance(entries, list):
            errors.append(f"taxonomy/{category}.json: expected an array")
            continue
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                entries_by_id[entry["id"]] = entry
    return entries_by_id, errors


def _taxonomy_ids(root: Path) -> tuple[set[str], list[str]]:
    entries, errors = _taxonomy_entries(root)
    return set(entries), errors


def _supported_input_vocabulary(entries: dict[str, dict[str, Any]]) -> set[str]:
    vocabulary: set[str] = set()
    for entry in entries.values():
        routes = entry.get("detectable_from", [])
        if isinstance(routes, list):
            for route in routes:
                if isinstance(route, str):
                    vocabulary.update(route.split("+"))
    return vocabulary


def _eligible_defect_ids(
    entries: dict[str, dict[str, Any]], supported_inputs: set[str]
) -> set[str]:
    eligible: set[str] = set()
    for defect_id, entry in entries.items():
        routes = entry.get("detectable_from", [])
        if not isinstance(routes, list):
            continue
        for route in routes:
            if isinstance(route, str) and set(route.split("+")).issubset(supported_inputs):
                eligible.add(defect_id)
                break
    return eligible


def _schema_errors(root: Path, value: dict[str, Any], filename: str, location: str) -> list[str]:
    schema, errors = _load_schema(root, filename)
    if schema is not None:
        errors.extend(validate_schema(value, schema, location))
    return errors


def _location_child(location: str, key: str | int) -> str:
    return f"{location}[{key}]" if isinstance(key, int) else f"{location}.{key}"


def _has_private_or_local_url(value: str) -> bool:
    if FILE_URL.search(value):
        return True
    for match in HTTP_URL.finditer(value):
        hostname = urlparse(match.group()).hostname
        if not hostname:
            continue
        host = hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".local", ".internal")):
            return True
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            try:
                address = ipaddress.IPv4Address(socket.inet_aton(host))
            except OSError:
                continue
        if address.is_private or address.is_loopback or address.is_unspecified or address.is_link_local:
            return True
    return False


def privacy_errors(value: Any, location: str = "document") -> list[str]:
    """Find recipient-unsafe strings without exposing the matched value."""
    errors: list[str] = []

    def visit(current: Any, current_location: str) -> None:
        if isinstance(current, str):
            without_urls = HTTP_URL.sub("", current).replace("~/.claude/skills/punchlist", "")
            if (
                WINDOWS_PATH.search(without_urls)
                or POSIX_HOME_PATH.search(without_urls)
                or UNC_PATH.search(without_urls)
                or TILDE_PATH.search(without_urls)
                or ABSOLUTE_POSIX_PATH.search(without_urls)
            ):
                errors.append(f"{current_location}: absolute local path")
            if CREDENTIAL_ASSIGNMENT.search(current):
                errors.append(f"{current_location}: credential-shaped assignment")
            if _has_private_or_local_url(current):
                errors.append(f"{current_location}: private or local URL")
            for email in EMAIL_ADDRESS.findall(current):
                if email.lower() not in SYNTHETIC_EMAIL_ALLOWLIST:
                    errors.append(f"{current_location}: email address")
                    break
            return
        if isinstance(current, list):
            for index, item in enumerate(current):
                visit(item, _location_child(current_location, index))
            return
        if isinstance(current, dict):
            if current.get("type") == "screenshot" or (
                current.get("verified_how") == "screenshot"
                and "publication_approved" in current
            ):
                if current.get("publication_approved") is not True or not isinstance(current.get("alt"), str) or not current["alt"].strip():
                    errors.append(f"{current_location}: unapproved screenshot evidence")
            for key, item in current.items():
                visit(item, _location_child(current_location, key))

    visit(value, location)
    return errors


def _final_findings(audit: dict[str, Any]) -> list[dict[str, Any]]:
    findings = audit.get("findings", [])
    if not isinstance(findings, list):
        return []
    final = [
        finding
        for finding in findings
        if isinstance(finding, dict)
        and finding.get("decision") == "confirmed"
        and isinstance(finding.get("severity"), (int, float))
        and not isinstance(finding.get("severity"), bool)
        and finding["severity"] > 0
        and finding.get("lifecycle") == "open"
    ]
    return sorted(final, key=lambda finding: (-finding["severity"], str(finding.get("finding_id", ""))))


def _duplicate_stable_id_errors(records: Any, field: str, location: str) -> list[str]:
    if not isinstance(records, list):
        return []
    errors: list[str] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not isinstance(record.get(field), str):
            continue
        identifier = record[field]
        if identifier in seen:
            errors.append(f"{location}[{index}].{field}: duplicate {field}")
        else:
            seen.add(identifier)
    return errors


def computed_counts(audit: dict[str, Any]) -> dict[str, int]:
    """Count confirmed primary defects only; aliases and report values never contribute."""
    counts = Counter(
        finding["defect"]
        for finding in _final_findings(audit)
        if isinstance(finding.get("defect"), str)
    )
    return dict(sorted(counts.items()))


def _verification_capability_errors(
    method: Any,
    supported_inputs: set[str],
    rendered_surface_proven_live: bool,
    location: str,
) -> list[str]:
    errors: list[str] = []
    required = VERIFICATION_CAPABILITY.get(method)
    if required is not None and required not in supported_inputs:
        errors.append(f"{location}: verification method is not supported by capabilities")
    if method == "rendered" and not rendered_surface_proven_live:
        errors.append(f"{location}: rendered verification requires a proven-live surface")
    return errors


def _evidence_capability_errors(
    evidence: dict[str, Any],
    supported_inputs: set[str],
    rendered_surface_proven_live: bool,
    location: str,
) -> list[str]:
    errors = _verification_capability_errors(
        evidence.get("verified_how"),
        supported_inputs,
        rendered_surface_proven_live,
        f"{location}.verified_how",
    )
    evidence_type = evidence.get("type")
    method = evidence.get("verified_how")
    allowed_methods = EVIDENCE_TYPE_VERIFICATION.get(evidence_type)
    if allowed_methods is not None and method not in allowed_methods:
        errors.append(f"{location}: evidence type is incompatible with verified_how")
    required = EVIDENCE_TYPE_CAPABILITY.get(evidence_type)
    if required is not None and required not in supported_inputs:
        errors.append(f"{location}.type: evidence type is not supported by capabilities")
    return errors


def validate_audit_bundle(root: Path, audit: dict[str, Any]) -> list[str]:
    """Validate an audit against schemas, taxonomy, lifecycle, and privacy rules."""
    errors = _schema_errors(root, audit, "audit.schema.json", "audit")
    taxonomy_entries, taxonomy_errors = _taxonomy_entries(root)
    taxonomy_ids = set(taxonomy_entries)
    errors.extend(taxonomy_errors)
    errors.extend(privacy_errors(audit, "audit"))
    errors.extend(_duplicate_stable_id_errors(audit.get("findings"), "finding_id", "audit.findings"))
    errors.extend(_duplicate_stable_id_errors(audit.get("gaps"), "gap_id", "audit.gaps"))
    errors.extend(
        _duplicate_stable_id_errors(
            audit.get("not_assessed"), "not_assessed_id", "audit.not_assessed"
        )
    )
    errors.extend(_duplicate_stable_id_errors(audit.get("provenance"), "provenance_id", "audit.provenance"))
    errors.extend(_duplicate_stable_id_errors(audit.get("strengths"), "strength_id", "audit.strengths"))
    errors.extend(_duplicate_stable_id_errors(audit.get("critics"), "critic_id", "audit.critics"))

    target = audit.get("target", {})
    target_classification = target.get("classification") if isinstance(target, dict) else None
    authorization = target.get("authorization") if isinstance(target, dict) else None
    if target_classification == "authorized-restricted":
        if not isinstance(authorization, dict):
            errors.append("audit.target: restricted target requires authorization")
        elif authorization.get("publication_approved") is not True:
            errors.append("audit.target.authorization: restricted publication must be approved")
        redaction = audit.get("redaction")
        if not isinstance(redaction, dict) or redaction.get("attested") is not True or redaction.get("status") != "complete":
            errors.append("audit.redaction: restricted audit redaction must be complete and attested")
    authorization_id = authorization.get("authorization_id") if isinstance(authorization, dict) else None
    provenance = audit.get("provenance", [])
    provenance_by_id = {
        item.get("provenance_id"): item
        for item in (provenance if isinstance(provenance, list) else [])
        if isinstance(item, dict) and isinstance(item.get("provenance_id"), str)
    }
    for index, record in enumerate(provenance if isinstance(provenance, list) else []):
        if not isinstance(record, dict):
            continue
        if record.get("publication_approved") is not True:
            errors.append(f"audit.provenance[{index}]: publication approval required")
        if record.get("classification") == "authorized-restricted":
            if not authorization_id or record.get("authorization_id") != authorization_id:
                errors.append(f"audit.provenance[{index}]: restricted provenance requires target authorization")

    capabilities = audit.get("capabilities", {})
    supported_inputs: set[str] = set()
    rendered_surface_proven_live = False
    if isinstance(capabilities, dict) and isinstance(capabilities.get("supported_inputs"), list):
        rendered_surface_proven_live = capabilities.get("rendered_surface_proven_live") is True
        vocabulary = _supported_input_vocabulary(taxonomy_entries)
        for index, supported_input in enumerate(capabilities["supported_inputs"]):
            if isinstance(supported_input, str):
                if supported_input not in vocabulary:
                    errors.append(f"audit.capabilities.supported_inputs[{index}]: unknown supported input")
                else:
                    supported_inputs.add(supported_input)
        if "rendered" in supported_inputs and not rendered_surface_proven_live:
            errors.append("audit.capabilities.rendered_surface_proven_live: rendered capability requires a proven-live surface")
    eligibility_inputs = set(supported_inputs)
    if "rendered" in eligibility_inputs:
        eligibility_inputs.add("screenshot")
    eligible_ids = _eligible_defect_ids(taxonomy_entries, eligibility_inputs)

    findings = audit.get("findings", [])
    if isinstance(findings, list):
        critic_ids = {
            critic.get("critic_id")
            for critic in audit.get("critics", [])
            if isinstance(critic, dict) and isinstance(critic.get("critic_id"), str)
        }
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                continue
            location = f"audit.findings[{index}]"
            defect = finding.get("defect")
            if defect not in taxonomy_ids:
                errors.append(f"{location}.defect: unknown defect")
            elif defect not in eligible_ids:
                errors.append(f"{location}.defect: outside supported eligibility")
            also_matches = finding.get("also_matches", [])
            if isinstance(also_matches, list):
                for alias_index, alias in enumerate(also_matches):
                    if alias not in taxonomy_ids:
                        errors.append(f"{location}.also_matches[{alias_index}]: unknown defect")
            if finding.get("severity") == 0:
                errors.append(f"{location}.severity: severity must be above zero")
            lifecycle = finding.get("lifecycle")
            resweep = finding.get("resweep")
            if lifecycle == "superseded":
                if not isinstance(resweep, dict) or not isinstance(resweep.get("superseded_by"), str) or not isinstance(resweep.get("evidence"), str):
                    errors.append(f"{location}.resweep: superseded finding requires superseded_by and evidence")
            elif lifecycle == "fixed":
                required_resweep = ("status", "verified_how", "verified_at", "verified_by", "evidence")
                if (
                    not isinstance(resweep, dict)
                    or resweep.get("status") != "verified-fixed"
                    or any(not isinstance(resweep.get(field), str) or not resweep[field].strip() for field in required_resweep[1:])
                ):
                    errors.append(f"{location}.resweep: fixed finding requires structured verification evidence")
                elif isinstance(resweep, dict):
                    errors.extend(
                        _verification_capability_errors(
                            resweep.get("verified_how"),
                            supported_inputs,
                            rendered_surface_proven_live,
                            f"{location}.resweep.verified_how",
                        )
                    )
            elif resweep is not None:
                errors.append(f"{location}.resweep: allowed only for a superseded finding")
            errors.extend(
                _verification_capability_errors(
                    finding.get("verified_how"),
                    supported_inputs,
                    rendered_surface_proven_live,
                    f"{location}.verified_how",
                )
            )
            votes = finding.get("severity_votes", [])
            if isinstance(votes, list):
                vote_ids = [vote.get("critic_id") for vote in votes if isinstance(vote, dict)]
                if len(vote_ids) != len(set(vote_ids)):
                    errors.append(f"{location}.severity_votes: duplicate critic vote")
                if set(vote_ids) != critic_ids or len(vote_ids) != len(critic_ids):
                    errors.append(f"{location}.severity_votes: must match declared critics exactly")
                severities = [
                    vote.get("severity") for vote in votes
                    if isinstance(vote, dict)
                    and isinstance(vote.get("severity"), (int, float))
                    and not isinstance(vote.get("severity"), bool)
                ]
                if any(severity == 0 for severity in severities):
                    errors.append(f"{location}.severity_votes: confirmed finding has a zero-vote veto")
                if severities and isinstance(finding.get("severity"), (int, float)):
                    expected_severity = sum(severities) / len(severities)
                    if abs(float(finding["severity"]) - expected_severity) > 1e-9:
                        errors.append(f"{location}.severity: must equal severity vote mean")
            evidence = finding.get("evidence", [])
            for evidence_index, item in enumerate(evidence if isinstance(evidence, list) else []):
                if not isinstance(item, dict):
                    continue
                evidence_location = f"{location}.evidence[{evidence_index}]"
                errors.extend(
                    _evidence_capability_errors(
                        item,
                        supported_inputs,
                        rendered_surface_proven_live,
                        evidence_location,
                    )
                )
                provenance_record = provenance_by_id.get(item.get("provenance_id"))
                if provenance_record is None:
                    errors.append(f"{evidence_location}.provenance_id: unknown provenance ID")
                elif item.get("classification") != provenance_record.get("classification"):
                    errors.append(f"{evidence_location}.classification: must match provenance classification")
                if item.get("publication_approved") is not True:
                    errors.append(f"{evidence_location}: publication approval required")
                if item.get("classification") == "authorized-restricted":
                    if not authorization_id or item.get("authorization_id") != authorization_id:
                        errors.append(f"{evidence_location}: restricted evidence requires target authorization")
            try:
                fingerprint = finding_fingerprint(finding)
            except (KeyError, ValueError):
                continue
            if finding.get("fingerprint") != fingerprint:
                errors.append(f"{location}.fingerprint: must match canonical fingerprint")
            expected_id = f"f-{fingerprint[:12]}"
            if finding.get("finding_id") != expected_id:
                errors.append(f"{location}.finding_id: must match canonical fingerprint id")

        findings_by_id = {
            finding.get("finding_id"): finding
            for finding in findings
            if isinstance(finding, dict) and isinstance(finding.get("finding_id"), str)
        }
        supersession_edges: dict[str, str] = {}
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict) or finding.get("lifecycle") != "superseded":
                continue
            resweep = finding.get("resweep")
            successor_id = resweep.get("superseded_by") if isinstance(resweep, dict) else None
            if isinstance(successor_id, str) and isinstance(finding.get("finding_id"), str):
                supersession_edges[finding["finding_id"]] = successor_id
            successor = findings_by_id.get(successor_id)
            if not isinstance(successor, dict) or successor.get("lifecycle") != "open":
                errors.append(f"audit.findings[{index}].resweep.superseded_by: must reference an existing current finding")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit_supersession(finding_id: str) -> bool:
            if finding_id in visiting:
                return True
            if finding_id in visited:
                return False
            visiting.add(finding_id)
            successor_id = supersession_edges.get(finding_id)
            cyclic = isinstance(successor_id, str) and visit_supersession(successor_id)
            visiting.remove(finding_id)
            visited.add(finding_id)
            return cyclic

        if any(visit_supersession(finding_id) for finding_id in supersession_edges):
            errors.append("audit.findings: supersession graph must be acyclic")

    ledger = audit.get("ledger", [])
    if isinstance(ledger, list):
        ledger_ids: set[str] = set()
        ledger_defects: set[str] = set()
        eligible_ledger_ids: set[str] = set()
        for index, item in enumerate(ledger):
            if not isinstance(item, dict):
                continue
            ledger_id = item.get("ledger_id")
            defect = item.get("defect")
            if isinstance(ledger_id, str):
                if ledger_id in ledger_ids:
                    errors.append(f"audit.ledger[{index}].ledger_id: duplicate ledger ID")
                ledger_ids.add(ledger_id)
            if isinstance(defect, str):
                if defect in ledger_defects:
                    errors.append(f"audit.ledger[{index}].defect: duplicate ledger defect")
                ledger_defects.add(defect)
                if defect not in taxonomy_ids:
                    errors.append(f"audit.ledger[{index}].defect: unknown defect")
                elif defect not in eligible_ids:
                    errors.append(f"audit.ledger[{index}].defect: ineligible ledger defect")
                elif isinstance(ledger_id, str):
                    eligible_ledger_ids.add(ledger_id)
            if item.get("disposition") == "found" and isinstance(defect, str):
                finding_defects = {
                    candidate_defect
                    for candidate in _final_findings(audit)
                    for candidate_defect in [candidate.get("defect"), *(candidate.get("also_matches", []) if isinstance(candidate.get("also_matches"), list) else [])]
                }
                if defect not in finding_defects:
                    errors.append(f"audit.ledger[{index}]: found row has no canonical finding")
            if item.get("disposition") == "not_assessed":
                not_assessed_ids = {
                    record.get("not_assessed_id")
                    for record in audit.get("not_assessed", [])
                    if isinstance(record, dict)
                }
                if item.get("not_assessed_id") not in not_assessed_ids:
                    errors.append(f"audit.ledger[{index}].not_assessed_id: must link a canonical not-assessed record")
                else:
                    linked = next(
                        (record for record in audit.get("not_assessed", []) if isinstance(record, dict) and record.get("not_assessed_id") == item.get("not_assessed_id")),
                        None,
                    )
                    if isinstance(linked, dict) and linked.get("check_id") != defect:
                        errors.append(f"audit.ledger[{index}].not_assessed_id: linked record must close the same defect")
        if ledger_defects != eligible_ids or len(ledger) != len(eligible_ids):
            errors.append("audit.ledger: incomplete eligible ledger")
        critics = audit.get("critics", [])
        assigned_ledger_ids: set[str] = set()
        if isinstance(critics, list):
            for critic_index, critic in enumerate(critics):
                if not isinstance(critic, dict) or not isinstance(critic.get("ledger_ids"), list):
                    continue
                for assignment_index, ledger_id in enumerate(critic["ledger_ids"]):
                    location = f"audit.critics[{critic_index}].ledger_ids[{assignment_index}]"
                    if ledger_id not in ledger_ids:
                        errors.append(f"{location}: unknown ledger ID")
                    elif isinstance(ledger_id, str):
                        assigned_ledger_ids.add(ledger_id)
        for index, item in enumerate(ledger):
            if isinstance(item, dict) and item.get("ledger_id") in eligible_ledger_ids:
                if item["ledger_id"] not in assigned_ledger_ids:
                    errors.append(f"audit.ledger[{index}]: unassigned eligible ledger row")
    for index, record in enumerate(audit.get("not_assessed", []) if isinstance(audit.get("not_assessed"), list) else []):
        if not isinstance(record, dict):
            continue
        if isinstance(record.get("blocker"), str) and INVALID_BLOCKER.search(record["blocker"]):
            errors.append(f"audit.not_assessed[{index}].blocker: invalid operational blocker")
        if record.get("escalation_required") is not True:
            errors.append(f"audit.not_assessed[{index}].escalation_required: must be true")
    for strength_index, strength in enumerate(audit.get("strengths", []) if isinstance(audit.get("strengths"), list) else []):
        if not isinstance(strength, dict):
            continue
        for evidence_index, item in enumerate(strength.get("evidence", []) if isinstance(strength.get("evidence"), list) else []):
            if not isinstance(item, dict):
                continue
            location = f"audit.strengths[{strength_index}].evidence[{evidence_index}]"
            errors.extend(
                _verification_capability_errors(
                    item.get("verified_how"),
                    supported_inputs,
                    rendered_surface_proven_live,
                    f"{location}.verified_how",
                )
            )
            provenance_record = provenance_by_id.get(item.get("provenance_id"))
            if provenance_record is None:
                errors.append(f"{location}.provenance_id: unknown provenance ID")
            elif item.get("classification") != provenance_record.get("classification"):
                errors.append(f"{location}.classification: must match provenance classification")
            if item.get("publication_approved") is not True:
                errors.append(f"{location}: publication approval required")
    return errors


def _report_references(report: dict[str, Any]) -> list[tuple[str, Any]]:
    references: list[tuple[str, Any]] = []
    lead_findings = report.get("lead_findings")
    for index, finding_id in enumerate(lead_findings if isinstance(lead_findings, list) else []):
        references.append((f"report.lead_findings[{index}]", finding_id))
    headlines = report.get("lead_headlines", {})
    if isinstance(headlines, dict):
        references.extend(
            (f"report.lead_headlines[{index}]", key)
            for index, key in enumerate(headlines)
        )
    recommendations = report.get("recommendations")
    for index, recommendation in enumerate(recommendations if isinstance(recommendations, list) else []):
        if isinstance(recommendation, dict):
            canonical_ids = recommendation.get("canonical_ids")
            for id_index, finding_id in enumerate(canonical_ids if isinstance(canonical_ids, list) else []):
                references.append((f"report.recommendations[{index}].canonical_ids[{id_index}]", finding_id))
    next_test = report.get("next_test", {})
    if isinstance(next_test, dict):
        canonical_ids = next_test.get("canonical_ids")
        for index, finding_id in enumerate(canonical_ids if isinstance(canonical_ids, list) else []):
            references.append((f"report.next_test.canonical_ids[{index}]", finding_id))
    appendix = report.get("appendix", {})
    if isinstance(appendix, dict):
        finding_ids = appendix.get("finding_ids")
        for index, finding_id in enumerate(finding_ids if isinstance(finding_ids, list) else []):
            references.append((f"report.appendix.finding_ids[{index}]", finding_id))
    return references


def validate_report_projection(
    audit: dict[str, Any], report: dict[str, Any], theme: dict[str, Any], root: Path | None = None
) -> list[str]:
    """Validate a recipient-facing projection against one canonical audit."""
    root = root or Path(__file__).resolve().parents[1]
    errors = _schema_errors(root, report, "report.schema.json", "report")
    errors.extend(_schema_errors(root, theme, "theme.schema.json", "theme"))
    if isinstance(audit, dict):
        errors.extend(validate_audit_bundle(root, audit))
    errors.extend(privacy_errors(audit, "audit"))
    errors.extend(privacy_errors(report, "report"))

    if not isinstance(audit, dict) or not isinstance(report, dict) or not isinstance(theme, dict):
        return errors

    if report.get("audit_id") != audit.get("audit_id"):
        errors.append("report.audit_id: must reference the canonical audit")
    report_redaction = report.get("redaction")
    report_review = report.get("review")
    report_approval = report.get("publication_approval")
    if not isinstance(report_redaction, dict) or report_redaction.get("attested") is not True:
        errors.append("report.redaction: report redaction must be attested")
    if not isinstance(report_review, dict) or report_review.get("status") != "approved":
        errors.append("report.review: report review must be approved")
    if not isinstance(report_approval, dict) or report_approval.get("approved") is not True:
        errors.append("report.publication_approval: report publication must be approved")
    if not isinstance(report_approval, dict) or not isinstance(report_approval.get("approved_by"), str) or not report_approval["approved_by"].strip():
        errors.append("report.publication_approval.approved_by: publication approver is required")
    if not isinstance(report_approval, dict) or not isinstance(report_approval.get("scope"), str) or not report_approval["scope"].strip():
        errors.append("report.publication_approval.scope: publication scope is required")
    target = audit.get("target", {})
    if isinstance(target, dict) and report.get("publication") != target.get("classification"):
        errors.append("report.publication: must match audit target classification")
    if isinstance(target, dict) and target.get("classification") == "authorized-restricted":
        authorization = target.get("authorization")
        if not isinstance(authorization, dict):
            errors.append("audit.target: restricted target requires authorization")
        elif authorization.get("publication_approved") is not True:
            errors.append("audit.target.authorization: restricted publication must be approved")
        if not isinstance(report_redaction, dict) or report_redaction.get("attested") is not True:
            errors.append("report.redaction: restricted report redaction must be attested")
        if not isinstance(report_review, dict) or report_review.get("status") != "approved":
            errors.append("report.review: restricted report review must be approved")
        if not isinstance(report_approval, dict) or report_approval.get("approved") is not True:
            errors.append("report.publication_approval: restricted publication must be separately approved")
        if isinstance(authorization, dict):
            recipients = authorization.get("recipients")
            if not isinstance(recipients, list) or report.get("audience") not in recipients:
                errors.append("report.audience: audience must be an authorized recipient")
            if report_approval is None or not isinstance(report_approval, dict) or report_approval.get("scope") != authorization.get("scope"):
                errors.append("report.publication_approval.scope: scope must match audit authorization")
    report_theme = report.get("theme") if isinstance(report.get("theme"), dict) else {}
    if report_theme.get("theme_id") != theme.get("theme_id"):
        errors.append("report.theme.theme_id: must match supplied theme")
    if "counts" in report:
        errors.append("report.counts: counts must be derived from canonical findings")

    canonical_ids = {finding.get("finding_id") for finding in _final_findings(audit)}
    lead_ids = report.get("lead_findings", [])
    headlines = report.get("lead_headlines", {})
    if isinstance(lead_ids, list) and isinstance(headlines, dict):
        if set(headlines) != set(lead_ids) or len(headlines) != len(lead_ids):
            errors.append("report.lead_headlines: keys must match lead_findings exactly")
        for index, headline in enumerate(headlines.values()):
            if not isinstance(headline, str) or not headline.strip():
                errors.append(f"report.lead_headlines[{index}]: headline must be nonempty")
    for location, finding_id in _report_references(report):
        if finding_id not in canonical_ids:
            errors.append(f"{location}: unknown canonical finding")
    appendix = report.get("appendix", {})
    if isinstance(appendix, dict) and isinstance(appendix.get("finding_ids"), list):
        if set(appendix["finding_ids"]) != canonical_ids:
            errors.append("report.appendix.finding_ids: must include every canonical finding")
    gaps = audit.get("gaps")
    audit_gap_ids = {
        gap.get("gap_id")
        for gap in (gaps if isinstance(gaps, list) else [])
        if isinstance(gap, dict) and isinstance(gap.get("gap_id"), str)
    }
    not_assessed = audit.get("not_assessed")
    audit_not_assessed_ids = {
        record.get("not_assessed_id")
        for record in (not_assessed if isinstance(not_assessed, list) else [])
        if isinstance(record, dict) and isinstance(record.get("not_assessed_id"), str)
    }
    duplicate_gap_errors = _duplicate_stable_id_errors(gaps, "gap_id", "audit.gaps")
    duplicate_not_assessed_errors = _duplicate_stable_id_errors(
        not_assessed, "not_assessed_id", "audit.not_assessed"
    )
    errors.extend(duplicate_gap_errors)
    errors.extend(duplicate_not_assessed_errors)
    if isinstance(appendix, dict):
        gap_ids = appendix.get("gap_ids")
        if isinstance(gap_ids, list):
            for index, gap_id in enumerate(gap_ids):
                if gap_id not in audit_gap_ids:
                    errors.append(f"report.appendix.gap_ids[{index}]: unknown audit gap ID")
            if set(gap_ids) != audit_gap_ids:
                errors.append("report.appendix.gap_ids: must include every audit gap")
            if duplicate_gap_errors:
                errors.append("report.appendix.gap_ids: audit gap IDs are ambiguous")
        not_assessed_ids = appendix.get("not_assessed_ids")
        if isinstance(not_assessed_ids, list):
            for index, record_id in enumerate(not_assessed_ids):
                if record_id not in audit_not_assessed_ids:
                    errors.append(f"report.appendix.not_assessed_ids[{index}]: unknown audit not-assessed ID")
            if set(not_assessed_ids) != audit_not_assessed_ids:
                errors.append("report.appendix.not_assessed_ids: must include every audit not-assessed record")
            if duplicate_not_assessed_errors:
                errors.append("report.appendix.not_assessed_ids: audit not-assessed IDs are ambiguous")
    audit_strength_ids = {
        strength.get("strength_id")
        for strength in audit.get("strengths", [])
        if isinstance(strength, dict) and isinstance(strength.get("strength_id"), str)
    }
    report_strength_ids = report.get("strengths", [])
    if isinstance(report_strength_ids, list):
        for index, strength_id in enumerate(report_strength_ids):
            if strength_id not in audit_strength_ids:
                errors.append(f"report.strengths[{index}]: unknown canonical strength")
    return errors
