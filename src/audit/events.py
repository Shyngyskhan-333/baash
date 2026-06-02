from __future__ import annotations

import json
from typing import Any, Mapping

from src.evidence.models import AuditLog, compute_sha256, make_stable_id

SECRET_FIELDS = frozenset({"azure_key", "openai_key", "anthropic_key"})
AI_SETTINGS_TARGET_TYPE = "AISettings"
AI_SETTINGS_TARGET_ID = "global"
AI_SETTINGS_UPDATED = "settings.ai.updated"


def sanitized_config_hash(config: Mapping[str, Any]) -> str:
    sanitized = {
        str(key): _sanitized_value(key, value)
        for key, value in sorted(config.items(), key=lambda item: str(item[0]))
    }
    raw = json.dumps(sanitized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return compute_sha256(raw)


def build_ai_settings_audit_log(
    *,
    actor_id: str,
    before_config: Mapping[str, Any],
    after_config: Mapping[str, Any],
    reason: str = AI_SETTINGS_UPDATED,
    organization_id: str | None = None,
) -> AuditLog:
    before_hash = sanitized_config_hash(before_config)
    after_hash = sanitized_config_hash(after_config)
    return AuditLog(
        id=make_stable_id("audit", AI_SETTINGS_UPDATED, actor_id, before_hash, after_hash, reason),
        actor_id=actor_id,
        action=AI_SETTINGS_UPDATED,
        target_type=AI_SETTINGS_TARGET_TYPE,
        target_id=AI_SETTINGS_TARGET_ID,
        organization_id=organization_id,
        before_hash=before_hash,
        after_hash=after_hash,
        reason=reason,
    )


def _sanitized_value(key: Any, value: Any) -> Any:
    if str(key) in SECRET_FIELDS:
        return "__redacted__" if value else ""
    return value
