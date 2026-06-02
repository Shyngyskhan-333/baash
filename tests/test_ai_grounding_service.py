import unittest

from src.evidence.ai_grounding import AIGroundingService
from src.evidence.models import compute_sha256


class AIGroundingServiceTests(unittest.TestCase):
    def test_ground_answer_creates_model_run_and_evidence_packet(self):
        service = AIGroundingService()
        evidence_result = {
            "document_version_id": "version_1",
            "citation_id": "citation_1",
            "citation_label": "Test Law, Article 1",
            "citation_quote": "Citizens may submit petitions.",
            "chunk_id": "chunk_1",
        }

        grounded = service.ground_answer(
            answer="The draft should be reviewed against Article 1.",
            model_name="mock",
            model_version="test",
            messages=[{"role": "user", "content": "Can citizens submit petitions?"}],
            system_prompt="Answer only from citations.",
            evidence_results=[evidence_result],
            packet_title="Grounded Answer",
            packet_purpose="legal research copilot",
            parameters={"temperature": 0.1},
        )

        self.assertEqual(grounded.answer, "The draft should be reviewed against Article 1.")
        self.assertEqual(grounded.model_run.input_citation_ids, ("citation_1",))
        self.assertEqual(grounded.model_run.output_hash, compute_sha256(grounded.answer))
        self.assertEqual(grounded.evidence_packet.packet.model_run_ids, (grounded.model_run.id,))
        self.assertEqual(grounded.evidence_packet.packet.citation_ids, ("citation_1",))
        self.assertEqual(grounded.evidence_packet.citations[0].quote, "Citizens may submit petitions.")

    def test_ground_answer_rejects_output_without_citations(self):
        service = AIGroundingService()

        with self.assertRaises(ValueError):
            service.ground_answer(
                answer="Ungrounded legal conclusion.",
                model_name="mock",
                model_version="test",
                messages=[{"role": "user", "content": "What is the law?"}],
                evidence_results=[],
                packet_title="Invalid",
                packet_purpose="legal research copilot",
            )

    def test_same_grounded_answer_has_stable_model_run_id(self):
        service = AIGroundingService()
        kwargs = {
            "answer": "Cited answer.",
            "model_name": "mock",
            "model_version": "test",
            "messages": [{"role": "user", "content": "Question"}],
            "evidence_results": [
                {
                    "document_version_id": "version_1",
                    "citation_id": "citation_1",
                    "citation_label": "Doc, Article 1",
                    "citation_quote": "Quoted legal text.",
                }
            ],
            "packet_title": "Packet",
            "packet_purpose": "research",
        }

        first = service.ground_answer(**kwargs)
        second = service.ground_answer(**kwargs)

        self.assertEqual(first.model_run.id, second.model_run.id)
        self.assertEqual(first.model_run.prompt_hash, second.model_run.prompt_hash)
        self.assertEqual(first.evidence_packet.packet.packet_hash, second.evidence_packet.packet.packet_hash)


if __name__ == "__main__":
    unittest.main()
