import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI

env_file = os.getenv("ENV_FILE", ".env").strip() or ".env"
load_dotenv(dotenv_path=Path(env_file))

CONFIG_PATH = Path("data/ai_config.json")


class AIProvider:
    def __init__(self):
        self._azure_client: Optional[AsyncAzureOpenAI] = None
        self._openai_client: Optional[AsyncOpenAI] = None
        self._anthropic_client: Optional[AsyncAnthropic] = None
        self._azure_signature: Optional[tuple] = None
        self._openai_signature: Optional[tuple] = None
        self._anthropic_signature: Optional[tuple] = None
        self._request_retries = 0

    def _request_timeout_sec(self) -> float:
        
        raw = (os.getenv("AI_REQUEST_TIMEOUT_SEC") or "").strip()
        if raw:
            try:
                return max(15.0, float(raw))
            except ValueError:
                pass
        return 300.0

    def _load_config(self) -> Dict[str, str]:
        file_config: Dict[str, str] = {}
        if CONFIG_PATH.exists():
            try:
                file_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                file_config = {}

        return {
            "provider": (file_config.get("provider") or os.getenv("AI_PROVIDER") or "mock").strip().lower(),
            "azure_endpoint": (file_config.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/"),
            "azure_key": (file_config.get("azure_key") or os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY") or "").strip(),
            "azure_deployment": (file_config.get("azure_deployment") or os.getenv("AZURE_OPENAI_DEPLOYMENT") or "gpt-4o").strip(),
            "azure_api_version": (file_config.get("azure_api_version") or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview").strip(),
            "openai_key": (file_config.get("openai_key") or os.getenv("OPENAI_API_KEY") or "").strip(),
            "openai_model": (file_config.get("openai_model") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip(),
            "anthropic_key": (file_config.get("anthropic_key") or os.getenv("ANTHROPIC_API_KEY") or "").strip(),
            "anthropic_model": (file_config.get("anthropic_model") or os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-latest").strip(),
            "ollama_url": (file_config.get("ollama_url") or os.getenv("OLLAMA_URL") or "http://localhost:11434").strip().rstrip("/"),
            "ollama_model": (file_config.get("ollama_model") or os.getenv("OLLAMA_MODEL") or "qwen2.5:7b").strip(),
        }

    async def _complete_azure(self, config: Dict[str, str], messages: List[Dict[str, str]]) -> str:
        if not config["azure_key"] or not config["azure_endpoint"]:
            return "Ошибка конфигурации Azure OpenAI: отсутствует endpoint или API-ключ."

        timeout = self._request_timeout_sec()
        signature = (config["azure_endpoint"], config["azure_key"], config["azure_api_version"], timeout)
        if self._azure_client is None or self._azure_signature != signature:
            self._azure_client = AsyncAzureOpenAI(
                api_key=config["azure_key"],
                api_version=config["azure_api_version"],
                azure_endpoint=config["azure_endpoint"],
                timeout=timeout,
                max_retries=self._request_retries,
            )
            self._azure_signature = signature

        response = await self._azure_client.chat.completions.create(
            model=config["azure_deployment"],
            messages=messages,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    async def _complete_openai(self, config: Dict[str, str], messages: List[Dict[str, str]]) -> str:
        if not config["openai_key"]:
            return "Ошибка конфигурации OpenAI: отсутствует API-ключ."

        timeout = self._request_timeout_sec()
        signature = (config["openai_key"], timeout)
        if self._openai_client is None or self._openai_signature != signature:
            self._openai_client = AsyncOpenAI(
                api_key=config["openai_key"],
                timeout=timeout,
                max_retries=self._request_retries,
            )
            self._openai_signature = signature

        response = await self._openai_client.chat.completions.create(
            model=config["openai_model"] or "gpt-4o-mini",
            messages=messages,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    async def _complete_anthropic(self, config: Dict[str, str], messages: List[Dict[str, str]]) -> str:
        if not config["anthropic_key"]:
            return "Ошибка конфигурации Anthropic: отсутствует API-ключ."

        timeout = self._request_timeout_sec()
        signature = (config["anthropic_key"], timeout)
        if self._anthropic_client is None or self._anthropic_signature != signature:
            self._anthropic_client = AsyncAnthropic(
                api_key=config["anthropic_key"],
                timeout=timeout,
                max_retries=self._request_retries,
            )
            self._anthropic_signature = signature

        system_parts = [message["content"] for message in messages if message["role"] == "system"]
        chat_messages = [message for message in messages if message["role"] != "system"]

        response = await self._anthropic_client.messages.create(
            model=config["anthropic_model"] or "claude-3-5-sonnet-latest",
            system="\n\n".join(system_parts),
            messages=chat_messages,
            max_tokens=1024,
            temperature=0.1,
        )
        return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")

    async def _complete_ollama(self, config: Dict[str, str], messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": config["ollama_model"],
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1},
        }

        async with httpx.AsyncClient(timeout=self._request_timeout_sec()) as client:
            response = await client.post(f"{config['ollama_url']}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    async def complete(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> str:
        config = self._load_config()
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        provider = config["provider"]
        try:
            if provider == "azure":
                return await self._complete_azure(config, full_messages)
            if provider == "openai":
                return await self._complete_openai(config, full_messages)
            if provider == "anthropic":
                return await self._complete_anthropic(config, full_messages)
            if provider == "ollama":
                return await self._complete_ollama(config, full_messages)
            if provider == "mock":
                return "AI отключен: выбран provider mock. Настройте провайдера в Settings."
            return f"Неизвестный AI provider: {provider}"
        except Exception as error:
            err = str(error).lower()
            if "timed out" in err or "timeout" in err:
                return (
                    f"Ошибка AI provider ({provider}): превышено время ожидания. "
                    f"Для медленных моделей (например DeepSeek R1) задайте в .env AI_REQUEST_TIMEOUT_SEC=600 и перезапустите API. "
                    f"({error})"
                )
            return f"Ошибка AI provider ({provider}): {error}"


ai_provider = AIProvider()