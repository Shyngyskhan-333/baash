from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List
import httpx

from api.services.ai_provider import load_config, save_config

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


class AIConfig(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    ollama_url: Optional[str] = "http://localhost:11434"
    ollama_model: Optional[str] = "qwen2.5:7b"


@router.get("/ai")
async def get_ai_settings():
    """Return current AI config (API key is masked)."""
    cfg = load_config()
    masked = cfg.copy()
    key = masked.get("api_key", "")
    if key:
        masked["api_key"] = key[:6] + "..." + key[-4:] if len(key) > 12 else "***"
    return masked


@router.post("/ai")
async def update_ai_settings(config: AIConfig):
    """Save new AI provider configuration."""
    existing = load_config()
    update = config.dict(exclude_none=True)
    # Don't overwrite the key if a masked placeholder was sent back
    if update.get("api_key", "").endswith("..."):
        update.pop("api_key", None)
    existing.update(update)
    save_config(existing)
    return {"status": "saved", "provider": existing["provider"]}


@router.post("/ai/test")
async def test_ai_connection(config: AIConfig):
    """Test that the given config connects to the AI provider successfully."""
    existing = load_config()
    update = config.dict(exclude_none=True)
    if update.get("api_key", "").endswith("..."):
        update.pop("api_key", None)
    existing.update(update)

    provider = existing.get("provider", "mock")
    try:
        if provider == "ollama":
            ollama_url = existing.get("ollama_url", "http://localhost:11434")
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
            return {"status": "ok", "provider": "ollama", "available_models": models}

        elif provider in ("openai", "azure", "anthropic"):
            # Temporarily write config and test
            save_config(existing)
            from api.services.ai_provider import AIProvider
            tmp = AIProvider()
            reply = await tmp.complete(
                messages=[{"role": "user", "content": "Reply with OK only."}],
                system_prompt="You are a helpful assistant."
            )
            return {"status": "ok", "provider": provider, "reply": reply[:120]}

        else:
            return {"status": "mock", "message": "Провайдер mock — настройте реальный."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка подключения: {e}")


@router.get("/ollama/models")
async def list_ollama_models():
    """List all Ollama models installed locally."""
    cfg = load_config()
    ollama_url = cfg.get("ollama_url", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
        return {"models": models, "running": True}
    except Exception:
        return {
            "models": [],
            "running": False,
            "hint": "Запустите: ollama serve  |  Установка: https://ollama.com/download"
        }
