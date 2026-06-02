import json
import tempfile
import unittest
from pathlib import Path

from src.audit.events import build_ai_settings_audit_log
from src.audit.sink import JsonlAuditSink


class JsonlAuditSinkTests(unittest.TestCase):
    def test_append_writes_one_json_line_per_audit_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.jsonl"
            sink = JsonlAuditSink(audit_path)
            audit = build_ai_settings_audit_log(
                actor_id="system",
                before_config={"provider": "mock"},
                after_config={"provider": "ollama"},
            )

            sink.append(audit)

            lines = audit_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["id"], audit.id)
        self.assertEqual(payload["action"], "settings.ai.updated")
        self.assertEqual(payload["target_type"], "AISettings")
        self.assertIn("timestamp", payload)

    def test_append_is_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.jsonl"
            sink = JsonlAuditSink(audit_path)
            first = build_ai_settings_audit_log(
                actor_id="system",
                before_config={"provider": "mock"},
                after_config={"provider": "ollama"},
            )
            second = build_ai_settings_audit_log(
                actor_id="system",
                before_config={"provider": "ollama"},
                after_config={"provider": "openai"},
            )

            sink.append(first)
            sink.append(second)

            lines = audit_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["id"], first.id)
        self.assertEqual(json.loads(lines[1])["id"], second.id)

    def test_append_does_not_write_secret_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.jsonl"
            sink = JsonlAuditSink(audit_path)
            audit = build_ai_settings_audit_log(
                actor_id="system",
                before_config={"provider": "mock", "openai_key": "old-secret"},
                after_config={"provider": "openai", "openai_key": "new-secret"},
            )

            sink.append(audit)

            content = audit_path.read_text(encoding="utf-8")

        self.assertNotIn("old-secret", content)
        self.assertNotIn("new-secret", content)


if __name__ == "__main__":
    unittest.main()
