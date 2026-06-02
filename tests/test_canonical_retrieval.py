import unittest

from src.evidence.memory_repository import InMemoryEvidenceRepository
from src.ingestion.service import EvidenceIngestionService
from src.ingestion.snapshot import FetchedSourceContent
from src.search.canonical_retrieval import InMemoryCanonicalRetrievalIndex


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


class InMemoryCanonicalRetrievalIndexTests(unittest.TestCase):
    def test_search_returns_matching_canonical_chunks(self):
        repository = InMemoryEvidenceRepository()
        bundle = _bundle("K000000018", "Search Law", "Банк обязан хранить документы.")
        repository.add_ingestion_bundle(bundle)

        results = InMemoryCanonicalRetrievalIndex(repository).search("банк документы", top_k=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].citation_id, bundle.citations[0].id)
        self.assertEqual(results[0].document_version_id, bundle.version.id)

    def test_search_orders_results_by_simple_token_score_then_stable_id(self):
        repository = InMemoryEvidenceRepository()
        weak = _bundle("K000000019", "Weak Law", "Банк раскрывает информацию.")
        strong = _bundle("K000000020", "Strong Law", "Банк хранит документы банка.")
        repository.add_ingestion_bundle(weak)
        repository.add_ingestion_bundle(strong)

        results = InMemoryCanonicalRetrievalIndex(repository).search("банк документы", top_k=2)

        self.assertEqual(results[0].citation_id, strong.citations[0].id)
        self.assertEqual(results[1].citation_id, weak.citations[0].id)

    def test_search_filters_by_document_id(self):
        repository = InMemoryEvidenceRepository()
        first = _bundle("K000000021", "First Law", "Банк хранит документы.")
        second = _bundle("K000000022", "Second Law", "Банк хранит документы.")
        repository.add_ingestion_bundle(first)
        repository.add_ingestion_bundle(second)

        results = InMemoryCanonicalRetrievalIndex(repository).search("банк документы", doc_ids=[second.document.id])

        self.assertEqual([chunk.citation_id for chunk in results], [second.citations[0].id])

    def test_search_rejects_empty_query(self):
        repository = InMemoryEvidenceRepository()

        with self.assertRaises(ValueError):
            InMemoryCanonicalRetrievalIndex(repository).search("   ")


if __name__ == "__main__":
    unittest.main()
