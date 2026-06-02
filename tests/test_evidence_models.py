import unittest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

from src.evidence.models import (
    Article,
    AuditLog,
    Citation,
    EvidencePacket,
    LegalDocument,
    LegalDocumentStatus,
    LegalDocumentVersion,
    ModelRun,
    SemanticChunk,
    Source,
    SourceSnapshot,
    SourceType,
    compute_sha256,
)


class EvidenceModelTests(unittest.TestCase):
    def test_source_snapshot_from_content_computes_stable_hash_and_id(self):
        snapshot = SourceSnapshot.from_content(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000001",
            content="<html>law</html>",
            raw_content_uri="data/raw/K000000001.html",
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            http_status=200,
            parser_version="legacy-v1",
        )

        self.assertEqual(snapshot.content_hash, compute_sha256("<html>law</html>"))
        self.assertTrue(snapshot.id.startswith("snapshot_"))
        self.assertEqual(snapshot.source_id, "adilet")

    def test_core_evidence_entities_are_immutable(self):
        source = Source(
            id="adilet",
            name="Adilet",
            source_type=SourceType.OFFICIAL_PORTAL,
            jurisdiction="KZ",
        )

        with self.assertRaises(FrozenInstanceError):
            source.name = "Changed"

    def test_legal_document_version_rejects_invalid_effective_range(self):
        with self.assertRaises(ValueError):
            LegalDocumentVersion(
                id="version_1",
                document_id="doc_1",
                source_snapshot_id="snapshot_1",
                version_label="current",
                text_hash=compute_sha256("text"),
                status=LegalDocumentStatus.ACTIVE,
                effective_from=datetime(2026, 2, 1, tzinfo=UTC),
                effective_to=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_article_clause_citation_and_chunk_can_share_traceable_ids(self):
        document = LegalDocument(
            id="doc_K000000001",
            external_id="K000000001",
            title="Test Law",
            jurisdiction="KZ",
            document_type="law",
            canonical_source_id="adilet",
        )
        version = LegalDocumentVersion(
            id="version_K000000001_current",
            document_id=document.id,
            source_snapshot_id="snapshot_1",
            version_label="current",
            text_hash=compute_sha256("Article 1. Test text."),
        )
        article = Article.from_text(
            id="article_1",
            document_version_id=version.id,
            number="Article 1",
            text="Article 1. Test text.",
        )
        citation = Citation(
            id="citation_1",
            document_version_id=version.id,
            article_id=article.id,
            quote="Test text.",
            citation_label="Test Law, Article 1",
            start_offset=11,
            end_offset=21,
        )
        chunk = SemanticChunk.from_text(
            id="chunk_1",
            document_version_id=version.id,
            article_id=article.id,
            citation_id=citation.id,
            text=article.text,
        )

        self.assertEqual(article.text_hash, compute_sha256(article.text))
        self.assertEqual(chunk.chunk_hash, compute_sha256(chunk.text))
        self.assertEqual(chunk.citation_id, citation.id)

    def test_citation_rejects_invalid_offsets(self):
        with self.assertRaises(ValueError):
            Citation(
                id="citation_bad",
                document_version_id="version_1",
                quote="text",
                citation_label="Doc, Article 1",
                start_offset=10,
                end_offset=5,
            )

    def test_evidence_packet_requires_citations_and_computes_hash(self):
        packet = EvidencePacket(
            id="packet_1",
            title="Review Packet",
            purpose="draft law review",
            citation_ids=("citation_1",),
            source_snapshot_ids=("snapshot_1",),
            model_run_ids=("model_run_1",),
        ).with_computed_hash()

        self.assertEqual(len(packet.packet_hash), 64)
        self.assertEqual(packet.packet_hash, packet.with_computed_hash().packet_hash)

    def test_evidence_packet_rejects_empty_citation_list(self):
        with self.assertRaises(ValueError):
            EvidencePacket(
                id="packet_empty",
                title="Empty Packet",
                purpose="invalid",
                citation_ids=(),
            )

    def test_model_run_and_audit_log_validate_hash_fields(self):
        prompt_hash = compute_sha256("prompt")
        output_hash = compute_sha256("output")
        run = ModelRun(
            id="model_run_1",
            model_name="mock",
            model_version="test",
            prompt_hash=prompt_hash,
            output_hash=output_hash,
            input_citation_ids=("citation_1",),
        )
        log = AuditLog(
            id="audit_1",
            actor_id="user_1",
            action="evidence_packet.created",
            target_type="EvidencePacket",
            target_id="packet_1",
            after_hash=output_hash,
        )

        self.assertEqual(run.prompt_hash, prompt_hash)
        self.assertEqual(log.after_hash, output_hash)


if __name__ == "__main__":
    unittest.main()
