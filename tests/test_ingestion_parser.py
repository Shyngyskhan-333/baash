import unittest

from src.evidence.models import SourceSnapshot
from src.ingestion.parser import SourceParser


class SourceParserTests(unittest.TestCase):
    def test_parser_returns_metadata_only_document_without_side_effects(self):
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000001",
            content="<html><head><title>Test Law</title></head><body>01.01.2026</body></html>",
            raw_content_uri="data/raw/K000000001.html",
            fetch_method="mock_http",
        )

        parsed = SourceParser().parse(
            snapshot=snapshot,
            raw_content="<html><head><title>Test Law</title></head><body>01.01.2026</body></html>",
        )

        self.assertEqual(parsed.source_snapshot_id, snapshot.id)
        self.assertEqual(parsed.doc_id, "K000000001")
        self.assertEqual(parsed.title, "Test Law")
        self.assertEqual(parsed.url, snapshot.url)
        self.assertEqual(parsed.date, "01.01.2026")
        self.assertEqual(parsed.parse_quality, "metadata_only")
        self.assertFalse(parsed.legal_text_available)
        self.assertEqual(parsed.articles, ())
        self.assertEqual(parsed.references, ())

    def test_parser_extracts_article_and_clause_structure_when_available(self):
        html = """
        <html>
          <head><title>Structured Law</title></head>
          <body>
            <section class="article" data-article-number="1">
              <h2>Статья 1. Основные понятия</h2>
              <p>1. Первый пункт закона.</p>
              <p>2. Второй пункт закона.</p>
            </section>
            <section class="article" data-article-number="2">
              <h2>Статья 2. Полномочия</h2>
              <p>Уполномоченный орган действует в пределах компетенции.</p>
            </section>
          </body>
        </html>
        """
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000005",
            content=html,
            raw_content_uri="data/raw/K000000005.html",
        )

        parsed = SourceParser().parse(snapshot=snapshot, raw_content=html)

        self.assertEqual(parsed.parse_quality, "structured_legal_text")
        self.assertTrue(parsed.legal_text_available)
        self.assertEqual(len(parsed.articles), 2)
        self.assertEqual(parsed.articles[0]["number"], "1")
        self.assertEqual(parsed.articles[0]["title"], "Основные понятия")
        self.assertEqual(parsed.articles[0]["text"], "1. Первый пункт закона.\n2. Второй пункт закона.")
        self.assertEqual(
            parsed.articles[0]["clauses"],
            (
                {"number": "1", "path": "article:1/clause:1", "text": "Первый пункт закона.", "order": 1},
                {"number": "2", "path": "article:1/clause:2", "text": "Второй пункт закона.", "order": 2},
            ),
        )
        self.assertEqual(parsed.articles[1]["number"], "2")
        self.assertEqual(parsed.articles[1]["clauses"][0]["number"], None)
        self.assertEqual(
            parsed.articles[1]["clauses"][0]["path"],
            "article:2/clause:1",
        )

    def test_parser_extracts_references_from_raw_content(self):
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000002",
            content='<a href="/rus/docs/K111111111">ref</a><a href="/rus/docs/Z222222222_">ref</a>',
            raw_content_uri="data/raw/K000000002.html",
        )

        parsed = SourceParser().parse(
            snapshot=snapshot,
            raw_content='<a href="/rus/docs/K111111111">ref</a><a href="/rus/docs/Z222222222_">ref</a>',
        )

        self.assertEqual(parsed.references, ("K111111111", "Z222222222_"))

    def test_parser_rejects_raw_content_that_does_not_match_snapshot_hash(self):
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000003",
            content="<html>original</html>",
            raw_content_uri="data/raw/K000000003.html",
        )

        with self.assertRaises(ValueError):
            SourceParser().parse(snapshot=snapshot, raw_content="<html>changed</html>")

    def test_parser_does_not_mutate_snapshot_parser_version(self):
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000004",
            content="<html>raw</html>",
            raw_content_uri="data/raw/K000000004.html",
        )

        SourceParser().parse(snapshot=snapshot, raw_content="<html>raw</html>")

        self.assertIsNone(snapshot.parser_version)


if __name__ == "__main__":
    unittest.main()
