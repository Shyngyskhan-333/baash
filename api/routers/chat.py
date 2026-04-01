from fastapi import APIRouter, HTTPException
from typing import List

from api.models.schemas import ChatRequest, ChatResponse, Source, SuggestedArticle
from api.services.nlp_service import nlp_service
from api.services.ai_provider import ai_provider

router = APIRouter()

SYSTEM_PROMPT = """\
Ты AI-помощник, юрист и эксперт по законодательству Казахстана (LexEntropy).
- Отвечай ТОЛЬКО на русском языке.
- Опирайся ИСКЛЮЧИТЕЛЬНО на предоставленный контекст из казахстанских НПА.
- Ссылайся на конкретные статьи из контекста.
- Объясняй юридические термины простым и понятным языком.
- Если в контексте нет ответа — честно скажи об этом.
"""


def _build_context(request: ChatRequest):
    """Build context_text and sources from search results."""
    context_text = ""
    sources: List[Source] = []
    suggested_articles: List[SuggestedArticle] = []

    if request.doc_id:
        top_k = 3 if request.mode == "article_search" else 2
        search_res = nlp_service.search_within_document(request.doc_id, request.message, top_k=top_k)
        for item in search_res:
            art   = item.get("article_number", "")
            title = item.get("doc_title", "")
            text  = item.get("text", "")
            score = item.get("cosine_score", 0.0) or item.get("rrf_score", 0.0)
            sources.append(Source(article=art, text=text[:300] + "...", relevance=round(score, 4)))
            if request.mode == "article_search":
                suggested_articles.append(SuggestedArticle(doc_id=request.doc_id, article=art, title=title))
            context_text += f"Статья: {art}\nТекст: {text}\n---\n"
    else:
        search_res = nlp_service.search(request.message, top_k=4)
        for item in search_res.get("results", []):
            doc_title = item.get("doc_title", "")
            art   = item.get("article_number", "")
            text  = item.get("text", "")
            score = item.get("cosine_score", 0.0) or item.get("rrf_score", 0.0)
            sources.append(Source(article=f"{doc_title}, {art}", text=text[:300] + "...", relevance=round(score, 4)))
            context_text += f"Закон: {doc_title}\nСтатья: {art}\nТекст: {text}\n---\n"

    return context_text, sources, suggested_articles


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat_interaction(request: ChatRequest):
    context_text, sources, suggested_articles = _build_context(request)

    messages = [{"role": msg.role, "content": msg.content} for msg in request.history]
    user_prompt = f"Вопрос: {request.message}\n\nКонтекст (найденные материалы):\n{context_text}"
    messages.append({"role": "user", "content": user_prompt})

    try:
        ai_response = await ai_provider.complete(messages=messages, system_prompt=SYSTEM_PROMPT)
    except Exception as e:
        # Graceful degradation — return context-based answer without LLM
        ai_response = (
            "⚠️ **AI-провайдер недоступен.** Настройте провайдера в разделе [Настройки AI](/settings).\n\n"
            f"**Найденные материалы по запросу:**\n"
            + "\n".join(f"- {s.article}: {s.text[:150]}..." for s in sources[:3])
            if sources else "Документы по запросу не найдены в базе."
        )

    return ChatResponse(
        answer=ai_response,
        sources=sources,
        suggested_articles=suggested_articles,
    )
