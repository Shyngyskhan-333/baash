import asyncio
import concurrent.futures
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.scraper.adilet_scraper import parse_batch
from api.services.nlp_service import nlp_service

router = APIRouter()

def _safe_doc_id(doc_id: str) -> str:
    if not doc_id or doc_id.strip() != doc_id:
        raise HTTPException(status_code=400, detail="Некорректный идентификатор документа")
    for bad in ("..", "/", "\\"):
        if bad in doc_id:
            raise HTTPException(status_code=400, detail="Некорректный идентификатор документа")
    return doc_id


def _base_doc_id(doc_id: str) -> str:
    safe_doc_id = _safe_doc_id(doc_id)
    if safe_doc_id.endswith("_current"):
        return safe_doc_id[:-8]
    if re.search(r"_\d+$", safe_doc_id):
        return safe_doc_id.rsplit("_", 1)[0]
    return safe_doc_id

class IndexRequest(BaseModel):
    doc_ids: List[str]

class PreviewResponse(BaseModel):
    doc_id: str
    title: str
    date: Optional[str] = ""
    versions_found: int = 1
    versions: List[dict] = Field(default_factory=list)

def _run_index(doc_ids: List[str]) -> dict:

    docs = parse_batch(doc_ids)
    if docs:
        added = nlp_service.retriever.add_documents(docs)

        for doc in docs:
            doc_id = doc.get("doc_id")
            if doc_id:
                print(f"[INDEX_AUTO_ANALYZE] Triggering auto-analysis for {doc_id}")
                nlp_service.analyze_document_fast(doc_id)

        return {"status": "success", "added_chunks": added, "docs_processed": len(docs)}
    return {"status": "success", "added_chunks": 0, "message": "Docs already indexed or not found", "docs_processed": 0}

@router.post("/index/build")
async def build_index(req: IndexRequest):
    print(f"[INDEX] Scrape & Index requested for: {req.doc_ids}")
    if not req.doc_ids:
        raise HTTPException(status_code=400, detail="doc_ids list is empty")
    try:

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(pool, _run_index, req.doc_ids)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/preview/{doc_id}", response_model=PreviewResponse)
async def preview_document(doc_id: str):
    requested_doc_id = _safe_doc_id(doc_id)
    base_doc_id = _base_doc_id(requested_doc_id)
    print(f"[PREVIEW] Fetching info for: {requested_doc_id} -> {base_doc_id}")
    from src.scraper.adilet_scraper import fetch_versions
    try:
        versions = await fetch_versions(base_doc_id)
        if not versions:
            raise HTTPException(status_code=404, detail="Document not found on Adilet")

        current = versions[0]["doc"]
        return PreviewResponse(
            doc_id=base_doc_id,
            title=current.get("title", ""),
            date=current.get("date", ""),
            versions_found=len(versions),
            versions=[{"version_id": v["version_id"], "date": v["date"], "status": v["status"]} for v in versions]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[PREVIEW] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/document/{doc_id}")
async def get_document_full(doc_id: str):

    import json
    from pathlib import Path
    from src.scraper.adilet_scraper import fetch_by_url

    safe_doc_id = _safe_doc_id(doc_id)
    exact_path = Path("data/parsed") / f"{safe_doc_id}.json"
    fallback_path = Path("data/parsed") / f"{_base_doc_id(safe_doc_id)}.json"
    archive_match = re.fullmatch(r"([A-Z]\d+_?)_(\d{2}\.\d{2}\.\d{4})", safe_doc_id, re.IGNORECASE)
    doc = None

    parsed_path = exact_path
    if not parsed_path.exists() and archive_match:
        doc = await fetch_by_url(
            f"https://adilet.zan.kz/rus/archive/docs/{archive_match.group(1).upper()}/{archive_match.group(2)}"
        )
    elif not parsed_path.exists():
        parsed_path = fallback_path

    if doc is None and not parsed_path.exists():
        raise HTTPException(status_code=404, detail="Document not found. Scrape it first.")

    if doc is None:
        with open(parsed_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

    full_text = ""
    for art in doc.get("articles", []):
        block = (art.get("text") or "").strip()
        if not block and art.get("chunks"):
            block = "\n\n".join((c.get("text") or "").strip() for c in art["chunks"] if c.get("text"))
        full_text += block + "\n\n"

    return {"doc_id": safe_doc_id, "title": doc.get("title", ""), "text": full_text.strip()}


@router.get("/index/document/by-url")
async def get_document_by_url(
    url: str = Query(..., description="Adilet document or archive URL"),
):
    try:
        from src.scraper.adilet_scraper import fetch_by_url
        doc = await fetch_by_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    full_text = ""
    for art in doc.get("articles", []):
        block = (art.get("text") or "").strip()
        if not block and art.get("chunks"):
            block = "\n\n".join((c.get("text") or "").strip() for c in art["chunks"] if c.get("text"))
        full_text += block + "\n\n"

    return {"doc_id": doc.get("doc_id", ""), "title": doc.get("title", ""), "text": full_text.strip()}