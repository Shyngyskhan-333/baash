
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()

CONFIG_PATH = Path("data/ai_config.json")

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

    data = config.model_dump()
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
