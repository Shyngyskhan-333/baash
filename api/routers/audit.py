from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio
import concurrent.futures

from src.reasoning.detector import detect_all_problems
from src.retrieval.retriever import LegalRetriever
from src.graph.knowledge_graph import LegalKnowledgeGraph

router = APIRouter()


def _run_audit_sync() -> dict:
    """Runs the full O(N²) NLI audit. Must be called from a thread pool."""
    retriever = LegalRetriever()
    graph = LegalKnowledgeGraph()
    problems = detect_all_problems(retriever, top_k_explain=5)
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


@router.post("/api/v1/audit/detect")
async def run_global_audit():
    """
    Runs the full NLI collision audit in a background thread so it doesn't
    block the FastAPI async event loop.
    """
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(pool, _run_audit_sync)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
