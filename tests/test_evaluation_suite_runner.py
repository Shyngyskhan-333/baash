import unittest

from src.evidence.evaluation import EvaluationCase, EvaluationCaseType, EvaluationStatus
from src.evidence.evaluation_suite import EvaluationSuiteRunner
from src.evidence.memory_repository import InMemoryEvidenceRepository
from src.ingestion.service import EvidenceIngestionService
from src.ingestion.snapshot import FetchedSourceContent
from src.search.canonical_grounding import CanonicalSearchGroundingService
from src.search.canonical_service import CanonicalSearchService


def _repository_bundle_and_grounding():
    html = """
    <html>
      <head><title>Suite Law</title></head>
      <body>
        <section class="article" data-article-number="1">
          <h2>Статья 1. Основные понятия</h2>
          <p>1. Банк обязан хранить документы.</p>
        </section>
      </body>
    </html>
    """
    fetched = FetchedSourceContent(
        source_id="adilet",
        url="https://adilet.zan.kz/rus/docs/K000000032",
        content=html,
        raw_content_uri="data/raw/K000000032.html",
    )
    bundle = EvidenceIngestionService().ingest_fetched(fetched)
    repository = InMemoryEvidenceRepository()
    repository.add_ingestion_bundle(bundle)
    grounded = CanonicalSearchGroundingService.from_repository(repository).ground_answer(
        query="банк документы",
        answer="The cited source says the bank must keep documents.",
        model_name="mock",
        model_version="test",
        messages=[{"role": "user", "content": "What must the bank keep?"}],
        packet_title="Suite Grounding",
        packet_purpose="evaluation suite",
    )
    return repository, bundle, grounded


class EvaluationSuiteRunnerTests(unittest.TestCase):
    def test_run_executes_retrieval_citation_and_grounding_cases(self):
        repository, bundle, grounded = _repository_bundle_and_grounding()
        retrieval_case = EvaluationCase.create(
            case_type=EvaluationCaseType.RETRIEVAL_RECALL,
            name="Retrieval case",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
        )
        citation_case = EvaluationCase.create(
            case_type=EvaluationCaseType.CITATION_ACCURACY,
            name="Citation case",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
            expected_document_version_ids=(bundle.version.id,),
        )
        grounding_case = EvaluationCase.create(
            case_type=EvaluationCaseType.ANSWER_GROUNDING,
            name="Grounding case",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
        )

        report = EvaluationSuiteRunner.from_search_service(CanonicalSearchService.from_repository(repository)).run(
            cases=(retrieval_case, citation_case, grounding_case),
            expected_quotes={bundle.citations[0].id: bundle.citations[0].quote},
            grounded_outputs={grounding_case.id: grounded},
        )

        self.assertEqual(report.total_cases, 3)
        self.assertEqual(report.passed_cases, 3)
        self.assertEqual(report.failed_cases, 0)
        self.assertEqual([result.status for result in report.results], [EvaluationStatus.PASSED] * 3)

    def test_run_fails_closed_when_grounding_output_is_missing(self):
        repository, bundle, _ = _repository_bundle_and_grounding()
        grounding_case = EvaluationCase.create(
            case_type=EvaluationCaseType.ANSWER_GROUNDING,
            name="Missing grounding output",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
        )

        with self.assertRaises(ValueError):
            EvaluationSuiteRunner.from_search_service(CanonicalSearchService.from_repository(repository)).run(
                cases=(grounding_case,),
                grounded_outputs={},
            )

    def test_run_rejects_unsupported_case_type(self):
        repository, bundle, _ = _repository_bundle_and_grounding()
        hallucination_case = EvaluationCase.create(
            case_type=EvaluationCaseType.HALLUCINATION,
            name="Unsupported",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
        )

        with self.assertRaises(ValueError):
            EvaluationSuiteRunner.from_search_service(CanonicalSearchService.from_repository(repository)).run(
                cases=(hallucination_case,),
            )


if __name__ == "__main__":
    unittest.main()
