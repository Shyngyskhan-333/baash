import unittest
from dataclasses import replace

from src.evidence.evaluation import EvaluationCase, EvaluationCaseType, EvaluationStatus
from src.evidence.grounding_evaluation import GroundingEvaluationService
from src.evidence.memory_repository import InMemoryEvidenceRepository
from src.ingestion.service import EvidenceIngestionService
from src.ingestion.snapshot import FetchedSourceContent
from src.search.canonical_grounding import CanonicalSearchGroundingService


def _grounded_output():
    html = """
    <html>
      <head><title>Grounding Eval Law</title></head>
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
        url="https://adilet.zan.kz/rus/docs/K000000031",
        content=html,
        raw_content_uri="data/raw/K000000031.html",
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
        packet_title="Grounding Evaluation",
        packet_purpose="answer grounding evaluation",
    )
    return grounded, bundle


class GroundingEvaluationServiceTests(unittest.TestCase):
    def test_evaluate_passes_when_grounded_output_matches_expected_citations(self):
        grounded, bundle = _grounded_output()
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.ANSWER_GROUNDING,
            name="Grounded answer",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
        )

        result = GroundingEvaluationService().evaluate(case, grounded)

        self.assertEqual(result.status, EvaluationStatus.PASSED)
        self.assertEqual(result.observed_citation_ids, (bundle.citations[0].id,))
        self.assertEqual(result.observed_model_run_id, grounded.model_run.id)
        self.assertEqual(result.score, 1.0)

    def test_evaluate_fails_when_grounded_output_has_unexpected_citation(self):
        grounded, bundle = _grounded_output()
        tampered_model_run = replace(grounded.model_run, input_citation_ids=("citation_unexpected",))
        tampered = replace(grounded, model_run=tampered_model_run)
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.ANSWER_GROUNDING,
            name="Grounded answer mismatch",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
        )

        result = GroundingEvaluationService().evaluate(case, tampered)

        self.assertEqual(result.status, EvaluationStatus.FAILED)
        self.assertEqual(result.observed_citation_ids, ("citation_unexpected",))
        self.assertEqual(result.score, 0.0)
        self.assertIn("unexpected citations", result.notes)

    def test_evaluate_fails_when_packet_does_not_link_model_run(self):
        grounded, bundle = _grounded_output()
        tampered_packet = replace(grounded.evidence_packet.packet, model_run_ids=())
        tampered_bundle = replace(grounded.evidence_packet, packet=tampered_packet)
        tampered = replace(grounded, evidence_packet=tampered_bundle)
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.ANSWER_GROUNDING,
            name="Missing model run link",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
        )

        result = GroundingEvaluationService().evaluate(case, tampered)

        self.assertEqual(result.status, EvaluationStatus.FAILED)
        self.assertIn("packet missing model run", result.notes)

    def test_evaluate_rejects_non_grounding_case(self):
        grounded, bundle = _grounded_output()
        case = EvaluationCase.create(
            case_type=EvaluationCaseType.RETRIEVAL_RECALL,
            name="Wrong type",
            query="банк документы",
            expected_citation_ids=(bundle.citations[0].id,),
        )

        with self.assertRaises(ValueError):
            GroundingEvaluationService().evaluate(case, grounded)


if __name__ == "__main__":
    unittest.main()
