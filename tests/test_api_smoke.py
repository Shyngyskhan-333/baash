import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from api.main import app


class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_diff_endpoint_returns_stats(self):
        response = self.client.post(
            "/api/v1/diff",
            json={
                "text_a": "Статья 1. Старый текст.",
                "text_b": "Статья 1. Новый текст.",
            },
        )

        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("stats", body)
        self.assertIn("hunks", body)
        self.assertIn("ai_summary", body)
        self.assertGreaterEqual(body["stats"]["added"] + body["stats"]["removed"] + body["stats"]["changed"], 1)

    def test_diff_endpoint_rejects_empty_payload(self):
        response = self.client.post(
            "/api/v1/diff",
            json={
                "text_a": "",
                "text_b": "",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_preview_endpoint_returns_archived_versions_when_history_exists(self):
        response = self.client.get("/api/v1/index/preview/K1500000377")

        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertGreater(body["versions_found"], 1)
        self.assertTrue(any(version["status"] == "archived" for version in body["versions"]))

    def test_document_endpoint_fetches_archive_version_instead_of_fallback_current(self):
        archived_doc = {
            "doc_id": "K1500000377_31.10.2015",
            "title": "Archived version",
            "articles": [
                {"text": "Archived article text."},
            ],
        }

        with patch("src.scraper.adilet_scraper.fetch_by_url", new=AsyncMock(return_value=archived_doc)) as mocked_fetch:
            response = self.client.get("/api/v1/index/document/K1500000377_31.10.2015")

        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["doc_id"], "K1500000377_31.10.2015")
        self.assertIn("Archived article text.", body["text"])
        mocked_fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()