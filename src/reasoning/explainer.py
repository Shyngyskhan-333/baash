"""
LLM Explainer для объяснения коллизий.
Читает конфиг из data/ai_config.json (Settings UI) с fallback на .env.
"""
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path("data/ai_config.json")


def _load_config() -> dict:
    """Load dynamic config (Settings UI) with .env as fallback."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "provider": os.getenv("AI_PROVIDER", "mock"),
        "model": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "ollama_url": "http://localhost:11434",
        "ollama_model": "qwen2.5:7b",
    }


PROMPT_CONTRADICTION = """\
Ты — старший юридический аналитик законодательства Казахстана.
Две нормы (статьи или пункты) противоречат друг другу:

НОРМА A ({law_a}):
{text_a}

НОРМА B ({law_b}):
{text_b}

Объясни противоречие и верни ответ строго в формате JSON (без markdown, без ```):
{{
  "contradiction": true,
  "type": "direct" или "partial",
  "explanation": "Объяснение в 3-4 предложениях",
  "articles_involved": ["Статья N...", "Статья M..."]
}}
"""


def _extract_json(text: str) -> dict:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {
            "contradiction": True,
            "type": "parse_error",
            "explanation": f"Ошибка парсинга JSON: {text[:200]}",
            "articles_involved": [],
        }


def explain_contradiction(text_a: str, text_b: str, law_a: str, law_b: str) -> dict:
    """
    Объясняет противоречие через AI-провайдер.
    Читает конфигурацию динамически (поддерживает обновление через Settings UI).
    """
    cfg = _load_config()
    provider = cfg.get("provider", "mock").lower()

    prompt = PROMPT_CONTRADICTION.format(
        law_a=law_a, law_b=law_b,
        text_a=text_a[:600], text_b=text_b[:600]
    )

    try:
        if provider == "azure":
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=cfg.get("api_key", ""),
                api_version="2024-02-01",
                azure_endpoint=cfg.get("endpoint", ""),
            )
            resp = client.chat.completions.create(
                model=cfg.get("model", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600, temperature=0.1
            )
            return _extract_json(resp.choices[0].message.content or "{}")

        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=cfg.get("api_key", ""))
            resp = client.chat.completions.create(
                model=cfg.get("model", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600, temperature=0.1
            )
            return _extract_json(resp.choices[0].message.content or "{}")

        elif provider == "ollama":
            import httpx
            ollama_url = cfg.get("ollama_url", "http://localhost:11434")
            model = cfg.get("ollama_model", "qwen2.5:7b")
            resp = httpx.post(
                f"{ollama_url}/api/chat",
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False},
                timeout=90.0
            )
            resp.raise_for_status()
            content = resp.json().get("message", {}).get("content", "{}")
            return _extract_json(content)

        elif provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=cfg.get("api_key", ""))
            resp = client.messages.create(
                model=cfg.get("model", "claude-3-5-sonnet-20241022"),
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            return _extract_json(resp.content[0].text)

        else:
            return {
                "contradiction": True,
                "type": "mock",
                "explanation": "AI_PROVIDER не настроен. Перейдите в Настройки AI.",
                "articles_involved": [law_a, law_b],
            }

    except Exception as e:
        return {
            "contradiction": True,
            "type": "error",
            "explanation": f"Ошибка AI-анализа: {e}",
            "articles_involved": [law_a, law_b],
        }
