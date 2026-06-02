import json
import tempfile
import unittest
from pathlib import Path

from src.audit.events import build_ai_settings_audit_log
from src.audit.reader import AuditReadService, JsonlAuditReader
from src.audit.sink import JsonlAuditSink
from src.security.rbac import AuthContext, PermissionDenied, Role


class AuditReaderTests(unittest.TestCase):
    def test_reader_returns_records_in_append_order(self):
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

            records = JsonlAuditReader(audit_path).list_records()

        self.assertEqual([record["id"] for record in records], [first.id, second.id])

    def test_reader_applies_limit_to_most_recent_records(self):
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

            records = JsonlAuditReader(audit_path).list_records(limit=1)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], second.id)

    def test_reader_skips_malformed_json_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.jsonl"
            audit_path.write_text(
                "\n".join(
                    [
                        "{bad json",
                        json.dumps({"id": "audit_1", "action": "settings.ai.updated"}),
                    ]
                ),
                encoding="utf-8",
            )

            records = JsonlAuditReader(audit_path).list_records()

        self.assertEqual(records, [{"id": "audit_1", "action": "settings.ai.updated"}])

    def test_reader_filters_by_organization_and_global_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.jsonl"
            audit_path.write_text(
                "\n".join(
                    [
                        json.dumps({"id": "global", "action": "settings.ai.updated", "organization_id": None}),
                        json.dumps({"id": "org_1", "action": "review_task.validated", "organization_id": "org_1"}),
                        json.dumps({"id": "org_2", "action": "review_task.validated", "organization_id": "org_2"}),
                    ]
                ),
                encoding="utf-8",
            )

            records = JsonlAuditReader(audit_path).list_records(organization_id="org_1")

        self.assertEqual([record["id"] for record in records], ["global", "org_1"])


class AuditReadServiceTests(unittest.TestCase):
    def test_service_rejects_missing_actor_in_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = AuditReadService(JsonlAuditReader(Path(tmp) / "audit.jsonl"))

            with self.assertRaises(PermissionDenied):
                service.list_records(actor=None, production_mode=True)

    def test_service_allows_external_auditor_for_own_organization(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_path = Path(tmp) / "audit.jsonl"
            audit_path.write_text(
                "\n".join(
                    [
                        json.dumps({"id": "global", "action": "settings.ai.updated", "organization_id": None}),
                        json.dumps({"id": "org_1", "action": "review_task.validated", "organization_id": "org_1"}),
                        json.dumps({"id": "org_2", "action": "review_task.validated", "organization_id": "org_2"}),
                    ]
                ),
                encoding="utf-8",
            )
            service = AuditReadService(JsonlAuditReader(audit_path))
            actor = AuthContext(actor_id="auditor_1", role=Role.EXTERNAL_AUDITOR, organization_id="org_1")

            records = service.list_records(actor=actor, production_mode=True)

        self.assertEqual([record["id"] for record in records], ["global", "org_1"])


if __name__ == "__main__":
    unittest.main()
