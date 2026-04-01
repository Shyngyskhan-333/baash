from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import concurrent.futures

from src.retrieval.retriever import LegalRetriever
from src.scraper.adilet_scraper import parse_batch

router = APIRouter()

class IndexRequest(BaseModel):
    doc_ids: List[str]

def _run_index(doc_ids: List[str]) -> dict:
    """Runs the full index pipeline safely in a thread (avoids asyncio conflicts)."""
    docs = parse_batch(doc_ids)
    retriever = LegalRetriever()
    if docs:
        added = retriever.add_documents(docs)
        return {"status": "success", "added_chunks": added, "docs_processed": len(docs)}
    return {"status": "success", "added_chunks": 0, "message": "Docs already indexed or not found", "docs_processed": 0}

@router.post("/api/v1/index/build")
async def build_index(req: IndexRequest):
    """
    Parses and indexes a list of document IDs from adilet.zan.kz.
    Runs in a thread pool to avoid blocking the async event loop.
    """
    if not req.doc_ids:
        raise HTTPException(status_code=400, detail="doc_ids list is empty")
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(pool, _run_index, req.doc_ids)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
