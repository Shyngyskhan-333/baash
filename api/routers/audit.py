from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
import asyncio
import concurrent.futures
from pydantic import BaseModel

from src.reasoning.detector import detect_all_problems
from src.retrieval.retriever import LegalRetriever
from src.graph.knowledge_graph import LegalKnowledgeGraph

router = APIRouter()

class AuditRequest(BaseModel):
    doc_ids: Optional[List[str]] = None

async def _run_audit(doc_ids: Optional[List[str]] = None) -> dict:
    """Runs the full O(N²) NLI audit. Filters by doc_ids if provided."""
    print(f"[AUDIT] Starting async audit with scope: {doc_ids}")
    retriever = LegalRetriever()
    graph = LegalKnowledgeGraph()
    # detect_all_problems is now async
    problems = await detect_all_problems(retriever, top_k_explain=5, doc_ids=doc_ids)
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
async def run_global_audit(req: AuditRequest = AuditRequest()):
    print(f"[AUDIT] Received global audit request. Scope: {req.doc_ids}")
    try:
        # Directly await the async audit function
        return await _run_audit(req.doc_ids)
    except Exception as e:
        print(f"[AUDIT] Error during audit: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
