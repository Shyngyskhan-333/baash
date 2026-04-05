from fastapi import APIRouter
from typing import List

from api.models.schemas import ChatRequest, ChatResponse, Source, SuggestedArticle
from api.services.nlp_service import nlp_service
from api.services.ai_provider import ai_provider

router = APIRouter()

SYSTEM_PROMPT = 

def _build_context(request: ChatRequest):

    context_text = ""
    sources: List[Source] = []
    suggested_articles: List[SuggestedArticle] = []

    scope_doc_ids = request.doc_ids or ([request.doc_id] if request.doc_id else None)
    search_res = nlp_service.search(request.message, top_k=8, doc_ids=scope_doc_ids)

    max_score = 0.0
    for item in search_res.get("results", []):
        doc_title = item.get("doc_title", "")
        art = item.get("article_number", "")
        text = item.get("text", "")
        score = item.get("cosine_score", 0.0) or item.get("rrf_score", 0.0)

        if score > max_score:
            max_score = float(score)

        sources.append(
            Source(
                article=f"{doc_title}, {art}",
                text=text[:300] + "...",
                relevance=round(score, 4),
            )
        )
        if item.get("doc_id") and art:
            suggested_articles.append(
                SuggestedArticle(
                    doc_id=item["doc_id"],
                    article=art,
                    title=doc_title,
                )
            )

        context_text += f"[Source: {doc_title}] Content: {text[:600]}\n"

    context_text = context_text[:8000]

    return context_text, sources, suggested_articles, max_score

@router.post("/chat", response_model=ChatResponse)
async def chat_interaction(request: ChatRequest):
    print(f"[CHAT] Message received: '{request.message[:50]}...'. Scope: {request.doc_ids}")

    try:
        context_text, sources, suggested_articles, max_score = _build_context(request)

        messages = [{"role": msg.role, "content": msg.content} for msg in request.history]

        fallback_msg = ""
        if not sources or max_score < 0.35:
            fallback_msg = (
                "\n\nВнимание: релевантность найденных фрагментов низкая. "
                "Если ответ опирается на общие знания, обязательно укажите это явно."
            )

        user_prompt = (
            f"ВОПРОС ПОЛЬЗОВАТЕЛЯ: {request.message}\n\n"
            f"КОНТЕКСТ ПРОЕКТА:\n{context_text}{fallback_msg}"
        )
        messages.append({"role": "user", "content": user_prompt})

        explainability = ""
        try:
            ai_response = await ai_provider.complete(messages=messages, system_prompt=SYSTEM_PROMPT)
        except Exception:

            if sources:
                ai_response = (
                    "**AI‑провайдер недоступен.** Проверьте настройки в разделе Settings.\n\n"
                    "**Найденные материалы по запросу:**\n"
                    + "\n".join(f"- {s.article}: {s.text[:150]}..." for s in sources[:3])
                )
            else:
                ai_response = "AI‑провайдер недоступен. Проверьте настройки в разделе Settings."
            explainability = (
                f"LLM недоступен; показан fallback по ретриверу. "
                f"Источников: {len(sources)}, max_score={max_score:.4f}."
            )
        else:
            top = max_score
            explainability = (
                f"Ответ построен на гибридном поиске (BM25+FAISS→RRF). "
                f"Максимальная релевантность фрагмента: {top:.4f} (косинус/сводный скор). "
                f"Использовано источников в контексте: {len(sources)}."
            )
            if top < 0.35:
                explainability += (
                    " Релевантность низкая — ответ может опираться на общие знания модели; "
                    "проверьте формулировку запроса и полноту индекса."
                )

        return ChatResponse(
            answer=ai_response,
            sources=sources,
            suggested_articles=suggested_articles,
            explanation=explainability or None,
        )
    except Exception as e:
        print(f"[CHAT_ERROR] Global crash: {e}")
        return ChatResponse(
            answer=f"Ошибка обработки запроса: {str(e)}",
            sources=[],
            suggested_articles=[],
        )