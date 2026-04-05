from fastapi import APIRouter, HTTPException

from api.models.schemas import SearchRequest, SearchResponse, SearchResult
from api.services.nlp_service import nlp_service

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):

    q = (request.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Пустой поисковый запрос")
    print(f"[SEARCH] Query: '{q[:50]}...'. Scope: {request.doc_ids}")
    try:
        data = nlp_service.search(
            query=q,
            top_k=request.top_k,
            filters=request.filters,
            doc_ids=request.doc_ids
        )

        results = []
        for r in data["results"]:
            text = r.get("text", "")
            results.append(SearchResult(
                doc_id=r.get("doc_id", ""),
                title=r.get("doc_title", ""),
                excerpt=text[:300] + ("..." if len(text) > 300 else ""),
                text=text,
                score=r.get("rrf_score", 0.0) or r.get("cosine_score", 0.0),
                bm25_score=r.get("bm25_score", 0.0),
                cosine_score=r.get("cosine_score", 0.0),
                risk_level="low",
            ))

        return SearchResponse(
            results=results,
            query_vector=data.get("query_vector", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))