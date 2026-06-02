import unittest
from dataclasses import replace

from src.evidence.memory_repository import InMemoryEvidenceRepository
from src.ingestion.service import EvidenceIngestionService
from src.ingestion.snapshot import FetchedSourceContent


def _ingestion_bundle():
    html = """
    <html>
      <head><title>Repository Law</title></head>
      <body>
        <section class="article" data-article-number="1">
          <h2>Статья 1. Основные понятия</h2>
          <p>1. Первый пункт закона.</p>
          <p>2. Второй пункт закона.</p>
        </section>
      </body>
    </html>
    """
    fetched = FetchedSourceContent(
        source_id="adilet",
        url="https://adilet.zan.kz/rus/docs/K000000017",
        content=html,
        raw_content_uri="data/raw/K000000017.html",
    )
    return EvidenceIngestionService().ingest_fetched(fetched)


class InMemoryEvidenceRepositoryTests(unittest.TestCase):
    def test_add_ingestion_bundle_makes_evidence_queryable(self):
        bundle = _ingestion_bundle()
        repository = InMemoryEvidenceRepository()

        repository.add_ingestion_bundle(bundle)

        self.assertEqual(repository.get_snapshot(bundle.snapshot.id), bundle.snapshot)
        self.assertEqual(repository.get_document(bundle.document.id), bundle.document)
        self.assertEqual(repository.get_document_version(bundle.version.id), bundle.version)
        self.assertEqual(repository.list_articles(bundle.version.id), list(bundle.articles))
        self.assertEqual(repository.list_clauses(bundle.articles[0].id), list(bundle.clauses))
        self.assertEqual(repository.get_citation(bundle.citations[0].id), bundle.citations[0])
        self.assertEqual(repository.list_citations_for_version(bundle.version.id), list(bundle.citations))
        self.assertEqual(repository.list_chunks_for_version(bundle.version.id), list(bundle.chunks))

    def test_add_ingestion_bundle_is_idempotent_for_same_bundle(self):
        bundle = _ingestion_bundle()
        repository = InMemoryEvidenceRepository()

        repository.add_ingestion_bundle(bundle)
        repository.add_ingestion_bundle(bundle)

        self.assertEqual(len(repository.list_articles(bundle.version.id)), 1)
        self.assertEqual(len(repository.list_citations_for_version(bundle.version.id)), 2)
        self.assertEqual(len(repository.list_chunks_for_version(bundle.version.id)), 2)

    def test_add_snapshot_rejects_conflicting_duplicate_id(self):
        bundle = _ingestion_bundle()
        repository = InMemoryEvidenceRepository()
        repository.add_snapshot(bundle.snapshot)
        conflicting_snapshot = replace(bundle.snapshot, raw_content_uri="data/raw/conflict.html")

        with self.assertRaises(ValueError):
            repository.add_snapshot(conflicting_snapshot)


if __name__ == "__main__":
    unittest.main()
