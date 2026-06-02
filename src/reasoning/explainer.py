
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path("data/ai_config.json")

PROMPT_CONTRADICTION = """
Сравни два фрагмента нормативных актов Республики Казахстан и объясни, есть ли между ними противоречие.
Отвечай строго JSON без markdown.

Формат:
{{
  "contradiction": true,
  "type": "semantic_conflict",
  "explanation": "краткое объяснение",
  "articles_involved": ["{law_a}", "{law_b}"]
}}

Акт A: {law_a}
Фрагмент A:
{text_a}

Акт B: {law_b}
Фрагмент B:
{text_b}
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

async def explain_contradiction(text_a: str, text_b: str, law_a: str, law_b: str, ai_caller) -> dict:

    prompt = PROMPT_CONTRADICTION.format(
        law_a=law_a, law_b=law_b,
        text_a=text_a[:600], text_b=text_b[:600]
    )

    content = await ai_caller([{"role": "user", "content": prompt}])
    return _extract_json(content)
