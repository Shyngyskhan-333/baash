import unittest

from src.audit.events import build_ai_settings_audit_log, sanitized_config_hash


class AuditEventTests(unittest.TestCase):
    def test_sanitized_config_hash_ignores_secret_values(self):
        base = {
            "provider": "openai",
            "openai_model": "gpt-4o-mini",
            "openai_key": "secret-a",
        }
        changed_secret = {
            "provider": "openai",
            "openai_model": "gpt-4o-mini",
            "openai_key": "secret-b",
        }

        self.assertEqual(sanitized_config_hash(base), sanitized_config_hash(changed_secret))

    def test_sanitized_config_hash_changes_for_non_secret_settings(self):
        base = {
            "provider": "openai",
            "openai_model": "gpt-4o-mini",
            "openai_key": "secret-a",
        }
        changed_model = {
            "provider": "openai",
            "openai_model": "gpt-4o",
            "openai_key": "secret-a",
        }

        self.assertNotEqual(sanitized_config_hash(base), sanitized_config_hash(changed_model))

    def test_build_ai_settings_audit_log_redacts_secrets_and_hashes_before_after(self):
        before = {"provider": "mock", "openai_key": "old-secret"}
        after = {"provider": "openai", "openai_key": "new-secret"}

        audit = build_ai_settings_audit_log(
            actor_id="system",
            before_config=before,
            after_config=after,
            reason="settings.ai.updated",
        )

        self.assertEqual(audit.actor_id, "system")
        self.assertEqual(audit.action, "settings.ai.updated")
        self.assertEqual(audit.target_type, "AISettings")
        self.assertEqual(audit.target_id, "global")
        self.assertEqual(audit.before_hash, sanitized_config_hash(before))
        self.assertEqual(audit.after_hash, sanitized_config_hash(after))
        self.assertEqual(audit.reason, "settings.ai.updated")

    def test_same_settings_change_has_stable_audit_id_for_same_actor_and_hashes(self):
        before = {"provider": "mock"}
        after = {"provider": "ollama"}

        first = build_ai_settings_audit_log(
            actor_id="system",
            before_config=before,
            after_config=after,
            reason="settings.ai.updated",
        )
        second = build_ai_settings_audit_log(
            actor_id="system",
            before_config=before,
            after_config=after,
            reason="settings.ai.updated",
        )

        self.assertEqual(first.id, second.id)


if __name__ == "__main__":
    unittest.main()
