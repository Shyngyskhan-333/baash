import unittest
from pathlib import Path

from src.evidence.ai_grounding import AIGroundingService
from src.evidence.evaluation import EvaluationCaseType, EvaluationStatus
from src.evidence.evaluation_fixture_loader import EvaluationFixtureLoader
from src.evidence.fixture_evaluation import FixtureEvaluationRunner


class FakeSearchService:
    def __init__(self, results):
        self.results = results

    def search(self, query, *, top_k=10, doc_ids=None):
        self.query = query
        self.top_k = top_k
        self.doc_ids = doc_ids
        return {"results": self.results}


class FixtureEvaluationRunnerTests(unittest.TestCase):
    def test_run_file_loads_fixture_cases_and_runs_deterministic_suite(self):
        fixture_path = Path(__file__).parent / "fixtures" / "evaluation" / "golden_cases.json"
        cases = EvaluationFixtureLoader().load_file(fixture_path)
        grounding_case = next(case for case in cases if case.case_type == EvaluationCaseType.ANSWER_GROUNDING)
        license_quote = "Synthetic licensing requirement quote."
        notification_quote = "Synthetic notification requirement quote."
        search_results = [
            {
                "citation_id": "citation_synthetic_bank_obligation_001",
                "citation_quote": "Synthetic banking obligation quote.",
                "document_version_id": "version_synthetic_bank_law_2026_001",
            },
            {
                "citation_id": "citation_synthetic_license_requirement_001",
                "citation_quote": license_quote,
                "document_version_id": "version_synthetic_license_rule_2026_001",
            },
        ]
        grounded = AIGroundingService().ground_answer(
            answer="Synthetic answer grounded to the notification citation.",
            model_name="fixture",
            model_version="test",
            messages=[{"role": "user", "content": grounding_case.query}],
            evidence_results=[
                {
                    "citation_id": "citation_synthetic_notification_requirement_001",
                    "citation_label": "Synthetic notification citation",
                    "citation_quote": notification_quote,
                    "document_version_id": "version_synthetic_notification_rule_2026_001",
                }
            ],
            packet_title="Synthetic grounding packet",
            packet_purpose="fixture evaluation",
        )

        report = FixtureEvaluationRunner.from_search_service(FakeSearchService(search_results)).run_file(
            fixture_path,
            expected_quotes={
                "citation_synthetic_license_requirement_001": license_quote,
            },
            grounded_outputs={grounding_case.id: grounded},
        )

        self.assertEqual(report.total_cases, 3)
        self.assertEqual(report.passed_cases, 3)
        self.assertEqual([result.status for result in report.results], [EvaluationStatus.PASSED] * 3)

    def test_run_file_fails_closed_when_grounding_output_is_missing(self):
        fixture_path = Path(__file__).parent / "fixtures" / "evaluation" / "golden_cases.json"

        with self.assertRaises(ValueError):
            FixtureEvaluationRunner.from_search_service(FakeSearchService([])).run_file(
                fixture_path,
                expected_quotes={},
                grounded_outputs={},
            )


if __name__ == "__main__":
    unittest.main()
