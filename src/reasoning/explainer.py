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


from api.services.ai_provider import ai_provider

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


async def explain_contradiction(text_a: str, text_b: str, law_a: str, law_b: str) -> dict:
    """
    Объясняет противоречие через единый AI-провайдер.
    Теперь использует централизованный ai_provider.complete.
    """
    prompt = PROMPT_CONTRADICTION.format(
        law_a=law_a, law_b=law_b,
        text_a=text_a[:600], text_b=text_b[:600]
    )

    content = await ai_provider.complete([{"role": "user", "content": prompt}])
    return _extract_json(content)
