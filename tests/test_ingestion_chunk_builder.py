import unittest

from src.evidence.models import Citation, compute_sha256
from src.ingestion.chunk_builder import CitationChunkBuilder


class CitationChunkBuilderTests(unittest.TestCase):
    def test_build_creates_semantic_chunks_from_citations(self):
        citation = Citation(
            id="citation_1",
            document_version_id="version_1",
            article_id="article_1",
            clause_id="clause_1",
            quote="Первый пункт закона.",
            citation_label="Law, Article 1, Clause 1",
            start_offset=3,
            end_offset=23,
        )

        chunks = CitationChunkBuilder().build(citations=(citation,))

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].document_version_id, "version_1")
        self.assertEqual(chunks[0].text, "Первый пункт закона.")
        self.assertEqual(chunks[0].chunk_hash, compute_sha256("Первый пункт закона."))
        self.assertEqual(chunks[0].citation_id, "citation_1")
        self.assertEqual(chunks[0].article_id, "article_1")
        self.assertEqual(chunks[0].clause_id, "clause_1")
        self.assertEqual(chunks[0].start_offset, 3)
        self.assertEqual(chunks[0].end_offset, 23)
        self.assertEqual(chunks[0].strategy, "citation_clause_chunks")

    def test_build_is_stable_for_same_citations(self):
        citation = Citation(
            id="citation_1",
            document_version_id="version_1",
            article_id="article_1",
            clause_id="clause_1",
            quote="Первый пункт закона.",
            citation_label="Law, Article 1, Clause 1",
        )
        builder = CitationChunkBuilder()

        first = builder.build(citations=(citation,))
        second = builder.build(citations=(citation,))

        self.assertEqual(first[0].id, second[0].id)

    def test_build_rejects_empty_citation_list(self):
        with self.assertRaises(ValueError):
            CitationChunkBuilder().build(citations=())


if __name__ == "__main__":
    unittest.main()
