import re
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional

from api.models.schemas import AnalyzeResponse, Issue, RelatedLaw
from api.services.nlp_service import nlp_service
from api.services.ai_provider import ai_provider

router = APIRouter()

def _extract_doc_id_from_url(url: str) -> str:
    # Example: https://adilet.zan.kz/rus/docs/K1500000377
    match = re.search(r"/docs/([A-Z0-9]+)", url)
    if match:
        return match.group(1)
    raise ValueError("Invalid adilet.zan.kz URL")

@router.get("/analyze/{doc_id}", response_model=AnalyzeResponse)
async def analyze_document_id(doc_id: str, doc_ids: Optional[List[str]] = Query(None)):
    print(f"[ANALYZE] Request for doc_id: {doc_id}. Scope: {doc_ids}")
    return await _process_analyze(doc_id, doc_ids)

@router.get("/analyze/by-url", response_model=AnalyzeResponse)
async def analyze_document_url(url: str = Query(..., description="Adilet URL"), doc_ids: Optional[List[str]] = Query(None)):
    print(f"[ANALYZE] Request for URL: {url}. Scope: {doc_ids}")
    try:
        doc_id = _extract_doc_id_from_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await _process_analyze(doc_id, doc_ids)

async def _process_analyze(doc_id: str, doc_ids: Optional[List[str]] = None) -> AnalyzeResponse:
    # 1. Fetch document text
    doc = nlp_service.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    title = doc.get("title", f"Document {doc_id}")
    
    # 2. Extract issues
    analysis_data = nlp_service.analyze_document(doc_id, doc_ids=doc_ids)
    
    issues = []
    related_laws_dict = {}
    
    for p in analysis_data.get("problems", []):
        # Determine the other document related to this issue
        is_anchor = p.chunk_a.get("doc_id") == doc_id
        current_chunk = p.chunk_a if is_anchor else p.chunk_b
        related_chunk = p.chunk_b if is_anchor else p.chunk_a
        
        related_doc_id = related_chunk.get("doc_id")
        
        iss = Issue(
            type=p.type,
            article=current_chunk.get("article_number", ""),
            description=f"Взаимодействие с {related_chunk.get('doc_title', related_doc_id)} ({related_chunk.get('article_number', '')})",
            severity="high" if p.type in ("contradiction", "collision") else "medium" if p.type == "outdated" else "low",
            related_doc_id=related_doc_id,
            explanation=p.explanation.get("explanation", "") if p.explanation else None
        )
        issues.append(iss)
        
        if related_doc_id and related_doc_id != doc_id:
            related_laws_dict[related_doc_id] = {
                "title": related_chunk.get("doc_title", related_doc_id),
                "score": p.scores.get("cosine", 0.0)
            }
            
    # Calculate risk score (0.0 to 1.0)
    risk_score = 0.0
    if issues:
        base_risk = min(1.0, len(issues) * 0.1)
        # boost risk if there are contradictions
        if any(i.type in ("contradiction", "collision") for i in issues):
            risk_score = min(1.0, base_risk + 0.4)
        else:
            risk_score = base_risk
            
    risk_level = "high" if risk_score > 0.6 else "medium" if risk_score > 0.3 else "low"
    
    # Generate AI summary for the analysis
    summary_prompt = f"""
    Проанализируй результаты аудита закона "{title}".
    Найдено проблем: {len(issues)}. 
    Оцени общий риск ({risk_level}) и кратко (2-3 предложения) опиши ситуацию.
    Отвечай на русском языке строго в формате JSON (без markdown и тегов кода):
    {{
      "reasoning": "Твой подробный процесс размышления, анализ каждой проблемы",
      "summary": "Окончательный ответ, выводы (AI Резюме)"
    }}
    """
    ai_response = await ai_provider.complete(
        messages=[{"role": "user", "content": summary_prompt}],
        system_prompt="Ты AI-юрист, аудитор законодательства."
    )
    
    import json
    
    # Пытаемся извлечь JSON
    text = re.sub(r"```json\s*", "", ai_response)
    text = re.sub(r"```\s*", "", text)
    
    # Пытаемся извлечь <think> тег для fallbacks
    think_match = re.search(r"<think>(.*?)</think>", text, flags=re.DOTALL)
    think_content = think_match.group(1).strip() if think_match else ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    
    # Ищем JSON-блок, если модель ответила с текстом до и после
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        text = json_match.group(0)
        
    ai_summary = ""
    ai_reasoning = ""
    
    try:
        data = json.loads(text.strip())
        ai_summary = data.get("summary", "")
        ai_reasoning = data.get("reasoning", "")
        if think_content and not ai_reasoning:
            ai_reasoning = think_content
    except Exception:
        ai_summary = text.strip()
        ai_reasoning = think_content

    related_laws = [
        RelatedLaw(doc_id=r_id, title=r_data["title"], relevance_score=r_data["score"])
        for r_id, r_data in related_laws_dict.items()
    ]
    
    return AnalyzeResponse(
        doc_id=doc_id,
        title=title,
        risk_score=risk_score,
        risk_level=risk_level,
        issues=issues,
        summary=ai_summary,
        reasoning=ai_reasoning,
        related_laws=related_laws
    )
