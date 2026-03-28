"""
LLM-объяснения через Azure OpenAI (DeepSeek-R1 или GPT).
Вызывается ТОЛЬКО по клику пользователя — не на весь список.
"""
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

_client = None

def get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_KEY", ""),
            api_version="2024-02-01",
        )
    return _client


PROMPTS = {
    "duplicate": """\
Ты — старший юридический аналитик законодательства Казахстана.

Две нормы из разных нормативных актов:

НОРМА A (из: {law_a}):
{text_a}

НОРМА B (из: {law_b}):
{text_b}

Задача: объясни в 3-4 предложениях —
1. В чём конкретно состоит дублирование этих норм.
2. Какие практические проблемы это создаёт (правовая неопределённость, коррупционные риски, нагрузка на бизнес).
3. Какую из норм рекомендуется оставить или как их объединить.

Отвечай конкретно, без воды.""",

    "contradiction": """\
Ты — старший юридический аналитик законодательства Казахстана.

Две нормы, которые могут противоречить друг другу:

НОРМА A (из: {law_a}):
{text_a}

НОРМА B (из: {law_b}):
{text_b}

Задача: объясни в 3-4 предложениях —
1. В чём конкретно состоит противоречие.
2. Как это противоречие может использоваться недобросовестно.
3. Какая норма должна иметь приоритет и почему.

Отвечай конкретно, без воды.""",

    "outdated": """\
Ты — старший юридический аналитик законодательства Казахстана.

Норма из: {law_a}
{text_a}

Обнаруженный маркер устаревания: «{marker}»

Задача: объясни в 2-3 предложениях —
1. Почему эта норма, вероятно, устарела или утратила силу.
2. Какой риск несёт её формальное действие (лазейки, двусмысленность).
3. Что следует сделать: отменить, обновить, проверить актуальность.

Отвечай конкретно, без воды.""",

    "version_diff": """\
Ты — старший юридический аналитик законодательства Казахстана.

Сравниваются две редакции одной и той же нормы (статьи).

ПРЕДЫДУЩАЯ РЕДАКЦИЯ ({title_old}):
{text_old}

ТЕКУЩАЯ РЕДАКЦИЯ ({title_new}):
{text_new}

Семантическая близость текстов (косинус эмбеддингов): {score:.4f} (чем ниже, тем сильнее расхождение смысла).

Задача: в 2–4 предложениях опиши —
1. Что изменилось по смыслу между редакциями.
2. Какие практические последствия и риски это может дать для граждан, бизнеса или судов.

Не выдумывай ссылки на несуществующие статьи или акты. Если формулировки почти совпадают, скажи об этом кратко.""",
}


def explain(problem) -> str:
    """Получить LLM-объяснение для проблемы."""
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "deepseek-r1")
    prompt_template = PROMPTS[problem.type]

    prompt = prompt_template.format(
        law_a  = problem.article_a.get("doc_title", problem.article_a["doc_id"]),
        text_a = problem.article_a["text"][:1000],
        law_b  = problem.article_b.get("doc_title", "") if problem.article_b else "",
        text_b = problem.article_b["text"][:1000] if problem.article_b else "",
        marker = getattr(problem, "marker", ""),
    )

    try:
        client = get_client()
        resp = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )
        content = resp.choices[0].message.content or ""
        
        # Parse <think> block from deepseek-r1 so it doesn't get hidden as HTML in Streamlit
        import re
        if "<think>" in content:
            content = re.sub(
                r'<think>(.*?)</think>', 
                r'💭 **Ход мыслей (AI Reasoning):**\n```text\n\1\n```\n---\n**Ответ:**\n', 
                content, 
                flags=re.DOTALL
            )
        
        return content.strip()
    except Exception as e:
        return f"Ошибка при обращении к LLM: {e}"


def explain_version_diff(
    text_old: str,
    text_new: str,
    title_old: str,
    title_new: str,
    score: float,
) -> str:
    """LLM: краткое сравнение двух редакций одной статьи (вызывать по кнопке)."""
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "deepseek-r1")
    prompt = PROMPTS["version_diff"].format(
        title_old=title_old or "предыдущая редакция",
        title_new=title_new or "текущая редакция",
        text_old=(text_old or "")[:4000],
        text_new=(text_new or "")[:4000],
        score=float(score),
    )
    try:
        client = get_client()
        resp = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )
        content = resp.choices[0].message.content or ""
        import re

        if "\u003cthink\u003e" in content:
            content = re.sub(
                "\u003cthink\u003e(.*?)\u003c/think\u003e",
                r"💭 **Ход мыслей (AI Reasoning):**\n```text\n\1\n```\n---\n**Ответ:**\n",
                content,
                flags=re.DOTALL,
            )
        return content.strip()
    except Exception as e:
        return f"Ошибка при обращении к LLM: {e}"
