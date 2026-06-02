import unittest

from api.models.schemas import AnalyzeResponse
from src.evidence.analyze_grounding import build_analyze_evidence_results, ground_analyze_summary


class AnalyzeGroundingTests(unittest.TestCase):
    def test_build_analyze_evidence_results_creates_citations_from_legacy_doc(self):
        doc = {
            "title": "Test Law",
            "articles": [
                {
                    "article_number": "Article 1",
                    "chunks": [
                        {"chunk_id": "chunk_1", "text": "First cited legal text."},
                        {"chunk_id": "chunk_2", "text": "Second cited legal text."},
                    ],
                }
            ],
        }

        results = build_analyze_evidence_results("K000000001", doc, max_results=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["doc_id"], "K000000001")
        self.assertEqual(results[0]["doc_title"], "Test Law")
        self.assertEqual(results[0]["article_number"], "Article 1")
        self.assertEqual(results[0]["chunk_id"], "chunk_1")
        self.assertEqual(results[0]["citation_quote"], "First cited legal text.")
        self.assertTrue(results[0]["citation_id"].startswith("citation_"))

    def test_ground_analyze_summary_returns_candidate_metadata(self):
        doc = {
            "title": "Test Law",
            "articles": [{"article_number": "Article 1", "text": "A cited legal basis."}],
        }

        metadata = ground_analyze_summary(
            doc_id="K000000001",
            title="Test Law",
            doc=doc,
            summary="[Semantic analysis] Candidate summary.",
            messages=[{"role": "user", "content": "Analyze this document."}],
            system_prompt="Use only supplied evidence.",
            model_name="mock",
            model_version="test",
        )

        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual(metadata["status"], "candidate")
        self.assertEqual(metadata["validation_status"], "not_human_validated")
        self.assertTrue(metadata["model_run_id"].startswith("model_run_"))
        self.assertTrue(metadata["evidence_packet_id"].startswith("packet_"))
        self.assertEqual(len(metadata["citation_ids"]), 1)
        self.assertEqual(metadata["legal_claim_notice"], "AI-generated summary; not a validated legal conclusion.")

    def test_ground_analyze_summary_returns_none_when_no_citable_text_exists(self):
        metadata = ground_analyze_summary(
            doc_id="K000000001",
            title="Empty Law",
            doc={"title": "Empty Law", "articles": []},
            summary="No evidence.",
            messages=[{"role": "user", "content": "Analyze this document."}],
        )

        self.assertIsNone(metadata)

    def test_analyze_response_accepts_optional_grounding_metadata(self):
        response = AnalyzeResponse(
            doc_id="K000000001",
            title="Test Law",
            risk_score=0.0,
            risk_level="medium",
            issues=[],
            summary="[Semantic analysis] Candidate summary.",
            related_laws=[],
            grounding={
                "status": "candidate",
                "validation_status": "not_human_validated",
                "citation_ids": ["citation_1"],
            },
        )

        self.assertEqual(response.grounding["status"], "candidate")


if __name__ == "__main__":
    unittest.main()
