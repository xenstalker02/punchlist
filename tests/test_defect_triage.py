from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.defect_triage import (
    REPOSITORY_ROOT,
    Candidate,
    load_taxonomy,
    rank_candidates,
    triage,
)

SYMPTOM = "The saved frame choice was gone from the basket after reloading the page."


class RecordingJudge:
    """Stands in for a typed model: it returns exactly one value and counts requests."""

    def __init__(self, answer: object) -> None:
        self.answer = answer
        self.calls = 0
        self.seen: tuple[Candidate, ...] | None = None

    def __call__(self, table: tuple[Candidate, ...]) -> object:
        self.calls += 1
        self.seen = table
        return self.answer


class RankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = load_taxonomy()

    def test_every_taxonomy_entry_loads_once(self) -> None:
        self.assertEqual(50, len(self.entries))
        self.assertEqual(50, len({str(entry["id"]) for entry in self.entries}))

    def test_the_table_is_numbered_ordered_and_bounded(self) -> None:
        table = rank_candidates(SYMPTOM, self.entries, limit=5)
        self.assertTrue(table)
        self.assertLessEqual(len(table), 5)
        self.assertEqual(list(range(1, len(table) + 1)), [row.index for row in table])
        self.assertEqual(sorted((row.score for row in table), reverse=True), [row.score for row in table])
        self.assertEqual(len({row.id for row in table}), len(table))

    def test_an_unrelated_observation_offers_nothing(self) -> None:
        self.assertEqual((), rank_candidates("zzz qqq", self.entries))

    def test_rows_carry_no_more_than_the_presence_test(self) -> None:
        for row in rank_candidates(SYMPTOM, self.entries):
            self.assertLessEqual(len(row.presence_test), 240)
            self.assertTrue(row.presence_test)


class TypedChoiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = load_taxonomy()

    def test_an_index_selects_the_row_it_points_at(self) -> None:
        judge = RecordingJudge(1)
        result = triage(SYMPTOM, entries=self.entries, judge=judge)
        self.assertEqual("matched", result.outcome)
        self.assertEqual(1, judge.calls)
        self.assertEqual(result.candidates[0].id, result.suggestion)

    def test_a_defect_id_returned_by_the_judge_is_never_accepted(self) -> None:
        correct = rank_candidates(SYMPTOM, self.entries)[0].id
        result = triage(SYMPTOM, entries=self.entries, judge=RecordingJudge(correct))
        self.assertEqual("invalid", result.outcome)
        self.assertIsNone(result.suggestion)

    def test_answers_outside_the_table_are_invalid(self) -> None:
        for answer in (0, -1, 99, True, 1.0, "2"):
            with self.subTest(answer=answer):
                result = triage(SYMPTOM, entries=self.entries, judge=RecordingJudge(answer))
                self.assertEqual("invalid", result.outcome)
                self.assertIsNone(result.suggestion)

    def test_none_means_no_applicable_entry(self) -> None:
        result = triage(SYMPTOM, entries=self.entries, judge=RecordingJudge(None))
        self.assertEqual("none", result.outcome)
        self.assertIsNone(result.suggestion)

    def test_the_floor_spends_no_choice(self) -> None:
        judge = RecordingJudge(1)
        result = triage(SYMPTOM, entries=self.entries, judge=judge, floor=1.01)
        self.assertEqual("unknown", result.outcome)
        self.assertEqual(0, judge.calls)

    def test_an_unrelated_observation_spends_no_choice(self) -> None:
        judge = RecordingJudge(1)
        result = triage("zzz qqq", entries=self.entries, judge=judge)
        self.assertEqual("unknown", result.outcome)
        self.assertEqual(0, judge.calls)

    def test_without_a_judge_only_the_table_returns(self) -> None:
        result = triage(SYMPTOM, entries=self.entries)
        self.assertEqual("unjudged", result.outcome)
        self.assertIsNone(result.suggestion)
        self.assertTrue(result.candidates)

    def test_the_judge_sees_the_numbered_table_and_nothing_else(self) -> None:
        judge = RecordingJudge(1)
        triage(SYMPTOM, entries=self.entries, judge=judge, limit=3)
        self.assertIsNotNone(judge.seen)
        assert judge.seen is not None
        self.assertLessEqual(len(judge.seen), 3)
        fields = {field.name for field in dataclasses.fields(judge.seen[0])}
        self.assertEqual(
            {"index", "id", "name", "category", "standard", "presence_test", "score"},
            fields,
        )


class CommandLineTests(unittest.TestCase):
    def run_triage(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / "scripts" / "defect_triage.py"), *arguments],
            capture_output=True,
            text=True,
            cwd=REPOSITORY_ROOT,
        )

    def test_stdout_is_one_json_document(self) -> None:
        result = self.run_triage("--symptom", SYMPTOM, "--choose", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(1, len(result.stdout.strip().splitlines()))
        payload = json.loads(result.stdout)
        self.assertEqual("matched", payload["outcome"])
        self.assertEqual(payload["candidates"][0]["id"], payload["suggestion"])

    def test_no_choice_reports_the_table_only(self) -> None:
        payload = json.loads(self.run_triage("--symptom", SYMPTOM).stdout)
        self.assertEqual("unjudged", payload["outcome"])
        self.assertIsNone(payload["suggestion"])

    def test_an_out_of_range_choice_is_reported_not_crashed(self) -> None:
        result = self.run_triage("--symptom", SYMPTOM, "--choose", "99")
        self.assertEqual(0, result.returncode)
        self.assertEqual("invalid", json.loads(result.stdout)["outcome"])

    def test_an_unreadable_taxonomy_is_location_safe(self) -> None:
        result = self.run_triage("--symptom", SYMPTOM, "--taxonomy-root", str(REPOSITORY_ROOT / "tmp"))
        self.assertEqual(1, result.returncode)
        self.assertEqual("triage: taxonomy unavailable\n", result.stderr)
        self.assertNotIn(str(REPOSITORY_ROOT), result.stderr)


class PublishedFindingTests(unittest.TestCase):
    """The retrieval half must place a real published finding's defect in its table."""

    def test_a_published_symptom_reaches_its_recorded_defect(self) -> None:
        entries = load_taxonomy()
        symptom = "Reload discarded an unfinished configuration."
        table = rank_candidates(symptom, entries, limit=5)
        self.assertIn("amnesiac-relaunch", [row.id for row in table])


if __name__ == "__main__":
    unittest.main()
