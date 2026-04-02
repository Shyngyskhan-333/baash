from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any

from api.models.schemas import ChatRequest, ChatResponse, Source, SuggestedArticle
from api.services.nlp_service import nlp_service
from api.services.ai_provider import ai_provider

router = APIRouter()

SYSTEM_PROMPT = """\
Role: You are an expert analyst with access to the entire project knowledge base. Your goal is to provide high-fidelity synthesis across all provided documents.

Operational Protocols:

Multi-Source Synthesis: Cross-reference all available data. If a query spans multiple documents, integrate the facts into a single, cohesive response.

Conflict Detection: If you encounter contradictory data (e.g., different dates, versions, or laws), explicitly list the contradictions. Do not guess which is correct.

Strict Attribution: Every factual claim must be followed by a source tag in brackets, e.g., [Document Name/ID].

Knowledge Boundary: * Priority: Project Data.

Gap Filling: If the data is missing, you may use general knowledge but must prefix it with: "General AI Insight (not in project files):".

No-Fluff Output: Provide direct answers. Avoid introductory phrases like "Based on the documents provided..."

Formatting: Use bold headers for key concepts and bullet points for technical specifications.
"""


def _build_context(request: ChatRequest):
    """Build context_text and sources from global unified vector search."""
    context_text = ""
    sources: List[Source] = []
    suggested_articles: List[SuggestedArticle] = []

    # Unified Retrieval: Global search over entire vector database index
    # Ignoring `request.doc_id` or `request.doc_ids` bounds as per requirements
    search_res = nlp_service.search(request.message, top_k=8, doc_ids=None)
    
    max_score = 0.0
    for item in search_res.get("results", []):
        doc_title = item.get("doc_title", "")
        art   = item.get("article_number", "")
        text  = item.get("text", "")
        score = item.get("cosine_score", 0.0) or item.get("rrf_score", 0.0)
        
        if score > max_score:
            max_score = float(score)
            
        sources.append(Source(article=f"{doc_title}, {art}", text=text[:300] + "...", relevance=round(score, 4)))
        context_text += f"[Source: {doc_title}] Content: {text}\n"

    return context_text, sources, suggested_articles, max_score


@router.post("/chat", response_model=ChatResponse)
async def chat_interaction(request: ChatRequest):
    print(f"[CHAT] Message received: '{request.message[:50]}...'. Scope: {request.doc_ids}")
    
    try:
        context_text, sources, suggested_articles, max_score = _build_context(request)

        messages = [{"role": msg.role, "content": msg.content} for msg in request.history]
        
        fallback_msg = ""
        if not sources or max_score < 0.35:
            fallback_msg = "\n\nWARNING: The confidence score of the retrieved project data is low. You must explicitly state that the answer is being generated from your pre-trained weights, not the project data!"

        user_prompt = f"ВОПРОС ПОЛЬЗОВАТЕЛЯ: {request.message}\n\nPROJECT DATA CONTENT:\n{context_text}{fallback_msg}"
        messages.append({"role": "user", "content": user_prompt})

        try:
            ai_response = await ai_provider.complete(messages=messages, system_prompt=SYSTEM_PROMPT)
        except Exception as e:
            # Graceful degradation — return context-based answer without LLM
            ai_response = (
                "⚠️ **AI-провайдер недоступен.** Проверьте настройки в .env.\n\n"
                f"**Найденные материалы по запросу:**\n"
                + "\n".join(f"- {s.article}: {s.text[:150]}..." for s in sources[:3])
                if sources else "Документы по запросу не найдены в базе."
            )

        return ChatResponse(
            answer=ai_response,
            sources=sources,
            suggested_articles=suggested_articles,
        )
    except Exception as e:
        print(f"[CHAT_ERROR] Global crash: {e}")
        return ChatResponse(
            answer=f"❌ Внутренняя ошибка сервера: {str(e)}",
            sources=[],
            suggested_articles=[],
        )

