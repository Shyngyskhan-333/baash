import unittest

from src.copilot import (
    CopilotAnswerStatus,
    CopilotGroundingService,
    CopilotUncertainty,
)


class CopilotTests(unittest.TestCase):
    def test_create_grounded_answer_links_model_run_and_evidence_packet(self):
        service = CopilotGroundingService()

        answer = service.create_grounded_answer(
            question="What does Article 1 say?",
            answer_text="Article 1 requires registration before operation.",
            model_name="mock-model",
            model_version="v1",
            messages=[{"role": "user", "content": "What does Article 1 say?"}],
            evidence_results=[
                {
                    "citation_id": "citation_1",
                    "citation_label": "Test Law, Article 1",
                    "citation_quote": "Organizations must register before operation.",
                    "document_version_id": "version_1",
                }
            ],
            uncertainty=CopilotUncertainty.LOW,
        )

        self.assertEqual(answer.status, CopilotAnswerStatus.ANSWERED)
        self.assertEqual(answer.validation_status, "not_human_validated")
        self.assertEqual(answer.question, "What does Article 1 say?")
        self.assertEqual(answer.answer_text, "Article 1 requires registration before operation.")
        self.assertEqual(answer.citation_ids, ("citation_1",))
        self.assertTrue(answer.evidence_packet_id.startswith("packet_"))
        self.assertTrue(answer.model_run_id.startswith("model_run_"))
        self.assertEqual(answer.uncertainty, CopilotUncertainty.LOW)
        self.assertIn("AI-generated research answer", answer.legal_claim_notice)

    def test_refuse_without_citations_does_not_create_model_run_or_packet(self):
        service = CopilotGroundingService()

        answer = service.create_refusal(
            question="Can a bank do this?",
            reason="No cited legal evidence was retrieved.",
        )

        self.assertEqual(answer.status, CopilotAnswerStatus.REFUSED)
        self.assertEqual(answer.uncertainty, CopilotUncertainty.INSUFFICIENT_EVIDENCE)
        self.assertEqual(answer.citation_ids, ())
        self.assertIsNone(answer.evidence_packet_id)
        self.assertIsNone(answer.model_run_id)
        self.assertIn("No cited legal evidence", answer.answer_text)

    def test_grounded_answer_rejects_empty_evidence_results(self):
        service = CopilotGroundingService()

        with self.assertRaises(ValueError):
            service.create_grounded_answer(
                question="What is required?",
                answer_text="A requirement exists.",
                model_name="mock-model",
                model_version="v1",
                messages=[{"role": "user", "content": "What is required?"}],
                evidence_results=[],
            )

    def test_export_answer_includes_traceability_fields(self):
        service = CopilotGroundingService()
        answer = service.create_grounded_answer(
            question="What does Article 1 say?",
            answer_text="Article 1 requires registration before operation.",
            model_name="mock-model",
            model_version="v1",
            messages=[{"role": "user", "content": "What does Article 1 say?"}],
            evidence_results=[
                {
                    "citation_id": "citation_1",
                    "citation_label": "Test Law, Article 1",
                    "citation_quote": "Organizations must register before operation.",
                    "document_version_id": "version_1",
                }
            ],
        )

        exported = service.export_answer(answer)

        self.assertEqual(exported["status"], "answered")
        self.assertEqual(exported["citation_ids"], ["citation_1"])
        self.assertIn("evidence_packet_hash", exported)
        self.assertIn("legal_claim_notice", exported)


if __name__ == "__main__":
    unittest.main()
