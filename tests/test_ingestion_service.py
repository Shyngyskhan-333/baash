import unittest

from src.ingestion.service import EvidenceIngestionService
from src.ingestion.snapshot import FetchedSourceContent


class EvidenceIngestionServiceTests(unittest.TestCase):
    def test_ingest_fetched_content_builds_coherent_evidence_bundle(self):
        html = """
        <html>
          <head><title>Structured Law</title></head>
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
            url="https://adilet.zan.kz/rus/docs/K000000014",
            content=html,
            raw_content_uri="data/raw/K000000014.html",
            http_status=200,
            fetch_method="test_fixture",
        )

        bundle = EvidenceIngestionService().ingest_fetched(fetched)

        self.assertEqual(bundle.snapshot.source_id, "adilet")
        self.assertIsNone(bundle.snapshot.parser_version)
        self.assertEqual(bundle.parsed.source_snapshot_id, bundle.snapshot.id)
        self.assertEqual(bundle.document.external_id, "K000000014")
        self.assertEqual(bundle.version.document_id, bundle.document.id)
        self.assertEqual(bundle.version.source_snapshot_id, bundle.snapshot.id)
        self.assertEqual(bundle.articles[0].document_version_id, bundle.version.id)
        self.assertEqual(bundle.clauses[0].article_id, bundle.articles[0].id)
        self.assertEqual(bundle.citations[0].document_version_id, bundle.version.id)
        self.assertEqual(bundle.citations[0].clause_id, bundle.clauses[0].id)
        self.assertEqual(bundle.chunks[0].citation_id, bundle.citations[0].id)
        self.assertEqual(bundle.chunks[0].document_version_id, bundle.version.id)
        self.assertEqual(len(bundle.citations), 2)
        self.assertEqual(len(bundle.chunks), 2)

    def test_ingest_fetched_content_rejects_metadata_only_content(self):
        fetched = FetchedSourceContent(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000015",
            content="<html><title>Metadata Only</title></html>",
            raw_content_uri="data/raw/K000000015.html",
        )

        with self.assertRaises(ValueError):
            EvidenceIngestionService().ingest_fetched(fetched)

    def test_ingest_fetched_content_is_stable_for_same_content(self):
        html = """
        <section class="article" data-article-number="1">
          <h2>Статья 1. Основные понятия</h2>
          <p>1. Первый пункт закона.</p>
        </section>
        """
        fetched = FetchedSourceContent(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000016",
            content=html,
            raw_content_uri="data/raw/K000000016.html",
        )
        service = EvidenceIngestionService()

        first = service.ingest_fetched(fetched)
        second = service.ingest_fetched(fetched)

        self.assertEqual(first.snapshot.id, second.snapshot.id)
        self.assertEqual(first.version.id, second.version.id)
        self.assertEqual(first.citations[0].id, second.citations[0].id)
        self.assertEqual(first.chunks[0].id, second.chunks[0].id)


if __name__ == "__main__":
    unittest.main()
