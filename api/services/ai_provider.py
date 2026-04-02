"""
Единый AI-провайдер: Azure OpenAI Only.
Настраивается исключительно через файл .env.
Динамические настройки удалены для стабильности.
"""
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()

class AIProvider:
    def __init__(self):
        # Настройки считываются напрямую из .env и очищаются от лишних пробелов/слэшей
        self.api_key = (os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY", "")).strip()
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o").strip()
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview").strip()
        
        self._client = None
        print(f"[AI_INIT] Azure Provider initialized for endpoint: {self.endpoint}, deployment: {self.deployment}")

    def _get_client(self):
        if not self._client:
            if not self.api_key or not self.endpoint:
                print("[AI_ERROR] Missing AZURE_OPENAI_KEY or ENDPOINT in .env")
                return None
            try:
                self._client = AsyncAzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint,
                )
            except Exception as e:
                print(f"[AI_ERROR] Client initialization failed: {e}")
                return None
        return self._client

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Выполняет запрос к Azure OpenAI."""
        client = self._get_client()
        if not client:
            return "❌ Ошибка конфигурации AI: AZURE_OPENAI_KEY или ENDPOINT не заданы в .env"

        try:
            full_messages = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            print(f"[AI_REQ] Sending request to deployment '{self.deployment}' via {self.endpoint}")
            resp = await client.chat.completions.create(
                model=self.deployment,
                messages=full_messages,
                temperature=0.1,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            err_str = str(e)
            msg = f"❌ Ошибка Azure OpenAI ({self.deployment}): {err_str}"
            print(f"[AI_ERROR] Full details: {err_str}")
            
            # Common Azure errors
            if "Resource not found" in err_str:
                msg = f"❌ Ошибка 404: Ресурс или деплоймент '{self.deployment}' не найден.\nСовет: проверьте AZURE_OPENAI_DEPLOYMENT в .env."
            elif "Access denied" in err_str or "unauthorized" in err_str.lower():
                msg = "❌ Ошибка 401: Доступ запрещен.\nСовет: проверьте правильность AZURE_OPENAI_KEY в .env."
            elif "endpoint" in err_str.lower():
                msg = f"❌ Ошибка соединения: Неверный ENDPOINT.\nСовет: проверьте AZURE_OPENAI_ENDPOINT: {self.endpoint}"
            
            return msg


# Singleton
ai_provider = AIProvider()
