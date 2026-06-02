import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api.routers.settings import AIConfig, _build_ai_settings_audit_log, _merge_preserving_secrets, save_ai_settings


class SettingsSecretTests(unittest.TestCase):
    def test_masked_and_empty_secrets_preserve_existing_values(self):
        existing = {
            "provider": "openai",
            "azure_key": "azure-real-key",
            "openai_key": "openai-real-key",
            "anthropic_key": "anthropic-real-key",
        }
        incoming = {
            "provider": "ollama",
            "azure_key": "azure-re...",
            "openai_key": "",
            "anthropic_key": None,
        }

        merged = _merge_preserving_secrets(existing, incoming)

        self.assertEqual(merged["provider"], "ollama")
        self.assertEqual(merged["azure_key"], "azure-real-key")
        self.assertEqual(merged["openai_key"], "openai-real-key")
        self.assertEqual(merged["anthropic_key"], "anthropic-real-key")

    def test_new_secret_replaces_existing_value(self):
        existing = {"openai_key": "old-key"}
        incoming = {"openai_key": "new-key"}

        merged = _merge_preserving_secrets(existing, incoming)

        self.assertEqual(merged["openai_key"], "new-key")


class SettingsProductionGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_ai_settings_rejects_unauthenticated_production_mode(self):
        with patch.dict("os.environ", {"LEXLENS_ENV": "production"}, clear=False):
            with self.assertRaises(HTTPException) as ctx:
                await save_ai_settings(AIConfig(provider="mock"))

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("disabled in production", ctx.exception.detail)

    async def test_save_ai_settings_preserves_development_behavior(self):
        saved = {}
        appended = []

        with patch.dict("os.environ", {"LEXLENS_ENV": "development"}, clear=False):
            with patch("api.routers.settings._load_config", return_value={"provider": "mock"}):
                with patch("api.routers.settings._save_config", side_effect=lambda data: saved.update(data)):
                    with patch("api.routers.settings._append_audit_log", side_effect=lambda audit: appended.append(audit)):
                        response = await save_ai_settings(AIConfig(provider="ollama"))

        self.assertEqual(response["status"], "ok")
        self.assertEqual(saved["provider"], "ollama")
        self.assertEqual(len(appended), 1)
        self.assertEqual(appended[0].action, "settings.ai.updated")


class SettingsAuditTests(unittest.TestCase):
    def test_build_ai_settings_audit_log_uses_sanitized_before_after_hashes(self):
        before = {"provider": "mock", "openai_key": "old-secret"}
        after = {"provider": "openai", "openai_key": "new-secret"}

        audit = _build_ai_settings_audit_log(before, after)

        self.assertEqual(audit.action, "settings.ai.updated")
        self.assertEqual(audit.target_type, "AISettings")
        self.assertNotEqual(audit.before_hash, audit.after_hash)


if __name__ == "__main__":
    unittest.main()
