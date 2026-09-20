"""Measure the retrieval half of bounded defect triage on published findings.

Labels come from the two owner-approved public field reports under
``docs/field-reports/``; they are the only findings in this repository with a recorded
taxonomy id. Both reports describe a single-agent heuristic review — their own stated
limit — so this measures *retrieval*, not the pipeline's detection accuracy, and it is
not an accuracy claim about the taxonomy.

Run: ``python scripts/eval_defect_triage.py``
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.defect_triage import REPOSITORY_ROOT, load_taxonomy, rank_candidates

QUEEN_WORM = REPOSITORY_ROOT / "docs" / "field-reports" / "queen-worm.md"
ANGELS_REST = REPOSITORY_ROOT / "docs" / "field-reports" / "angels-rest.md"

# Queen Worm: | F1 · `f-…` — `defect-id` | 3/4 | observed problem | repair |
QUEEN_WORM_ROW = re.compile(
    r"^\|\s*F\d+\s*·\s*`f-[0-9a-f]+`\s*—\s*`(?P<id>[a-z0-9-]+)`\s*\|\s*\d/4\s*\|\s*(?P<symptom>[^|]+)\|",
    re.MULTILINE,
)
# Angel's Rest: | `f-…` — `defect-id`, **3/4** | recorded evidence | verification |
ANGELS_REST_ROW = re.compile(
    r"^\|\s*`f-[0-9a-f]+`\s*—\s*`(?P<id>[a-z0-9-]+)`[^|]*\|\s*(?P<symptom>[^|]+)\|",
    re.MULTILINE,
)


def read_rows(path: Path, pattern: re.Pattern[str]) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    rows = [(match.group("id"), " ".join(match.group("symptom").split())) for match in pattern.finditer(text, re.M)]
    return rows


def main() -> int:
    labelled = [("queen-worm", *row) for row in read_rows(QUEEN_WORM, QUEEN_WORM_ROW)]
    labelled += [("angels-rest", *row) for row in read_rows(ANGELS_REST, ANGELS_REST_ROW)]

    entries = load_taxonomy()
    known = {str(entry["id"]) for entry in entries}
    unknown = sorted({defect for _, defect, _ in labelled if defect not in known})
    if unknown:
        print(f"eval: labels missing from the taxonomy: {', '.join(unknown)}")
        return 1
    if len(labelled) != 10:
        print(f"eval: expected 10 published findings, parsed {len(labelled)}")
        return 1

    recall = {1: 0, 3: 0, 5: 0}
    name_hits = 0
    for _, defect, symptom in labelled:
        table = rank_candidates(symptom, entries, limit=5)
        ids = [row.id for row in table]
        for depth in recall:
            recall[depth] += 1 if defect in ids[:depth] else 0
        words = set(defect.split("-"))
        name_hits += 1 if words <= set(re.findall(r"[a-z]+", symptom.lower())) else 0

    majority, majority_count = Counter(defect for _, defect, _ in labelled).most_common(1)[0]
    summary = {
        "labelled_findings": len(labelled),
        "taxonomy_entries": len(entries),
        "recall_at": {f"top{depth}": count for depth, count in sorted(recall.items())},
        "baselines": {
            "defect_name_in_symptom": name_hits,
            "most_common_label": {"id": majority, "hits": majority_count},
        },
    }
    print(json.dumps(summary, sort_keys=True, indent=2))
    print("\nper finding:")
    for report, defect, symptom in labelled:
        table = rank_candidates(symptom, entries, limit=5)
        ids = [row.id for row in table]
        rank = ids.index(defect) + 1 if defect in ids else None
        print(f"  {report:<12} {defect:<22} rank {rank if rank else '—'}  ({symptom[:58]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
