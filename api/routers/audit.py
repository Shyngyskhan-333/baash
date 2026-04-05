from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import hashlib
import json
from pathlib import Path

from src.reasoning.detector import detect_all_problems
from src.retrieval.retriever import LegalRetriever
from src.graph.knowledge_graph import LegalKnowledgeGraph
from api.services.ai_provider import ai_provider

router = APIRouter()
CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class AuditRequest(BaseModel):
    doc_ids: Optional[List[str]] = None
    force_refresh: bool = False

def _scope_cache_key(doc_ids: Optional[List[str]]) -> str:
    if not doc_ids:
        return "all_documents"
    normalized = ",".join(sorted(set(doc_ids)))
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"scope_{digest}"

def _cache_path(doc_ids: Optional[List[str]]) -> Path:
    return CACHE_DIR / f"audit_{_scope_cache_key(doc_ids)}.json"

def _load_cached_audit(doc_ids: Optional[List[str]]) -> Optional[dict]:
    path = _cache_path(doc_ids)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            payload["cached"] = True
            payload["cache_key"] = _scope_cache_key(doc_ids)
            return payload
    except Exception as e:
        print(f"[AUDIT] Failed to read cache {path}: {e}")
    return None

def _save_cached_audit(doc_ids: Optional[List[str]], data: dict) -> None:
    path = _cache_path(doc_ids)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"[AUDIT] Failed to write cache {path}: {e}")

async def _run_audit(doc_ids: Optional[List[str]] = None) -> dict:

    print(f"[AUDIT] Starting async audit with scope: {doc_ids}")
    retriever = LegalRetriever()
    graph = LegalKnowledgeGraph()

    problems = await detect_all_problems(retriever, top_k_explain=5, doc_ids=doc_ids, ai_caller=ai_provider.complete)
    graph.build_from_detector_problems(problems)

    def serialize(p):
        return {
            "type": p.type,
            "chunk_a": p.chunk_a,
            "chunk_b": p.chunk_b,
            "scores": p.scores,
            "explanation": p.explanation,
        }

    p_cont = [p for p in problems if p.type == "contradiction"]
    p_dup  = [p for p in problems if p.type == "duplicate"]
    p_out  = [p for p in problems if p.type == "outdated"]

    return {
        "status": "success",
        "stats": {
            "contradictions": len(p_cont),
            "duplicates": len(p_dup),
            "outdated": len(p_out),
        },
        "contradictions": [serialize(p) for p in p_cont],
        "duplicates":     [serialize(p) for p in p_dup],
        "outdated":       [serialize(p) for p in p_out],
    }

@router.post("/audit/detect")
async def run_global_audit(req: Optional[AuditRequest] = None):
    req = req or AuditRequest()
    print(f"[AUDIT] Received global audit request. Scope: {req.doc_ids}")
    try:
        if not req.force_refresh:
            cached = _load_cached_audit(req.doc_ids)
            if cached is not None:
                print(f"[AUDIT] Returning cached audit: {_scope_cache_key(req.doc_ids)}")
                return cached

        fresh = await _run_audit(req.doc_ids)
        _save_cached_audit(req.doc_ids, fresh)
        fresh["cached"] = False
        fresh["cache_key"] = _scope_cache_key(req.doc_ids)
        return fresh
    except Exception as e:
        print(f"[AUDIT] Error during audit: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))