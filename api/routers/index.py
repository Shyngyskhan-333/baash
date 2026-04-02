from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import concurrent.futures

from src.retrieval.retriever import LegalRetriever
from src.scraper.adilet_scraper import parse_batch
from api.services.nlp_service import nlp_service

router = APIRouter()

class IndexRequest(BaseModel):
    doc_ids: List[str]

class PreviewResponse(BaseModel):
    doc_id: str
    title: str
    date: Optional[str] = ""
    versions_found: int = 1
    versions: List[dict] = []

def _run_index(doc_ids: List[str]) -> dict:
    """Runs the full index pipeline safely in a thread (avoids asyncio conflicts)."""
    docs = parse_batch(doc_ids)
    if docs:
        added = nlp_service.retriever.add_documents(docs)
        
        # Интеграция: сразу после индексации запускаем быстрый анализ для всех новых документов
        # Это наполняет ГРАФ автоматически при нажатии кнопки "Подтвердить"
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
        # For previewed docs, they might already be in data/parsed/
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(pool, _run_index, req.doc_ids)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/preview/{doc_id}", response_model=PreviewResponse)
async def preview_document(doc_id: str):
    print(f"[PREVIEW] Fetching info for: {doc_id}")
    from src.scraper.adilet_scraper import fetch_versions
    try:
        versions = await fetch_versions(doc_id)
        if not versions:
            raise HTTPException(status_code=404, detail="Document not found on Adilet")
            
        current = versions[0]["doc"]
        return PreviewResponse(
            doc_id=doc_id,
            title=current.get("title", ""),
            date=current.get("date", ""),
            versions_found=len(versions),
            versions=[{"version_id": v["version_id"], "date": v["date"], "status": v["status"]} for v in versions]
        )
    except Exception as e:
        print(f"[PREVIEW] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/document/{doc_id}")
async def get_document_full(doc_id: str):
    """Returns the full text of a document from data/parsed/."""
    import json
    from pathlib import Path
    parsed_path = Path("data/parsed") / f"{doc_id}.json"
    if not parsed_path.exists():
        raise HTTPException(status_code=404, detail="Document not found. Scrape it first.")
    
    with open(parsed_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
        
    full_text = ""
    for art in doc.get("articles", []):
        full_text += art.get("text", "") + "\n\n"
    
    return {"doc_id": doc_id, "title": doc.get("title", ""), "text": full_text.strip()}
