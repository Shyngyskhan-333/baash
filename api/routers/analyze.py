import re
import json
import hashlib
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional

from api.models.schemas import AnalyzeResponse, RelatedLaw
from api.services.nlp_service import nlp_service
from api.services.ai_provider import ai_provider
from src.evidence.analyze_grounding import ground_analyze_summary

router = APIRouter()
CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_ANALYZE_CACHE_VERSION = "legal_content_v1"
_CACHE_MODE_MARK = "content_only"

def _safe_doc_id(doc_id: str) -> str:
    if not doc_id or doc_id.strip() != doc_id:
        raise HTTPException(status_code=400, detail="Некорректный идентификатор документа")
    for bad in ("..", "/", "\\"):
        if bad in doc_id:
            raise HTTPException(status_code=400, detail="Некорректный идентификатор документа")
    return doc_id

def _article_body(art: dict) -> str:
    t = (art.get("text") or "").strip()
    if not t and art.get("chunks"):
        t = "\n\n".join((c.get("text") or "").strip() for c in art["chunks"] if c.get("text"))
    return t

def _compact_doc_excerpt(doc: dict, max_chars: int = 14000) -> str:

    parts: List[str] = []
    for art in doc.get("articles") or []:
        body = _article_body(art)
        if not body:
            continue
        header = (art.get("article_number") or "Фрагмент").strip()
        parts.append(f"### {header}\n{body}")
    full = "\n\n".join(parts)
    if len(full) <= max_chars:
        return full
    return full[: max_chars - 1] + "…"

def _related_laws_from_references(doc: dict, max_items: int = 40) -> List[RelatedLaw]:

    refs = doc.get("references") or []
    out: List[RelatedLaw] = []
    seen: set = set()
    for rid in refs:
        if not isinstance(rid, str):
            continue
        rid = rid.strip()
        if not rid or rid in seen:
            continue
        seen.add(rid)
        title = rid
        other = nlp_service.get_document_by_id(rid)
        if other and other.get("title"):
            title = str(other["title"])
        out.append(RelatedLaw(doc_id=rid, title=title, relevance_score=1.0))
        if len(out) >= max_items:
            break
    return out

def _extract_doc_id_from_url(url: str) -> str:
    match = re.search(r"/docs/([A-Z0-9]+)", url)
    if match:
        return match.group(1)
    raise ValueError("Invalid adilet.zan.kz URL")

@router.get("/analyze/by-url", response_model=AnalyzeResponse)
async def analyze_document_url(
    url: str = Query(..., description="Adilet URL"),
    doc_ids: Optional[List[str]] = Query(None),
    force_refresh: bool = Query(False),
):
    print(f"[ANALYZE] Request for URL: {url}. Scope: {doc_ids}")
    try:
        doc_id = _extract_doc_id_from_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    doc_id = _safe_doc_id(doc_id)
    return await _process_analyze(doc_id, doc_ids, force_refresh=force_refresh)

@router.get("/analyze/{doc_id}", response_model=AnalyzeResponse)
async def analyze_document_id(
    doc_id: str,
    doc_ids: Optional[List[str]] = Query(None),
    force_refresh: bool = Query(False),
):
    doc_id = _safe_doc_id(doc_id)
    print(f"[ANALYZE] Request for doc_id: {doc_id}. Scope: {doc_ids}")
    return await _process_analyze(doc_id, doc_ids, force_refresh=force_refresh)

def _scope_cache_key(doc_id: str, doc_ids: Optional[List[str]]) -> str:
    scope = "all" if not doc_ids else ",".join(sorted(set(doc_ids)))
    raw = f"{doc_id}|{scope}|{_ANALYZE_CACHE_VERSION}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{doc_id}_{digest}"

def _cache_path(doc_id: str, doc_ids: Optional[List[str]]) -> Path:
    return CACHE_DIR / f"analyze_{_scope_cache_key(doc_id, doc_ids)}.json"

def _load_cached_analyze(doc_id: str, doc_ids: Optional[List[str]]) -> Optional[dict]:
    path = _cache_path(doc_id, doc_ids)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and payload.get("analyze_mode") == _CACHE_MODE_MARK:
            return payload
    except Exception:
        return None
    return None

def _load_cached_analyze_any(doc_id: str) -> Optional[dict]:
    candidates = sorted(
        CACHE_DIR.glob(f"analyze_{doc_id}_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict) and payload.get("analyze_mode") == _CACHE_MODE_MARK:
                return payload
        except Exception:
            continue
    return None

def _save_cached_analyze(doc_id: str, doc_ids: Optional[List[str]], data: dict) -> None:
    path = _cache_path(doc_id, doc_ids)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

async def _process_analyze(doc_id: str, doc_ids: Optional[List[str]] = None, force_refresh: bool = False) -> AnalyzeResponse:
    if not force_refresh:
        cached = _load_cached_analyze(doc_id, doc_ids)
        if cached is not None:
            cached.pop("analyze_mode", None)
            return AnalyzeResponse(**cached)
        if doc_ids is None:
            cached_any = _load_cached_analyze_any(doc_id)
            if cached_any is not None:
                cached_any.pop("analyze_mode", None)
                return AnalyzeResponse(**cached_any)

    doc = nlp_service.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    title = doc.get("title", f"Document {doc_id}")
    excerpt = _compact_doc_excerpt(doc)
    related_laws = _related_laws_from_references(doc)

    summary_prompt = (
        "Сделай краткий смысловой разбор нормативного акта Республики Казахстан. "
        "Не оценивай коллизии и юридические риски, если они не указаны во входных данных. "
        "Явно укажи, что это смысловой разбор, а не юридическое заключение. "
        "Верни JSON с полями summary, summary_short, sections и reasoning.\n\n"
        f"Документ: {title}\n"
        f"ID: {doc_id}\n\n"
        f"Текст:\n{excerpt}"
    )

    try:
        ai_response = await ai_provider.complete(
            messages=[{"role": "user", "content": summary_prompt}],
            system_prompt="Ты AI-аналитик нормативных актов РК. Пишешь точно и по тексту, без коллизионного анализа.",
        )
    except Exception as error:
        ai_response = f"AI недоступен: {error}"

    if "insufficient_quota" in (ai_response or ""):
        ai_response = ""

    text = re.sub(r"```json\s*", "", ai_response or "")
    text = re.sub(r"```\s*", "", text)

    think_match = re.search(r"<redacted_thinking>(.*?)</redacted_thinking>", text, flags=re.DOTALL)
    think_content = think_match.group(1).strip() if think_match else ""
    text = re.sub(r"<redacted_thinking>.*?</redacted_thinking>", "", text, flags=re.DOTALL)

    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        text = json_match.group(0)

    ai_summary = ""
    ai_summary_short = ""
    ai_sections: Dict[str, Any] = {}
    ai_reasoning = ""

    try:
        data = json.loads(text.strip())
        ai_summary = data.get("summary", "") or data.get("summary_short", "")
        ai_summary_short = data.get("summary_short", "")
        ai_sections = data.get("sections") or {}
        ai_reasoning = data.get("reasoning", "")
        if think_content and not ai_reasoning:
            ai_reasoning = think_content
    except Exception:
        ai_summary = text.strip()
        ai_reasoning = think_content

    if isinstance(ai_reasoning, list):
        ai_reasoning = "\n".join(str(item) for item in ai_reasoning if item is not None)
    elif isinstance(ai_reasoning, dict):
        ai_reasoning = json.dumps(ai_reasoning, ensure_ascii=False)
    elif ai_reasoning is not None:
        ai_reasoning = str(ai_reasoning)

    if not ai_summary:
        ai_summary = (
            "Смысловой разбор недоступен (AI не настроен или ответ не распознан). "
            "Коллизии и пересечения с другими актами смотрите в разделе «Глобальный аудит» и на графе."
        )
    if not ai_summary_short:
        ai_summary_short = ai_summary.split("\n")[0].strip() if ai_summary else ""

    if isinstance(ai_sections, dict):
        ai_sections = {
            str(k): v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            for k, v in ai_sections.items()
        }

    result = AnalyzeResponse(
        doc_id=doc_id,
        title=title,
        risk_score=0.0,
        risk_level="medium",
        issues=[],
        summary=ai_summary,
        summary_short=ai_summary_short,
        sections=ai_sections if isinstance(ai_sections, dict) else None,
        reasoning=ai_reasoning,
        related_laws=related_laws,
    )
    if not result.summary.startswith("[Смысловой разбор]"):
        result.summary = "[Смысловой разбор] " + result.summary
    if result.summary_short and not result.summary_short.startswith("[Смысловой разбор]"):
        result.summary_short = "[Смысловой разбор] " + result.summary_short

    try:
        result.grounding = ground_analyze_summary(
            doc_id=doc_id,
            title=title,
            doc=doc,
            summary=result.summary,
            messages=[{"role": "user", "content": summary_prompt}],
            system_prompt="LexLens analyze summary prompt v1",
            model_name="configured-ai-provider",
            model_version="analyze-summary-v1",
        )
    except Exception as error:
        print(f"[ANALYZE_GROUNDING_ERROR] {error}")

    payload = result.model_dump()
    payload["analyze_mode"] = _CACHE_MODE_MARK
    _save_cached_analyze(doc_id, doc_ids, payload)
    return result
