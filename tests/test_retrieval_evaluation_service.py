import unittest

from src.evidence.evaluation import EvaluationCase, EvaluationCaseType, EvaluationStatus
from src.evidence.memory_repository import InMemoryEvidenceRepository
from src.evidence.retrieval_evaluation import RetrievalEvaluationService
from src.ingestion.service import EvidenceIngestionService
from src.ingestion.snapshot import FetchedSourceContent
from src.search.canonical_service import CanonicalSearchService


def _bundle(doc_id: str, title: str, paragraph: str):
    html = f"""
    <html>
      <head><title>{title}</title></head>
      <body>
        <section class="article" data-article-number="1">
          <h2>Статья 1. Основные понятия</h2>
          <p>1. {paragraph}</p>
        </section>
      </body>
    </html>
    """
    fetched = FetchedSourceContent(
        source_id="adilet",
        url=f"https://adilet.zan.kz/rus/docs/{doc_id}",
        content=html,
        raw_content_uri=f"data/raw/{doc_id}.html",
    )
    return EvidenceIngestionService().ingest_fetched(fetched)


class RetrievalEvaluationServiceTests(unittest.TestCase):
    def test_evaluate_retrieval_case_passes_when_expected_citation_found(self):
        repository = InMemoryEvidenceRepository()
        bundle = _bundle("K000000029", "Evaluation Law", "Банк обязан хранить документы.")
        repository.add_ingestion_bundle(bundle)
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.RETRIEVAL_RECALL,
            name="Bank documents",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
            expected_document_version_ids=(bundle.version.id,),
        )

        result = RetrievalEvaluationService(CanonicalSearchService.from_repository(repository)).evaluate(case)

        self.assertEqual(result.case_id, case.id)
        self.assertEqual(result.status, EvaluationStatus.PASSED)
        self.assertEqual(result.observed_citation_ids, (bundle.citations[0].id,))
        self.assertEqual(result.score, 1.0)

    def test_evaluate_retrieval_case_fails_with_partial_or_missing_recall(self):
        repository = InMemoryEvidenceRepository()
        bundle = _bundle("K000000030", "Evaluation Miss Law", "Банк обязан хранить документы.")
        repository.add_ingestion_bundle(bundle)
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.RETRIEVAL_RECALL,
            name="Missing expected citation",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id, "citation_missing"),
        )

        result = RetrievalEvaluationService(CanonicalSearchService.from_repository(repository)).evaluate(case)

        self.assertEqual(result.status, EvaluationStatus.FAILED)
        self.assertEqual(result.observed_citation_ids, (bundle.citations[0].id,))
        self.assertEqual(result.score, 0.5)
        self.assertIn("1/2", result.notes)

    def test_evaluate_rejects_non_retrieval_case(self):
        repository = InMemoryEvidenceRepository()
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.ANSWER_GROUNDING,
            name="Wrong type",
            query="банк документы",
            expected_citation_ids=("citation_1",),
        )

        with self.assertRaises(ValueError):
            RetrievalEvaluationService(CanonicalSearchService.from_repository(repository)).evaluate(case)


if __name__ == "__main__":
    unittest.main()
