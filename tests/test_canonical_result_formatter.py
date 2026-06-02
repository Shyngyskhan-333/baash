import unittest

from src.evidence.memory_repository import InMemoryEvidenceRepository
from src.ingestion.service import EvidenceIngestionService
from src.ingestion.snapshot import FetchedSourceContent
from src.search.result_formatter import CanonicalSearchResultFormatter


def _bundle():
    html = """
    <html>
      <head><title>Formatter Law</title></head>
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
        url="https://adilet.zan.kz/rus/docs/K000000023",
        content=html,
        raw_content_uri="data/raw/K000000023.html",
    )
    return EvidenceIngestionService().ingest_fetched(fetched)


class CanonicalSearchResultFormatterTests(unittest.TestCase):
    def test_format_chunk_returns_citation_aware_result_dict(self):
        repository = InMemoryEvidenceRepository()
        bundle = _bundle()
        repository.add_ingestion_bundle(bundle)

        result = CanonicalSearchResultFormatter(repository).format_chunk(bundle.chunks[0], score=2.0)

        self.assertEqual(result["doc_id"], "K000000023")
        self.assertEqual(result["document_id"], bundle.document.id)
        self.assertEqual(result["document_version_id"], bundle.version.id)
        self.assertEqual(result["source_snapshot_id"], bundle.snapshot.id)
        self.assertEqual(result["doc_title"], "Formatter Law")
        self.assertEqual(result["article_number"], "1")
        self.assertEqual(result["article_id"], bundle.articles[0].id)
        self.assertEqual(result["clause_id"], bundle.clauses[0].id)
        self.assertEqual(result["chunk_id"], bundle.chunks[0].id)
        self.assertEqual(result["text"], "Банк обязан хранить документы.")
        self.assertEqual(result["citation_id"], bundle.citations[0].id)
        self.assertEqual(result["citation_label"], bundle.citations[0].citation_label)
        self.assertEqual(result["citation_quote"], bundle.citations[0].quote)
        self.assertEqual(result["score"], 2.0)

    def test_format_chunks_preserves_input_order(self):
        repository = InMemoryEvidenceRepository()
        bundle = _bundle()
        repository.add_ingestion_bundle(bundle)
        formatter = CanonicalSearchResultFormatter(repository)

        results = formatter.format_chunks((bundle.chunks[0],), scores={bundle.chunks[0].id: 3.0})

        self.assertEqual([result["chunk_id"] for result in results], [bundle.chunks[0].id])
        self.assertEqual(results[0]["score"], 3.0)

    def test_format_chunk_rejects_missing_citation(self):
        bundle = _bundle()
        repository = InMemoryEvidenceRepository()
        repository.add_snapshot(bundle.snapshot)
        repository.add_document(bundle.document)
        repository.add_document_version(bundle.version)
        repository.add_chunk(bundle.chunks[0])

        with self.assertRaises(ValueError):
            CanonicalSearchResultFormatter(repository).format_chunk(bundle.chunks[0])


if __name__ == "__main__":
    unittest.main()
