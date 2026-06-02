import unittest

from src.evidence.citation_accuracy_evaluation import CitationAccuracyEvaluationService
from src.evidence.evaluation import EvaluationCase, EvaluationCaseType, EvaluationStatus


class FakeSearchService:
    def __init__(self, results):
        self.results = results

    def search(self, query, *, top_k=10, doc_ids=None):
        self.query = query
        self.top_k = top_k
        self.doc_ids = doc_ids
        return {"results": self.results}


class CitationAccuracyEvaluationServiceTests(unittest.TestCase):
    def test_evaluate_passes_when_citation_quote_and_version_match_expectations(self):
        result = {
            "citation_id": "citation_1",
            "citation_quote": "Банк обязан хранить документы.",
            "document_version_id": "version_1",
        }
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.CITATION_ACCURACY,
            name="Citation accuracy",
            query="банк документы",
            expected_citation_ids=("citation_1",),
            expected_document_version_ids=("version_1",),
        )

        evaluation = CitationAccuracyEvaluationService(FakeSearchService([result])).evaluate(
            case,
            expected_quotes={"citation_1": "Банк обязан хранить документы."},
        )

        self.assertEqual(evaluation.status, EvaluationStatus.PASSED)
        self.assertEqual(evaluation.observed_citation_ids, ("citation_1",))
        self.assertEqual(evaluation.score, 1.0)

    def test_evaluate_fails_when_quote_does_not_match(self):
        result = {
            "citation_id": "citation_1",
            "citation_quote": "Wrong quote.",
            "document_version_id": "version_1",
        }
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.CITATION_ACCURACY,
            name="Citation quote mismatch",
            query="банк документы",
            expected_citation_ids=("citation_1",),
            expected_document_version_ids=("version_1",),
        )

        evaluation = CitationAccuracyEvaluationService(FakeSearchService([result])).evaluate(
            case,
            expected_quotes={"citation_1": "Банк обязан хранить документы."},
        )

        self.assertEqual(evaluation.status, EvaluationStatus.FAILED)
        self.assertEqual(evaluation.score, 0.0)
        self.assertIn("quote mismatch", evaluation.notes)

    def test_evaluate_fails_when_document_version_does_not_match(self):
        result = {
            "citation_id": "citation_1",
            "citation_quote": "Банк обязан хранить документы.",
            "document_version_id": "version_wrong",
        }
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.CITATION_ACCURACY,
            name="Citation version mismatch",
            query="банк документы",
            expected_citation_ids=("citation_1",),
            expected_document_version_ids=("version_1",),
        )

        evaluation = CitationAccuracyEvaluationService(FakeSearchService([result])).evaluate(
            case,
            expected_quotes={"citation_1": "Банк обязан хранить документы."},
        )

        self.assertEqual(evaluation.status, EvaluationStatus.FAILED)
        self.assertEqual(evaluation.score, 0.0)
        self.assertIn("version mismatch", evaluation.notes)

    def test_evaluate_rejects_non_citation_accuracy_case(self):
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.RETRIEVAL_RECALL,
            name="Wrong type",
            query="банк документы",
            expected_citation_ids=("citation_1",),
        )

        with self.assertRaises(ValueError):
            CitationAccuracyEvaluationService(FakeSearchService([])).evaluate(case, expected_quotes={})


if __name__ == "__main__":
    unittest.main()
