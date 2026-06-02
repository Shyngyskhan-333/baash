import unittest

from src.evidence.packet_service import EvidencePacketService


class EvidencePacketServiceTests(unittest.TestCase):
    def test_build_from_search_results_creates_stable_packet_with_citations(self):
        service = EvidencePacketService()
        result = {
            "doc_id": "K000000001",
            "doc_title": "Test Law",
            "chunk_id": "chunk_1",
            "document_version_id": "version_1",
            "citation_id": "citation_1",
            "citation_label": "Test Law, Article 1",
            "citation_quote": "Citizens may submit petitions.",
        }

        bundle = service.build_from_search_results(
            title="Research Packet",
            purpose="legal research",
            results=[result, result],
            summary="Candidate answer must cite this packet.",
            model_run_ids=("model_run_1",),
        )

        self.assertEqual(bundle.packet.citation_ids, ("citation_1",))
        self.assertEqual(bundle.packet.model_run_ids, ("model_run_1",))
        self.assertEqual(len(bundle.citations), 1)
        self.assertEqual(bundle.citations[0].quote, "Citizens may submit petitions.")
        self.assertEqual(len(bundle.packet.packet_hash), 64)
        self.assertEqual(bundle.packet.packet_hash, bundle.packet.with_computed_hash().packet_hash)

    def test_build_from_search_results_rejects_uncited_results(self):
        service = EvidencePacketService()

        with self.assertRaises(ValueError):
            service.build_from_search_results(
                title="Invalid Packet",
                purpose="legal research",
                results=[{"doc_id": "K000000001", "text": "uncited claim"}],
            )

    def test_export_bundle_contains_packet_hash_and_citations(self):
        service = EvidencePacketService()
        bundle = service.build_from_search_results(
            title="Export Packet",
            purpose="draft review",
            results=[
                {
                    "document_version_id": "version_1",
                    "citation_id": "citation_1",
                    "citation_label": "Doc, Article 1",
                    "citation_quote": "Quoted legal text.",
                }
            ],
            source_snapshot_ids=("snapshot_1",),
        )

        exported = service.export_bundle(bundle)

        self.assertEqual(exported["packet"]["id"], bundle.packet.id)
        self.assertEqual(exported["packet"]["packet_hash"], bundle.packet.packet_hash)
        self.assertEqual(exported["packet"]["source_snapshot_ids"], ["snapshot_1"])
        self.assertEqual(exported["citations"][0]["id"], "citation_1")
        self.assertEqual(exported["citations"][0]["quote"], "Quoted legal text.")


if __name__ == "__main__":
    unittest.main()
