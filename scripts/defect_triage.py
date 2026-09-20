"""Bounded defect triage: an indexed candidate table plus one typed choice.

A report names defects. This module covers the step before that, where an incoming
observation ("the saved choice vanished after reload") has to be matched against the
taxonomy. Rather than asking a model to name a defect out of all 50 entries, it builds
a numbered table of the plausible entries and accepts exactly one index back. Code owns
the identity, so an invented, stale, or misspelled name cannot enter the record.

Pattern source: the indexed action space of ``browser-use/jev-ultrafast`` — a numbered
table of observed controls, one operation and one target per request, and a model that
never emits a selector. The rules borrowed here:

* index the options instead of describing them in prose;
* one typed choice per cycle over a bounded set;
* the answer is an index into the table the judge was shown, never an id or code;
* raw judge text is parsed strictly — a bare index or an explicit none, never mined
  for a number, so prose cannot smuggle an identity past the boundary;
* code validates that answer against that same table;
* a hopeless input resolves to ``unknown`` without spending a request.

This module decides nothing. A ``matched`` outcome is a suggestion for a human, the
taxonomy's own conformance rules stay with ``scripts/validate.py``, and a wrong answer
costs one rejected index rather than a wrong entry in a record.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_FILES = ("behavior", "content", "interface")
PRESENCE_TEST_LIMIT = 240
DEFAULT_LIMIT = 5

# A judge is any callable that sees the numbered table and returns one index, or None
# for "no applicable entry". It is never handed the full taxonomy, and its answer is
# never trusted as an identity.
Judge = Callable[[Sequence["Candidate"]], object]

OUTCOMES = ("matched", "none", "unknown", "invalid", "unjudged")


class TriageError(RuntimeError):
    """Raised when the taxonomy cannot be read."""


class UnparseableAnswer(ValueError):
    """Raised when a judge's raw text is neither a bare index nor an explicit none."""


# The only words accepted as "no applicable entry". Everything else that is not digits is
# refused, so a returned defect id or sentence cannot be mistaken for a choice.
NONE_WORDS = frozenset({"none", "no", "nothing", "n/a", "na", "unknown"})
BARE_INDEX = re.compile(r"\d+")


@dataclass(frozen=True)
class Candidate:
    """One numbered row of the table a judge is shown."""

    index: int
    id: str
    name: str
    category: str
    standard: str
    presence_test: str
    score: float


@dataclass(frozen=True)
class Triage:
    """The bounded decision, with the table it was taken against."""

    outcome: str
    symptom: str
    candidates: tuple[Candidate, ...]
    chosen: Candidate | None
    detail: str

    @property
    def suggestion(self) -> str | None:
        """The defect id a human may consider, or None for every other outcome."""
        return self.chosen.id if self.outcome == "matched" and self.chosen else None

    def as_json(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "suggestion": self.suggestion,
            "detail": self.detail,
            "candidates": [
                {"index": item.index, "id": item.id, "name": item.name, "score": item.score}
                for item in self.candidates
            ],
        }


def load_taxonomy(root: Path = REPOSITORY_ROOT) -> list[dict[str, Any]]:
    """Read every taxonomy entry. Failure is reported without leaking a local path."""
    entries: list[dict[str, Any]] = []
    for name in TAXONOMY_FILES:
        try:
            loaded = json.loads((root / "taxonomy" / f"{name}.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise TriageError(f"taxonomy unreadable: {name}") from error
        if not isinstance(loaded, list):
            raise TriageError(f"taxonomy unreadable: {name}")
        entries.extend(loaded)
    return entries


def _tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z]{3,}", text.lower())}


def _document(entry: dict[str, Any]) -> set[str]:
    return _tokens(
        " ".join(str(entry.get(field, "")) for field in ("id", "name", "definition", "symptom"))
    )


def rank_candidates(
    symptom: str,
    entries: Sequence[dict[str, Any]],
    *,
    limit: int = DEFAULT_LIMIT,
) -> tuple[Candidate, ...]:
    """Return the numbered table: entries sharing vocabulary with the observation.

    Scoring is IDF-weighted vocabulary coverage of the observation by each entry's own
    text. Entries sharing nothing are omitted rather than ranked last, so an unrelated
    observation produces an empty table instead of a misleading one.
    """
    query = _tokens(symptom)
    documents = [_document(entry) for entry in entries]
    document_frequency: dict[str, int] = {}
    for document in documents:
        for word in document:
            document_frequency[word] = document_frequency.get(word, 0) + 1
    idf = {
        word: math.log(max(len(entries), 1) / count)
        for word, count in document_frequency.items()
    }

    denominator = sum(idf.get(word, 0.0) for word in query) or 1.0
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for entry, document in zip(entries, documents):
        score = sum(idf.get(word, 0.0) for word in query & document) / denominator
        if score > 0:
            scored.append((score, str(entry.get("id", "")), entry))

    scored.sort(key=lambda item: (-item[0], item[1]))
    table: list[Candidate] = []
    for index, (score, entry_id, entry) in enumerate(scored[: max(limit, 0)], start=1):
        definition = str(entry.get("definition", "")).strip()
        table.append(
            Candidate(
                index=index,
                id=entry_id,
                name=str(entry.get("name", "")),
                category=str(entry.get("category", "")),
                standard=str(entry.get("standard", "")),
                presence_test=definition[:PRESENCE_TEST_LIMIT],
                score=round(score, 4),
            )
        )
    return tuple(table)


def triage(
    symptom: str,
    *,
    entries: Sequence[dict[str, Any]] | None = None,
    judge: Judge | None = None,
    limit: int = DEFAULT_LIMIT,
    floor: float = 0.0,
    root: Path = REPOSITORY_ROOT,
) -> Triage:
    """Build the table, then take at most one typed choice against it.

    ``floor`` gates *whether* a request is spent, not whether the answer is believed:
    no retrieved score is treated as a confidence. Callers must treat any outcome other
    than ``matched`` as "no suggestion".
    """
    table = rank_candidates(symptom, entries if entries is not None else load_taxonomy(root), limit=limit)
    if not table:
        return Triage("unknown", symptom, (), None, "no taxonomy entry shares vocabulary with the observation")
    if table[0].score < floor:
        return Triage("unknown", symptom, table, None, "best candidate sits below the configured floor; no choice requested")
    if judge is None:
        return Triage("unjudged", symptom, table, None, "candidate table only; no judge supplied")

    try:
        answer = judge(table)
    except UnparseableAnswer:
        return Triage("invalid", symptom, table, None, "judge text was not a bare index; an id, path or free text is never accepted")
    if answer is None:
        return Triage("none", symptom, table, None, "judge reported no applicable entry")
    if isinstance(answer, bool) or not isinstance(answer, int):
        return Triage("invalid", symptom, table, None, "judge returned something other than an index; an id, path or free text is never accepted")
    if not 1 <= answer <= len(table):
        return Triage("invalid", symptom, table, None, "judge returned an index outside the offered table")
    return Triage("matched", symptom, table, table[answer - 1], "index validated against the offered table")


def parse_choice(raw: str) -> int | None:
    """Map a judge's raw text to an index, or to None for "no applicable entry".

    Only a bare integer qualifies. A defect id, a path, a sentence or a code fragment is
    refused rather than searched for a number, so a judge cannot smuggle an identity
    through prose, and an empty answer is refused rather than read as a choice.
    """
    text = raw.strip()
    if text.endswith("."):
        text = text[:-1].strip()
    if text.lower() in NONE_WORDS:
        return None
    if BARE_INDEX.fullmatch(text):
        return int(text)
    raise UnparseableAnswer("judge text was not a bare index")


def text_judge(respond: Callable[[Sequence[Candidate]], str]) -> Judge:
    """Wrap a model call that returns text into a judge that returns an index or None."""

    def judge(table: Sequence[Candidate]) -> object:
        return parse_choice(respond(table))

    return judge


def _static_judge(choice: int | None) -> Judge:
    """A stand-in judge for the CLI: returns one typed choice and nothing else."""

    def judge(_table: Sequence[Candidate]) -> object:
        return choice

    return judge


def _select_judge(choice: int | None, answer: str | None) -> Judge | None:
    """A judge for the CLI: a typed index, or raw text parsed strictly, or none at all."""
    if choice is not None:
        return _static_judge(choice)
    if answer is not None:
        return text_judge(lambda _table: answer)
    return None


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank taxonomy entries for one observation and take one typed choice."
    )
    parser.add_argument("--symptom", required=True)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--floor", type=float, default=0.0)
    choices = parser.add_mutually_exclusive_group()
    choices.add_argument("--choose", type=int, default=None, help="typed index a judge would return")
    choices.add_argument("--answer", default=None, help="raw text a judge would return; parsed strictly")
    parser.add_argument("--taxonomy-root", type=Path, default=REPOSITORY_ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = _parse_args(argv)
    try:
        entries = load_taxonomy(arguments.taxonomy_root)
    except TriageError:
        print("triage: taxonomy unavailable", file=sys.stderr)
        return 1
    resolution = triage(
        arguments.symptom,
        entries=entries,
        judge=_select_judge(arguments.choose, arguments.answer),
        limit=arguments.limit,
        floor=arguments.floor,
    )
    print(json.dumps(resolution.as_json(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
