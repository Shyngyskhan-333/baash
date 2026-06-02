import json
import tempfile
import unittest
from pathlib import Path

from src.evidence.evaluation import EvaluationCaseType
from src.evidence.evaluation_fixture_loader import EvaluationFixtureLoader


class EvaluationFixtureLoaderTests(unittest.TestCase):
    def test_repository_golden_fixture_loads_supported_case_types(self):
        fixture_path = Path(__file__).parent / "fixtures" / "evaluation" / "golden_cases.json"

        cases = EvaluationFixtureLoader().load_file(fixture_path)

        self.assertEqual(
            [case.case_type for case in cases],
            [
                EvaluationCaseType.RETRIEVAL_RECALL,
                EvaluationCaseType.CITATION_ACCURACY,
                EvaluationCaseType.ANSWER_GROUNDING,
            ],
        )
        self.assertTrue(all(case.source == "fixture:golden_cases" for case in cases))
        self.assertTrue(all(case.id.startswith("eval_case_") for case in cases))

    def test_load_file_creates_evaluation_cases_from_json(self):
        payload = {
            "cases": [
                {
                    "case_type": "retrieval_recall",
                    "name": "Bank documents",
                    "query": "банк документы",
                    "expected_citation_ids": ["citation_1"],
                    "expected_document_version_ids": ["version_1"],
                    "source": "fixture:test",
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "cases.json"
            fixture_path.write_text(json.dumps(payload), encoding="utf-8")

            cases = EvaluationFixtureLoader().load_file(fixture_path)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].case_type, EvaluationCaseType.RETRIEVAL_RECALL)
        self.assertEqual(cases[0].name, "Bank documents")
        self.assertEqual(cases[0].expected_citation_ids, ("citation_1",))
        self.assertEqual(cases[0].expected_document_version_ids, ("version_1",))
        self.assertEqual(cases[0].source, "fixture:test")

    def test_load_file_uses_stable_id_when_id_is_omitted(self):
        payload = {
            "cases": [
                {
                    "case_type": "citation_accuracy",
                    "name": "Citation case",
                    "query": "банк документы",
                    "expected_citation_ids": ["citation_1"],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "cases.json"
            fixture_path.write_text(json.dumps(payload), encoding="utf-8")
            first = EvaluationFixtureLoader().load_file(fixture_path)
            second = EvaluationFixtureLoader().load_file(fixture_path)

        self.assertEqual(first[0].id, second[0].id)
        self.assertTrue(first[0].id.startswith("eval_case_"))

    def test_load_file_rejects_missing_cases_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "invalid.json"
            fixture_path.write_text(json.dumps({"items": []}), encoding="utf-8")

            with self.assertRaises(ValueError):
                EvaluationFixtureLoader().load_file(fixture_path)

    def test_load_file_rejects_invalid_case_payload(self):
        payload = {
            "cases": [
                {
                    "case_type": "retrieval_recall",
                    "name": "Missing citations",
                    "query": "банк документы",
                    "expected_citation_ids": [],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "invalid_case.json"
            fixture_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValueError):
                EvaluationFixtureLoader().load_file(fixture_path)


if __name__ == "__main__":
    unittest.main()
