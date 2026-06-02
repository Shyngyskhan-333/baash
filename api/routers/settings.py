
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional

from src.audit.events import build_ai_settings_audit_log
from src.audit.sink import JsonlAuditSink
from src.evidence.models import AuditLog
from src.security.rbac import PermissionDenied, ProtectedAction, require_permission

router = APIRouter()

CONFIG_PATH = Path("data/ai_config.json")
SECRET_FIELDS = {"azure_key", "openai_key", "anthropic_key"}
ALLOWED_PROVIDERS = {"mock", "azure", "openai", "anthropic", "ollama"}

class AIConfig(BaseModel):
    provider: str = "mock"
    azure_endpoint: Optional[str] = ""
    azure_key: Optional[str] = ""
    azure_deployment: Optional[str] = "gpt-4o"
    azure_api_version: Optional[str] = "2024-02-15-preview"
    openai_key: Optional[str] = ""
    openai_model: Optional[str] = "gpt-4o-mini"
    anthropic_key: Optional[str] = ""
    anthropic_model: Optional[str] = "claude-3-5-sonnet-latest"
    ollama_url: Optional[str] = "http://localhost:11434"
    ollama_model: Optional[str] = "qwen2.5:7b"

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        provider = (value or "mock").strip().lower()
        if provider not in ALLOWED_PROVIDERS:
            raise ValueError(f"Unsupported AI provider: {value}")
        return provider

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return AIConfig().model_dump()

def _save_config(config: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def _is_masked_secret(value: Optional[str]) -> bool:
    return bool(value and "..." in value)

def _merge_preserving_secrets(existing: dict, incoming: dict) -> dict:
    merged = {**existing, **incoming}
    for key in SECRET_FIELDS:
        value = incoming.get(key)
        if value is None or value == "" or _is_masked_secret(value):
            merged[key] = existing.get(key, "")
    return merged

def _production_mode_enabled() -> bool:
    for key in ("LEXLENS_ENV", "APP_ENV", "ENV"):
        if (os.getenv(key) or "").strip().lower() in {"prod", "production"}:
            return True
    return False

def _require_settings_write_allowed() -> None:
    try:
        require_permission(
            None,
            ProtectedAction.MANAGE_AI_SETTINGS,
            production_mode=_production_mode_enabled(),
        )
    except PermissionDenied as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail="AI settings writes are disabled in production without RBAC/admin authentication.",
        ) from exc

def _build_ai_settings_audit_log(before_config: dict, after_config: dict) -> AuditLog:
    return build_ai_settings_audit_log(
        actor_id="system",
        before_config=before_config,
        after_config=after_config,
        reason="settings.ai.updated",
    )

def _append_audit_log(audit_log: AuditLog) -> None:
    JsonlAuditSink().append(audit_log)

@router.get("/settings/ai")
async def get_ai_settings():

    config = _load_config()

    safe = config.copy()
    for key in ["azure_key", "openai_key", "anthropic_key"]:
        if safe.get(key):
            safe[key] = safe[key][:8] + "..." if len(safe.get(key, "")) > 8 else "***"
    return {"status": "ok", "config": safe}

@router.post("/settings/ai")
async def save_ai_settings(config: AIConfig):

    _require_settings_write_allowed()
    existing = _load_config()
    data = _merge_preserving_secrets(existing, config.model_dump())
    audit_log = _build_ai_settings_audit_log(existing, data)
    _append_audit_log(audit_log)
    _save_config(data)
    return {"status": "ok", "message": "Настройки сохранены"}

@router.post("/settings/ai/test")
async def test_ai_connection(config: AIConfig):

    provider = config.provider.lower()

    try:
        if provider == "ollama":
            import httpx
            url = (config.ollama_url or "http://localhost:11434").rstrip("/")
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{url}/api/tags")
                if resp.status_code == 200:
                    return {"status": "ok", "message": "Ollama подключён успешно"}
                return {"status": "error", "message": f"Ollama вернул код {resp.status_code}"}

        elif provider == "azure":
            from openai import AsyncAzureOpenAI
            client = AsyncAzureOpenAI(
                api_key=config.azure_key,
                api_version=config.azure_api_version or "2024-02-15-preview",
                azure_endpoint=config.azure_endpoint or "",
            )
            resp = await client.chat.completions.create(
                model=config.azure_deployment or "gpt-4o",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return {"status": "ok", "message": "Azure OpenAI подключён успешно"}

        elif provider == "openai":
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=config.openai_key)
            resp = await client.chat.completions.create(
                model=config.openai_model or "gpt-4o-mini",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return {"status": "ok", "message": "OpenAI подключён успешно"}

        elif provider == "anthropic":
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=config.anthropic_key)
            resp = await client.messages.create(
                model=config.anthropic_model or "claude-3-5-sonnet-latest",
                system="",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return {"status": "ok", "message": "Anthropic подключён успешно"}

        else:
            return {"status": "ok", "message": f"Провайдер '{provider}' принят (тест не реализован)"}

    except Exception as e:
        return {"status": "error", "message": f"Ошибка подключения: {str(e)}"}

@router.get("/settings/ollama/models")
async def get_ollama_models():

    try:
        import httpx
        config = _load_config()
        url = (config.get("ollama_url") or "http://localhost:11434").rstrip("/")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return {"status": "ok", "models": models}
            return {"status": "error", "models": [], "message": f"Ollama вернул код {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "models": [], "message": f"Ollama недоступен: {str(e)}"}
