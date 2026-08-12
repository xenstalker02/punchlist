#!/usr/bin/env python3
"""Validate Punchlist's taxonomy, examples, counts, and internal references."""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_COUNTS = {"interface": 20, "content": 16, "behavior": 14}
MARKDOWN_FILES = ("README.md", "SKILL.md")
PATH_SUFFIXES = (".json", ".md", ".py", ".yml", ".yaml", ".svg", ".png")
OPTIONAL_PROJECT_FILES = {"conventions.md"}


def type_matches(value: Any, expected: str) -> bool:
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
        errors.append(f"{location}: {value!r} is not one of {schema['enum']!r}")

    if isinstance(value, str) and "pattern" in schema:
        if re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{location}: {value!r} does not match {schema['pattern']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{location}: {value} is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{location}: {value} is above maximum {schema['maximum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{location}: expected at least {schema['minItems']} item(s)")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(validate_schema(item, schema["items"], f"{location}[{index}]"))

    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{location}: missing required property {required!r}")
        for key, child_schema in schema.get("properties", {}).items():
            if key in value:
                errors.extend(validate_schema(value[key], child_schema, f"{location}.{key}"))

    return errors


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as error:
        return None, [f"{path.as_posix()}: {error}"]


def validate_taxonomy(root: Path) -> tuple[list[str], int]:
    schema, errors = load_json(root / "schema" / "defect.schema.json")
    if errors or not isinstance(schema, dict):
        return errors or ["schema/defect.schema.json: expected an object"], 0

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
                    f"{location}.category: expected {category!r}, found {entry.get('category')!r}"
                )
            if not str(entry.get("definition", "")).startswith("Present when"):
                errors.append(f"{location}.definition: must begin 'Present when'")

            entry_id = entry.get("id")
            if isinstance(entry_id, str):
                if entry_id in seen_ids:
                    errors.append(f"{location}.id: duplicate id {entry_id!r}")
                seen_ids.add(entry_id)

            refs = entry.get("refs")
            public_refs: list[Any] = []
            if isinstance(refs, dict):
                for key in ("wcag", "other"):
                    values = refs.get(key, [])
                    if isinstance(values, list):
                        public_refs.extend(values)
            if not any(isinstance(ref, str) and ref.strip() for ref in public_refs):
                errors.append(f"{location}.refs: requires at least one public-standard reference")

            example = entry.get("example")
            if not isinstance(example, str) or not example.strip():
                errors.append(f"{location}.example: requires a documented real instance")

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


def referenced_paths(markdown: str) -> set[str]:
    references: set[str] = set()
    for target in re.findall(r"!?\[[^\]]*\]\(([^)\s]+)", markdown):
        references.add(target.split("#", 1)[0])
    for value in re.findall(r"(?<!`)`([^`\n]+)`(?!`)", markdown):
        candidate = value.strip().split("#", 1)[0]
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
    for filename in MARKDOWN_FILES:
        path = root / filename
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
    errors.extend(validate_internal_references(root))

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
