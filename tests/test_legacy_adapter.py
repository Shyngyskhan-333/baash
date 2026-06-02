import json
import tempfile
import unittest
from pathlib import Path

from src.evidence.legacy_adapter import import_legacy_document, import_legacy_parsed_dir
from src.evidence.models import compute_sha256


class LegacyAdapterTests(unittest.TestCase):
    def test_import_legacy_document_maps_chunks_to_citations(self):
        payload = {
            "doc_id": "K000000001",
            "title": "Test Law",
            "source_url": "https://adilet.zan.kz/rus/docs/K000000001",
            "articles": [
                {
                    "article_number": "Статья 1",
                    "chunks": [
                        {
                            "chunk_id": "K000000001_1_0",
                            "text": "Граждане имеют право на обращение.",
                            "hierarchy": ["Раздел 1", "Статья 1"],
                        }
                    ],
                }
            ],
        }

        imported = import_legacy_document(payload, raw_content_uri="data/parsed/K000000001.json")

        self.assertEqual(imported.document.external_id, "K000000001")
        self.assertEqual(imported.document.title, "Test Law")
        self.assertEqual(imported.version.document_id, imported.document.id)
        self.assertEqual(imported.snapshot.content_hash, compute_sha256(imported.raw_payload))
        self.assertEqual(len(imported.articles), 1)
        self.assertEqual(len(imported.citations), 1)
        self.assertEqual(len(imported.chunks), 1)
        self.assertEqual(imported.citations[0].chunk_id, imported.chunks[0].id)
        self.assertEqual(imported.chunks[0].citation_id, imported.citations[0].id)
        self.assertIn("Статья 1", imported.citations[0].citation_label)
        self.assertEqual(imported.citations[0].quote, "Граждане имеют право на обращение.")

    def test_import_legacy_document_uses_article_text_when_chunks_are_missing(self):
        payload = {
            "doc_id": "K000000002",
            "title": "Text Only Law",
            "articles": [
                {
                    "article_number": "Article 2",
                    "text": "This article has no explicit chunk list.",
                }
            ],
        }

        imported = import_legacy_document(payload, raw_content_uri="fixture.json")

        self.assertEqual(len(imported.citations), 1)
        self.assertEqual(imported.chunks[0].text, "This article has no explicit chunk list.")
        self.assertTrue(imported.citations[0].id.startswith("citation_"))

    def test_metadata_only_document_is_marked_non_citable(self):
        payload = {
            "doc_id": "K000000004",
            "title": "Metadata Only Law",
            "parse_quality": "metadata_only",
            "articles": [],
        }

        imported = import_legacy_document(payload, raw_content_uri="metadata.json")

        self.assertEqual(imported.parse_quality, "metadata_only")
        self.assertFalse(imported.legal_text_available)
        self.assertEqual(imported.citations, ())
        self.assertEqual(imported.chunks, ())

    def test_metadata_only_document_with_text_is_rejected(self):
        payload = {
            "doc_id": "K000000005",
            "title": "Invalid Metadata Only Law",
            "parse_quality": "metadata_only",
            "articles": [
                {
                    "article_number": "Article 1",
                    "text": "This text must not become citable when parse quality is metadata_only.",
                }
            ],
        }

        with self.assertRaises(ValueError):
            import_legacy_document(payload, raw_content_uri="metadata-invalid.json")

    def test_import_legacy_parsed_dir_skips_invalid_json_and_non_json_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed_dir = Path(tmp)
            (parsed_dir / "valid.json").write_text(
                json.dumps({"doc_id": "K000000003", "title": "Valid", "articles": []}),
                encoding="utf-8",
            )
            (parsed_dir / "invalid.json").write_text("{bad", encoding="utf-8")
            (parsed_dir / "notes.txt").write_text("ignore", encoding="utf-8")

            imported = import_legacy_parsed_dir(parsed_dir)

        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0].document.external_id, "K000000003")


if __name__ == "__main__":
    unittest.main()
