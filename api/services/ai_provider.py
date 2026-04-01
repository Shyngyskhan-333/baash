"""
Динамический AI-провайдер.
Загружает конфигурацию из data/ai_config.json (приоритет) или .env (fallback).
Поддерживаемые провайдеры: azure, openai, anthropic, ollama (local Qwen/любая модель)
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
load_dotenv()

CONFIG_PATH = Path("data/ai_config.json")

DEFAULT_CONFIG = {
    "provider": os.getenv("AI_PROVIDER", "mock"),
    "model": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    "api_key": os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "",
    "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    "ollama_url": "http://localhost:11434",
    "ollama_model": "qwen3:7b",
}


def load_config() -> dict:
    """Loads config from file (user settings) with .env as fallback."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Merge: saved config overrides defaults
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(saved)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


class AIProvider:
    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        cfg = load_config()
        provider = cfg.get("provider", "mock").lower()

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        if provider == "openai":
            return await self._call_openai(full_messages, cfg)
        elif provider == "azure":
            return await self._call_azure(full_messages, cfg)
        elif provider == "anthropic":
            return await self._call_anthropic(full_messages, cfg)
        elif provider == "ollama":
            return await self._call_ollama(full_messages, cfg)
        else:
            return self._call_mock(full_messages)

    async def _call_openai(self, messages, cfg) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=cfg["api_key"])
        resp = await client.chat.completions.create(
            model=cfg.get("model", "gpt-4o"),
            messages=messages,
            temperature=0.1,
        )
        return resp.choices[0].message.content or ""

    async def _call_azure(self, messages, cfg) -> str:
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            api_key=cfg["api_key"],
            api_version="2024-02-15-preview",
            azure_endpoint=cfg.get("endpoint", ""),
        )
        resp = await client.chat.completions.create(
            model=cfg.get("model", "gpt-4o"),
            messages=messages,
            temperature=0.1,
        )
        return resp.choices[0].message.content or ""

    async def _call_anthropic(self, messages, cfg) -> str:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=cfg["api_key"])
        system = None
        anthropic_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                anthropic_msgs.append(m)
        kwargs = {
            "model": cfg.get("model", "claude-3-5-sonnet-20241022"),
            "max_tokens": 4096,
            "messages": anthropic_msgs,
        }
        if system:
            kwargs["system"] = system
        resp = await client.messages.create(**kwargs)
        return resp.content[0].text

    async def _call_ollama(self, messages, cfg) -> str:
        """
        Local Qwen via Ollama — OpenAI-compatible API.
        Данные не покидают сервер (безопасность для гос-кейса).
        """
        import httpx
        ollama_url = cfg.get("ollama_url", "http://localhost:11434")
        model = cfg.get("ollama_model", "qwen3:7b")
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{ollama_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    def _call_mock(self, messages) -> str:
        return (
            "⚠️ AI-провайдер не настроен. Перейдите в **Настройки** и выберите "
            "провайдер (OpenAI, Azure, Anthropic или локальный Qwen)."
        )


# Singleton
ai_provider = AIProvider()
