#!/usr/bin/env python3
"""Validate Punchlist's taxonomy, examples, counts, and internal references."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


EXPECTED_COUNTS = {"interface": 20, "content": 16, "behavior": 14}
MARKDOWN_FILES = (
    "README.md",
    "SKILL.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "SUPPORT.md",
    "RELEASING.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
)
OPTIONAL_MARKDOWN_FILES: tuple[str, ...] = ()
PATH_SUFFIXES = (".json", ".md", ".py", ".yml", ".yaml", ".svg", ".png")
OPTIONAL_PROJECT_FILES = {"conventions.md"}
PUBLIC_ARTIFACT_SUFFIXES = {".md", ".json", ".html", ".pdf", ".svg", ".yml", ".yaml"}
PUBLIC_MEDIA_SUFFIXES = {".png", ".svg"}
PUBLIC_EXCLUDED_DIRECTORIES = {
    ".git",
    ".superpowers",
    "node_modules",
    "out",
    "output",
    "tmp",
    "__pycache__",
    "playwright-report",
    "test-results",
}
PUBLIC_EXCLUDED_FILES = {Path("conventions.md"), Path("themes/theme.local.json")}
PUBLIC_EXCLUDED_PREFIXES = (Path(".superpowers"), Path("docs/superpowers"))
REGISTERED_SYNTHETIC_JSON = {
    "examples/synthetic/audit.json",
    "examples/synthetic/report.json",
}
DOMAIN_SPECIFIC_BRIEF_MARKERS = (
    "first-time vinyl buyer",
    "known album",
    "one edition to buy",
    "first-time purchase",
)
PUBLIC_FORBIDDEN_MARKERS = (
    re.compile(r"\bcompass\b", re.IGNORECASE),
    re.compile(r"\bpharma commercial analytics\b", re.IGNORECASE),
    re.compile(r"\bdiscogs\b", re.IGNORECASE),
)
GOVERNANCE_REQUIRED_MARKERS = {
    "SECURITY.md": (("## Handle audit data separately", "report-data handling"),),
    "RELEASING.md": (("<!-- governance: fresh-separate-publish-authorization -->", "publish authorization"),),
}
GENERIC_BRIEF_CONTRACT = (
    "A `[user]`, in `[state]` on `[device]`, starts at `[entry point]` and tries to "
    "`[complete task]`; `[profile]` profile. Severity basis: `[basis]`."
)


def type_matches(value: Any, expected: str | list[str]) -> bool:
    if isinstance(expected, list):
        return any(type_matches(value, item) for item in expected)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_schema(value: Any, schema: dict[str, Any], location: str) -> list[str]:
    errors: list[str] = []

    if "oneOf" in schema:
        branch_errors = [validate_schema(value, branch, location) for branch in schema["oneOf"]]
        matches = sum(not branch for branch in branch_errors)
        if matches != 1:
            errors.append(f"{location}: must match exactly one allowed shape")
        return errors

    expected_type = schema.get("type")
    if expected_type and not type_matches(value, expected_type):
        return [f"{location}: expected {expected_type}, got {type(value).__name__}"]

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: must be one of allowed values")

    if isinstance(value, str) and "pattern" in schema:
        if re.search(schema["pattern"], value) is None:
            errors.append(f"{location}: does not match required pattern")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{location}: expected minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{location}: expected maxLength {schema['maxLength']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{location}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{location}: above maximum")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{location}: expected at least {schema['minItems']} item(s)")
        if schema.get("uniqueItems"):
            encoded_items = [json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True) for item in value]
            if len(encoded_items) != len(set(encoded_items)):
                errors.append(f"{location}: expected unique items")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(validate_schema(item, schema["items"], f"{location}[{index}]"))

    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{location}: missing required property {required!r}")
        if schema.get("additionalProperties") is False:
            properties = schema.get("properties", {})
            for key in sorted(value.keys() - properties.keys()):
                errors.append(f"{location}: unexpected property")
        for key, child_schema in schema.get("properties", {}).items():
            if key in value:
                errors.extend(validate_schema(value[key], child_schema, f"{location}.{key}"))

    return errors


def validate_source_reference(
    reference: dict[str, str], catalog: dict[str, dict[str, Any]]
) -> list[str]:
    source_id = reference.get("source_id")
    citation = reference.get("citation")
    if not isinstance(source_id, str):
        return ["source reference: source_id must be a string"]
    if source_id not in catalog:
        return ["source reference: unknown source_id"]
    if not isinstance(citation, str):
        return ["source reference: citation must be a string"]

    patterns = catalog[source_id].get("citation_patterns", [])
    if not isinstance(patterns, list):
        return ["source reference: invalid citation matcher"]
    try:
        matchers = [re.compile(pattern) for pattern in patterns]
    except (TypeError, re.error):
        return ["source reference: invalid citation matcher"]

    matches = sum(matcher.fullmatch(citation) is not None for matcher in matchers)
    if matches != 1:
        return [
            "source reference: citation must match exactly one permitted pattern"
        ]
    return []


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as error:
        return None, [f"{path.as_posix()}: {error}"]


def load_source_catalog(root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    document, errors = load_json(root / "sources" / "standards.json")
    schema, schema_errors = load_json(root / "schema" / "source.schema.json")
    errors.extend(schema_errors)
    if not isinstance(document, dict) or not isinstance(schema, dict):
        return {}, errors or ["sources/standards.json: expected an object"]

    errors.extend(validate_schema(document, schema, "sources/standards.json"))
    sources = document.get("sources")
    if not isinstance(sources, list):
        return {}, errors + ["sources/standards.json.sources: expected an array"]

    catalog: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str):
            continue
        if source_id in catalog:
            errors.append(f"sources/standards.json.sources[{index}]: duplicate source_id")
            continue
        catalog[source_id] = source
    return catalog, errors


def validate_taxonomy(root: Path) -> tuple[list[str], int]:
    schema, errors = load_json(root / "schema" / "defect.schema.json")
    if errors or not isinstance(schema, dict):
        return errors or ["schema/defect.schema.json: expected an object"], 0

    catalog, source_errors = load_source_catalog(root)
    errors.extend(source_errors)

    all_entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for category, expected_count in EXPECTED_COUNTS.items():
        relative_path = Path("taxonomy") / f"{category}.json"
        entries, load_errors = load_json(root / relative_path)
        errors.extend(load_errors)
        if load_errors:
            continue
        if not isinstance(entries, list):
            errors.append(f"{relative_path.as_posix()}: expected an array")
            continue
        if len(entries) != expected_count:
            errors.append(
                f"{relative_path.as_posix()}: expected {expected_count} entries, found {len(entries)}"
            )

        for index, entry in enumerate(entries):
            location = f"{relative_path.as_posix()}[{index}]"
            errors.extend(validate_schema(entry, schema, location))
            if not isinstance(entry, dict):
                continue
            all_entries.append(entry)

            if entry.get("category") != category:
                errors.append(
                    f"{location}.category: must match containing taxonomy category"
                )
            if not str(entry.get("definition", "")).startswith("Present when"):
                errors.append(f"{location}.definition: must begin 'Present when'")

            entry_id = entry.get("id")
            if isinstance(entry_id, str):
                if entry_id in seen_ids:
                    errors.append(f"{location}.id: duplicate id")
                seen_ids.add(entry_id)

            refs = entry.get("refs")
            public_refs: list[dict[str, str]] = []
            if isinstance(refs, dict):
                for key in ("wcag", "other"):
                    values = refs.get(key, [])
                    if isinstance(values, list):
                        for reference_index, reference in enumerate(values):
                            reference_location = f"{location}.refs.{key}[{reference_index}]"
                            if not isinstance(reference, dict):
                                errors.append(f"{reference_location}: expected a source reference object")
                                continue
                            source_errors = validate_source_reference(reference, catalog)
                            errors.extend(
                                f"{reference_location}: {error}" for error in source_errors
                            )
                            if not source_errors:
                                public_refs.append(reference)
            if not public_refs:
                errors.append(f"{location}.refs: requires at least one public-standard reference")

            illustration = entry.get("illustration")
            if not isinstance(illustration, str) or not illustration.startswith("Non-evidentiary illustration: "):
                errors.append(f"{location}.illustration: requires an explicit non-evidentiary label")

    expected_total = sum(EXPECTED_COUNTS.values())
    if len(all_entries) != expected_total:
        errors.append(f"taxonomy: expected {expected_total} defects, found {len(all_entries)}")
    return errors, len(all_entries)


def validate_examples(root: Path) -> list[str]:
    examples_dir = root / "examples"
    if not examples_dir.exists():
        return []

    schema, errors = load_json(root / "schema" / "finding.schema.json")
    if errors or not isinstance(schema, dict):
        return errors or ["schema/finding.schema.json: expected an object"]

    for path in sorted(examples_dir.glob("*.json")):
        document, load_errors = load_json(path)
        errors.extend(load_errors)
        if load_errors:
            continue
        findings = document if isinstance(document, list) else [document]
        for index, finding in enumerate(findings):
            relative = path.relative_to(root).as_posix()
            location = f"{relative}[{index}]" if isinstance(document, list) else relative
            errors.extend(validate_schema(finding, schema, location))
    return errors


def validate_synthetic_bundle(root: Path) -> list[str]:
    """Validate and render the committed synthetic audit/report contract."""
    from scripts.render_report import render_report
    from scripts.report_model import validate_audit_bundle, validate_report_projection

    errors: list[str] = []
    synthetic_root = root / "examples" / "synthetic"
    documents: dict[str, Any] = {}
    if not synthetic_root.is_dir():
        return ["examples/synthetic: expected directory"]

    for path in sorted(synthetic_root.rglob("*.json")):
        relative = path.relative_to(root).as_posix()
        if relative not in REGISTERED_SYNTHETIC_JSON:
            errors.append(f"{relative}: unregistered synthetic JSON")
        document, load_errors = load_json(path)
        errors.extend(load_errors)
        if not load_errors:
            documents[relative] = document

    audit_relative = "examples/synthetic/audit.json"
    report_relative = "examples/synthetic/report.json"
    audit = documents.get(audit_relative)
    report = documents.get(report_relative)
    if not isinstance(audit, dict):
        errors.append(f"{audit_relative}: expected a JSON object")
    if not isinstance(report, dict):
        errors.append(f"{report_relative}: expected a JSON object")

    theme_path = root / "themes" / "punchlist-default.json"
    theme, theme_errors = load_json(theme_path)
    errors.extend(theme_errors)
    if not isinstance(theme, dict):
        errors.append("themes/punchlist-default.json: expected a JSON object")

    if not isinstance(audit, dict) or not isinstance(report, dict) or not isinstance(theme, dict):
        return errors

    errors.extend(f"{audit_relative}: {error}" for error in validate_audit_bundle(root, audit))
    errors.extend(
        f"{report_relative}: {error}"
        for error in validate_report_projection(audit, report, theme, root)
    )
    if errors:
        return errors

    try:
        rendered_text = render_report(audit, report, theme, root)
    except ValueError as error:
        return [f"examples/synthetic: could not render canonical bundle: {error}"]
    rendered = rendered_text.encode("utf-8")
    html_path = synthetic_root / "report.html"
    try:
        committed = html_path.read_bytes()
    except OSError as error:
        return [f"examples/synthetic/report.html: {error}"]
    if committed != rendered:
        errors.append("examples/synthetic/report.html: stale generated HTML")
    return errors


def public_artifact_paths(root: Path) -> list[Path]:
    """Return public documentation and data files, excluding tool state."""
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in PUBLIC_ARTIFACT_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if relative in PUBLIC_EXCLUDED_FILES or any(
            part in PUBLIC_EXCLUDED_DIRECTORIES for part in relative.parts
        ) or any(relative.is_relative_to(prefix) for prefix in PUBLIC_EXCLUDED_PREFIXES):
            continue
        paths.append(path)
    return sorted(paths)


def validate_public_safety(root: Path) -> list[str]:
    """Reject recipient-unsafe values without reproducing secret-shaped values."""
    from scripts.report_model import privacy_errors

    errors: list[str] = []
    for path in public_artifact_paths(root):
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".pdf":
            try:
                from scripts.inspect_pdf import PdfDependencyError, validate_pdf_privacy

                errors.extend(validate_pdf_privacy(path, relative))
            except PdfDependencyError:
                errors.append(f"{relative}: PDF validation requires PyMuPDF from requirements-dev.txt")
            except ValueError:
                errors.append(f"{relative}: could not inspect public PDF")
            continue
        if path.suffix.lower() == ".json":
            document, load_errors = load_json(path)
            errors.extend(load_errors)
            if not load_errors:
                errors.extend(privacy_errors(document, relative))
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{relative}: {error}")
            continue
        errors.extend(privacy_errors(content, relative))
    return errors


def validate_public_media(root: Path) -> list[str]:
    """Require an approved, integrity-pinned registry for public raster/vector media."""
    errors: list[str] = []
    manifest_path = root / "assets" / "public-assets.json"
    manifest, load_errors = load_json(manifest_path)
    errors.extend(load_errors)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("assets"), list):
        return errors + ["assets/public-assets.json: expected an assets array"]

    required = {"path", "sha256", "purpose", "alt", "provenance", "publication_approved"}
    registered: set[str] = set()
    for index, record in enumerate(manifest["assets"]):
        location = f"assets/public-assets.json.assets[{index}]"
        if not isinstance(record, dict) or set(record) != required:
            errors.append(f"{location}: invalid public media record")
            continue
        relative = record.get("path")
        digest = record.get("sha256")
        relative_path = Path(relative) if isinstance(relative, str) else None
        if (
            not isinstance(relative, str)
            or "\\" in relative
            or relative_path is None
            or relative_path.is_absolute()
            or ".." in relative_path.parts
            or not relative.startswith("assets/")
            or relative_path.suffix.lower() not in PUBLIC_MEDIA_SUFFIXES
        ):
            errors.append(f"{location}.path: invalid public media path")
            continue
        if relative in registered:
            errors.append(f"{location}.path: duplicate public media path")
        registered.add(relative)
        if record.get("publication_approved") is not True:
            errors.append(f"{location}: publication approval required")
        for field in ("purpose", "alt", "provenance"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"{location}.{field}: required")
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"{relative}: registered public media is missing or unsafe")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if not isinstance(digest, str) or re.fullmatch(r"[a-f0-9]{64}", digest) is None or actual != digest:
            errors.append(f"{relative}: public media hash mismatch")

    discovered: set[str] = set()
    for path in (root / "assets").rglob("*"):
        if path.is_file() and path.suffix.lower() in PUBLIC_MEDIA_SUFFIXES:
            discovered.add(path.relative_to(root).as_posix())
    for relative in sorted(discovered - registered):
        errors.append(f"{relative}: unregistered public media")
    for relative in sorted(registered - discovered):
        errors.append(f"{relative}: registered public media is missing")
    return errors


def referenced_paths(markdown: str) -> set[str]:
    references: set[str] = set()
    for target in re.findall(r"!?\[[^\]]*\]\(([^)\s]+)", markdown):
        references.add(target.split("#", 1)[0])
    for value in re.findall(r"(?<!`)`([^`\n]+)`(?!`)", markdown):
        candidate = value.strip().split("#", 1)[0]
        if candidate.startswith(("python ", "npm ", "npx ", "git ", "@")):
            continue
        if candidate in OPTIONAL_PROJECT_FILES:
            continue
        if "/" in candidate and any(mark in candidate for mark in ("*", ".")):
            references.add(candidate)
        elif candidate.endswith(PATH_SUFFIXES):
            references.add(candidate)
    return {
        reference
        for reference in references
        if reference
        and not reference.startswith(("http://", "https://", "mailto:", "#", "~/"))
    }


def validate_internal_references(root: Path) -> list[str]:
    errors: list[str] = []
    for filename in (*MARKDOWN_FILES, *OPTIONAL_MARKDOWN_FILES):
        path = root / filename
        if filename in OPTIONAL_MARKDOWN_FILES and not path.exists():
            continue
        try:
            markdown = path.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{filename}: {error}")
            continue
        for reference in sorted(referenced_paths(markdown)):
            normalized = reference.rstrip(".,;:")
            if any(char in normalized for char in "*?["):
                matches = glob.glob(str(root / normalized))
                exists = bool(matches)
            else:
                exists = (root / normalized).exists()
            if not exists:
                errors.append(f"{filename}: internal reference does not resolve: {normalized}")
    return errors


def validate_public_brief_contract(root: Path) -> list[str]:
    errors: list[str] = []
    for filename in ("README.md", "SKILL.md"):
        try:
            content = (root / filename).read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{filename}: {error}")
            continue
        if GENERIC_BRIEF_CONTRACT not in content:
            errors.append(f"{filename}: requires the generic placeholder brief contract")
        if any(marker in content.lower() for marker in DOMAIN_SPECIFIC_BRIEF_MARKERS):
            errors.append(f"{filename}: domain-specific brief marker")
    return errors


def validate_public_forbidden_markers(root: Path) -> list[str]:
    errors: list[str] = []
    for path in public_artifact_paths(root):
        if path.suffix.lower() == ".pdf":
            continue
        filename = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{filename}: {error}")
            continue
        if any(marker.search(content) for marker in PUBLIC_FORBIDDEN_MARKERS):
            errors.append(f"{filename}: public forbidden marker")
    return errors


def validate_governance_contract(root: Path) -> list[str]:
    errors: list[str] = []
    for filename, markers in GOVERNANCE_REQUIRED_MARKERS.items():
        try:
            content = (root / filename).read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{filename}: {error}")
            continue
        for marker, label in markers:
            if marker not in content:
                errors.append(f"{filename}: missing governance {'section' if filename == 'SECURITY.md' else 'checkpoint'}: {label}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to validate (defaults to the validator's parent repository).",
    )
    return parser.parse_args()


def main() -> int:
    root = parse_args().root.resolve()
    errors, defect_count = validate_taxonomy(root)
    errors.extend(validate_examples(root))
    errors.extend(validate_synthetic_bundle(root))
    errors.extend(validate_public_safety(root))
    errors.extend(validate_public_media(root))
    errors.extend(validate_internal_references(root))
    errors.extend(validate_public_brief_contract(root))
    errors.extend(validate_public_forbidden_markers(root))
    errors.extend(validate_governance_contract(root))

    if errors:
        print(f"Punchlist validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Punchlist validation passed: "
        f"{defect_count} defects "
        f"({EXPECTED_COUNTS['interface']} interface, "
        f"{EXPECTED_COUNTS['content']} content, "
        f"{EXPECTED_COUNTS['behavior']} behavior), "
        "schemas, evidence fields, and internal references checked."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
