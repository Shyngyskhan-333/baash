import unittest

from src.search.service import SearchService


class FakeRetriever:
    def search_hybrid(self, query, top_k=10, doc_ids=None):
        self.query = query
        self.top_k = top_k
        self.doc_ids = doc_ids
        return [
            {
                "doc_id": "K000000001",
                "doc_title": "Test Law",
                "article_number": "Статья 1",
                "chunk_id": "K000000001_1_0",
                "text": "Граждане имеют право на обращение.",
                "rrf_score": 0.1,
            }
        ]


class SearchServiceTests(unittest.TestCase):
    def test_search_preserves_legacy_fields_and_adds_citation_fields(self):
        retriever = FakeRetriever()
        service = SearchService(retriever)

        response = service.search("обращение", top_k=5, doc_ids=["K000000001"])

        self.assertEqual(retriever.query, "обращение")
        self.assertEqual(retriever.top_k, 80)
        self.assertEqual(retriever.doc_ids, ["K000000001"])
        self.assertEqual(len(response["results"]), 1)
        result = response["results"][0]
        self.assertEqual(result["doc_id"], "K000000001")
        self.assertEqual(result["doc_title"], "Test Law")
        self.assertEqual(result["article_number"], "Статья 1")
        self.assertEqual(result["chunk_id"], "K000000001_1_0")
        self.assertTrue(result["citation_id"].startswith("citation_"))
        self.assertTrue(result["document_version_id"].startswith("version_"))
        self.assertIn("Test Law", result["citation_label"])
        self.assertIn("Статья 1", result["citation_label"])
        self.assertEqual(result["citation_quote"], "Граждане имеют право на обращение.")

    def test_search_applies_legacy_doc_id_filter_after_broad_search(self):
        class FilteringRetriever:
            def search_hybrid(self, query, top_k=10, doc_ids=None):
                return [
                    {"doc_id": "A", "doc_title": "A", "article_number": "1", "chunk_id": "a", "text": "a"},
                    {"doc_id": "B", "doc_title": "B", "article_number": "1", "chunk_id": "b", "text": "b"},
                ]

        response = SearchService(FilteringRetriever()).search(
            "query",
            top_k=10,
            filters={"doc_id": "B"},
        )

        self.assertEqual([result["doc_id"] for result in response["results"]], ["B"])


if __name__ == "__main__":
    unittest.main()
