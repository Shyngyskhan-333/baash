from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import time
import asyncio

from api.routers.analyze import _process_analyze
from api.routers.audit import _run_audit, _save_cached_audit
from api.routers.graph import get_graph_html, get_graph_heatmap

router = APIRouter()

class PrecomputeRequest(BaseModel):
    doc_ids: Optional[List[str]] = None
    include_analyze: bool = True
    include_audit: bool = True
    include_graph: bool = True
    async_mode: bool = True

def _list_doc_ids() -> List[str]:
    parsed_dir = Path("data/parsed")
    if not parsed_dir.exists():
        return []
    return sorted({p.stem for p in parsed_dir.glob("*.json")})

async def _run_precompute(ids: List[str], req: PrecomputeRequest) -> dict:
    if req.async_mode:
        if background_tasks is None:
            background_tasks = BackgroundTasks()
        background_tasks.add_task(_run_precompute_sync, ids, req)
        return {
            "status": "queued",
            "doc_ids_count": len(ids),
            "analyze_cached": 0,
            "audit_cached": False,
            "graph_cached": False,
            "elapsed_sec": 0,
        }

    return await _run_precompute(ids, req)

def _run_precompute_sync(ids: List[str], req: PrecomputeRequest) -> None:
    asyncio.run(_run_precompute(ids, req))

@router.post("/precompute/all")
async def precompute_all(
    req: Optional[PrecomputeRequest] = None,
    background_tasks: BackgroundTasks = None,
):
    req = req or PrecomputeRequest()
    start = time.time()
    ids = req.doc_ids or _list_doc_ids()
    if not ids:
        raise HTTPException(status_code=400, detail="No documents available for precompute.")

    analyze_count = 0
    if req.include_analyze:
        for doc_id in ids:
            await _process_analyze(doc_id, doc_ids=ids, force_refresh=True)
            analyze_count += 1

    audit_done = False
    if req.include_audit:
        audit_result = await _run_audit(ids)
        _save_cached_audit(ids, audit_result)
        audit_done = True

    graph_done = False
    if req.include_graph:
        doc_ids_param = ",".join(ids)
        await get_graph_html(filter_type="Все", doc_ids=doc_ids_param)
        await get_graph_heatmap(doc_ids=doc_ids_param)
        await get_graph_html(filter_type="Все", doc_ids=None)
        await get_graph_heatmap(doc_ids=None)
        graph_done = True

    return {
        "status": "ok",
        "doc_ids_count": len(ids),
        "analyze_cached": analyze_count,
        "audit_cached": audit_done,
        "graph_cached": graph_done,
        "elapsed_sec": round(time.time() - start, 2),
    }