import unittest

from src.evidence.models import LegalDocumentStatus, SourceSnapshot, compute_sha256
from src.ingestion.document_builder import ParsedDocumentVersionBuilder
from src.ingestion.parser import SourceParser


class ParsedDocumentVersionBuilderTests(unittest.TestCase):
    def test_build_creates_document_and_version_from_citable_parse(self):
        html = """
        <html>
          <head><title>Structured Law</title></head>
          <body>
            <section class="article" data-article-number="1">
              <h2>Статья 1. Основные понятия</h2>
              <p>1. Первый пункт закона.</p>
            </section>
          </body>
        </html>
        """
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000009",
            content=html,
            raw_content_uri="data/raw/K000000009.html",
        )
        parsed = SourceParser().parse(snapshot=snapshot, raw_content=html)

        bundle = ParsedDocumentVersionBuilder().build(parsed=parsed, snapshot=snapshot)

        self.assertEqual(bundle.document.external_id, "K000000009")
        self.assertEqual(bundle.document.title, "Structured Law")
        self.assertEqual(bundle.document.jurisdiction, "KZ")
        self.assertEqual(bundle.document.document_type, "legal_act")
        self.assertEqual(bundle.document.canonical_source_id, "adilet")
        self.assertEqual(bundle.version.document_id, bundle.document.id)
        self.assertEqual(bundle.version.source_snapshot_id, snapshot.id)
        self.assertEqual(bundle.version.version_label, "source-parser-v1")
        self.assertEqual(bundle.version.status, LegalDocumentStatus.UNKNOWN)
        self.assertEqual(bundle.version.text_hash, compute_sha256("1. Первый пункт закона."))

    def test_build_is_stable_for_same_parsed_document_and_snapshot(self):
        html = """
        <section class="article" data-article-number="1">
          <h2>Статья 1. Основные понятия</h2>
          <p>1. Первый пункт закона.</p>
        </section>
        """
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000010",
            content=html,
            raw_content_uri="data/raw/K000000010.html",
        )
        parsed = SourceParser().parse(snapshot=snapshot, raw_content=html)
        builder = ParsedDocumentVersionBuilder()

        first = builder.build(parsed=parsed, snapshot=snapshot)
        second = builder.build(parsed=parsed, snapshot=snapshot)

        self.assertEqual(first.document.id, second.document.id)
        self.assertEqual(first.version.id, second.version.id)

    def test_build_rejects_metadata_only_parse(self):
        html = "<html><title>Metadata Only</title></html>"
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000011",
            content=html,
            raw_content_uri="data/raw/K000000011.html",
        )
        parsed = SourceParser().parse(snapshot=snapshot, raw_content=html)

        with self.assertRaises(ValueError):
            ParsedDocumentVersionBuilder().build(parsed=parsed, snapshot=snapshot)

    def test_build_rejects_snapshot_mismatch(self):
        html = """
        <section class="article" data-article-number="1">
          <h2>Статья 1. Основные понятия</h2>
          <p>1. Первый пункт закона.</p>
        </section>
        """
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000012",
            content=html,
            raw_content_uri="data/raw/K000000012.html",
        )
        other_snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000013",
            content=html,
            raw_content_uri="data/raw/K000000013.html",
        )
        parsed = SourceParser().parse(snapshot=snapshot, raw_content=html)

        with self.assertRaises(ValueError):
            ParsedDocumentVersionBuilder().build(parsed=parsed, snapshot=other_snapshot)


if __name__ == "__main__":
    unittest.main()
