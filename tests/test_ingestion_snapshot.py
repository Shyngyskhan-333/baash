from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path

from src.evidence.models import compute_sha256
from src.ingestion.snapshot import FetchedSourceContent, SourceSnapshotBuilder


class SourceSnapshotBuilderTests(unittest.TestCase):
    def test_build_snapshot_from_fetched_content_before_parsing(self):
        fetched_at = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
        fetched = FetchedSourceContent(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000001",
            content="<html>legal source</html>",
            raw_content_uri="data/raw/K000000001.html",
            fetched_at=fetched_at,
            http_status=200,
            fetch_method="mock_http",
        )

        snapshot = SourceSnapshotBuilder().build(fetched)

        self.assertEqual(snapshot.source_id, "adilet")
        self.assertEqual(snapshot.url, fetched.url)
        self.assertEqual(snapshot.content_hash, compute_sha256(fetched.content))
        self.assertEqual(snapshot.raw_content_uri, "data/raw/K000000001.html")
        self.assertEqual(snapshot.fetched_at, fetched_at)
        self.assertEqual(snapshot.http_status, 200)
        self.assertIsNone(snapshot.parser_version)
        self.assertEqual(snapshot.fetch_method, "mock_http")

    def test_same_fetched_content_produces_stable_snapshot_id(self):
        fetched = FetchedSourceContent(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000001",
            content=b"<html>same</html>",
            raw_content_uri="data/raw/K000000001.html",
        )
        builder = SourceSnapshotBuilder()

        first = builder.build(fetched)
        second = builder.build(fetched)

        self.assertEqual(first.id, second.id)

    def test_builder_rejects_empty_raw_content(self):
        fetched = FetchedSourceContent(
            source_id="adilet",
            url="https://adilet.zan.kz/rus/docs/K000000001",
            content="",
            raw_content_uri="data/raw/K000000001.html",
        )

        with self.assertRaises(ValueError):
            SourceSnapshotBuilder().build(fetched)

    def test_builder_can_persist_raw_content_and_return_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "K000000001.html"
            fetched = FetchedSourceContent(
                source_id="adilet",
                url="https://adilet.zan.kz/rus/docs/K000000001",
                content="<html>persist me</html>",
                raw_content_uri=str(raw_path),
                http_status=200,
            )

            snapshot = SourceSnapshotBuilder().build_and_store(fetched)

            stored = raw_path.read_text(encoding="utf-8")

        self.assertEqual(stored, "<html>persist me</html>")
        self.assertEqual(snapshot.raw_content_uri, str(raw_path))
        self.assertEqual(snapshot.content_hash, compute_sha256(stored))


if __name__ == "__main__":
    unittest.main()
