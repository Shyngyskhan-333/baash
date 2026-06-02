import unittest

from src.evidence.models import compute_sha256
from src.ingestion.citation_builder import ParsedCitationBuilder
from src.ingestion.parser import SourceParser
from src.evidence.models import SourceSnapshot


class ParsedCitationBuilderTests(unittest.TestCase):
    def test_build_creates_articles_clauses_and_citations_from_parsed_structure(self):
        html = """
        <section class="article" data-article-number="1">
          <h2>Статья 1. Основные понятия</h2>
          <p>1. Первый пункт закона.</p>
          <p>2. Второй пункт закона.</p>
        </section>
        """
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000006",
            content=html,
            raw_content_uri="data/raw/K000000006.html",
        )
        parsed = SourceParser().parse(snapshot=snapshot, raw_content=html)

        bundle = ParsedCitationBuilder().build(
            parsed=parsed,
            document_version_id="version_K000000006_current",
            citation_title="Structured Law",
        )

        self.assertEqual(len(bundle.articles), 1)
        self.assertEqual(len(bundle.clauses), 2)
        self.assertEqual(len(bundle.citations), 2)
        self.assertEqual(bundle.articles[0].number, "1")
        self.assertEqual(bundle.articles[0].text_hash, compute_sha256(bundle.articles[0].text))
        self.assertEqual(bundle.clauses[0].path, "article:1/clause:1")
        self.assertEqual(bundle.clauses[0].text, "Первый пункт закона.")
        self.assertEqual(bundle.citations[0].quote, "Первый пункт закона.")
        self.assertEqual(bundle.citations[0].article_id, bundle.articles[0].id)
        self.assertEqual(bundle.citations[0].clause_id, bundle.clauses[0].id)
        self.assertEqual(bundle.citations[0].start_offset, 3)
        self.assertEqual(bundle.citations[0].end_offset, 23)
        self.assertIn("Article 1", bundle.citations[0].citation_label)

    def test_build_is_stable_for_same_parsed_structure(self):
        html = """
        <section class="article" data-article-number="1">
          <h2>Статья 1. Основные понятия</h2>
          <p>1. Первый пункт закона.</p>
        </section>
        """
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000007",
            content=html,
            raw_content_uri="data/raw/K000000007.html",
        )
        parsed = SourceParser().parse(snapshot=snapshot, raw_content=html)
        builder = ParsedCitationBuilder()

        first = builder.build(parsed=parsed, document_version_id="version_1", citation_title="Law")
        second = builder.build(parsed=parsed, document_version_id="version_1", citation_title="Law")

        self.assertEqual(first.articles[0].id, second.articles[0].id)
        self.assertEqual(first.clauses[0].id, second.clauses[0].id)
        self.assertEqual(first.citations[0].id, second.citations[0].id)

    def test_build_rejects_metadata_only_parse(self):
        html = "<html><title>Metadata Only</title></html>"
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000008",
            content=html,
            raw_content_uri="data/raw/K000000008.html",
        )
        parsed = SourceParser().parse(snapshot=snapshot, raw_content=html)

        with self.assertRaises(ValueError):
            ParsedCitationBuilder().build(
                parsed=parsed,
                document_version_id="version_K000000008_current",
                citation_title="Metadata Only",
            )


if __name__ == "__main__":
    unittest.main()
