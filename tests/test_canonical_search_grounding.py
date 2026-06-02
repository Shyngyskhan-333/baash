import unittest

from src.evidence.memory_repository import InMemoryEvidenceRepository
from src.ingestion.service import EvidenceIngestionService
from src.ingestion.snapshot import FetchedSourceContent
from src.search.canonical_grounding import CanonicalSearchGroundingService


def _repository_with_bundle():
    html = """
    <html>
      <head><title>Grounding Law</title></head>
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
        url="https://adilet.zan.kz/rus/docs/K000000028",
        content=html,
        raw_content_uri="data/raw/K000000028.html",
    )
    bundle = EvidenceIngestionService().ingest_fetched(fetched)
    repository = InMemoryEvidenceRepository()
    repository.add_ingestion_bundle(bundle)
    return repository, bundle


class CanonicalSearchGroundingServiceTests(unittest.TestCase):
    def test_ground_answer_links_model_run_packet_citations_and_snapshot(self):
        repository, bundle = _repository_with_bundle()

        grounded = CanonicalSearchGroundingService.from_repository(repository).ground_answer(
            query="банк документы",
            answer="The cited source says the bank must keep documents.",
            model_name="mock",
            model_version="test",
            messages=[{"role": "user", "content": "What must the bank keep?"}],
            packet_title="Canonical Grounding",
            packet_purpose="canonical legal research",
            system_prompt="Answer only from citations.",
            parameters={"temperature": 0},
        )

        self.assertEqual(grounded.answer, "The cited source says the bank must keep documents.")
        self.assertEqual(grounded.model_run.input_citation_ids, (bundle.citations[0].id,))
        self.assertEqual(grounded.evidence_packet.packet.citation_ids, (bundle.citations[0].id,))
        self.assertEqual(grounded.evidence_packet.packet.model_run_ids, (grounded.model_run.id,))
        self.assertEqual(grounded.evidence_packet.packet.source_snapshot_ids, (bundle.snapshot.id,))

    def test_ground_answer_rejects_query_without_cited_results(self):
        repository, _ = _repository_with_bundle()

        with self.assertRaises(ValueError):
            CanonicalSearchGroundingService.from_repository(repository).ground_answer(
                query="энергетика",
                answer="Ungrounded conclusion.",
                model_name="mock",
                model_version="test",
                messages=[{"role": "user", "content": "What about energy?"}],
                packet_title="Invalid",
                packet_purpose="canonical legal research",
            )


if __name__ == "__main__":
    unittest.main()
