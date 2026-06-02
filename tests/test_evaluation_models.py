import unittest
from dataclasses import FrozenInstanceError

from src.evidence.evaluation import (
    EvaluationCase,
    EvaluationCaseType,
    EvaluationResult,
    EvaluationStatus,
)
from src.evidence.models import compute_sha256


class EvaluationModelTests(unittest.TestCase):
    def test_evaluation_case_requires_expected_citations_for_retrieval_case(self):
        case = EvaluationCase(
            id="eval_case_1",
            case_type=EvaluationCaseType.RETRIEVAL_RECALL,
            name="Bank document retention",
            query="банк документы",
            expected_citation_ids=("citation_1",),
            expected_document_version_ids=("version_1",),
            source="golden_fixture",
        )

        self.assertEqual(case.expected_citation_ids, ("citation_1",))
        self.assertEqual(case.expected_document_version_ids, ("version_1",))
        self.assertEqual(case.input_hash, compute_sha256("банк документы"))

    def test_evaluation_case_rejects_empty_expected_citations_for_grounding_case(self):
        with self.assertRaises(ValueError):
            EvaluationCase(
                id="eval_case_invalid",
                case_type=EvaluationCaseType.ANSWER_GROUNDING,
                name="Invalid grounding",
                query="question",
                expected_citation_ids=(),
            )

    def test_evaluation_result_records_pass_fail_and_observed_citations(self):
        result = EvaluationResult(
            id="eval_result_1",
            case_id="eval_case_1",
            status=EvaluationStatus.PASSED,
            observed_citation_ids=("citation_1",),
            observed_model_run_id="model_run_1",
            score=1.0,
            notes="All expected citations retrieved.",
        )

        self.assertEqual(result.status, EvaluationStatus.PASSED)
        self.assertEqual(result.observed_citation_ids, ("citation_1",))
        self.assertEqual(result.score, 1.0)

    def test_evaluation_result_rejects_invalid_score(self):
        with self.assertRaises(ValueError):
            EvaluationResult(
                id="eval_result_bad",
                case_id="eval_case_1",
                status=EvaluationStatus.FAILED,
                observed_citation_ids=("citation_1",),
                score=1.5,
            )

    def test_evaluation_models_are_immutable(self):
        case = EvaluationCase(
            id="eval_case_immutable",
            case_type=EvaluationCaseType.CITATION_ACCURACY,
            name="Citation accuracy",
            query="question",
            expected_citation_ids=("citation_1",),
        )

        with self.assertRaises(FrozenInstanceError):
            case.name = "Changed"


if __name__ == "__main__":
    unittest.main()
