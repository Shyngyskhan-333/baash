from fastapi import APIRouter, HTTPException

from api.models.schemas import SearchRequest, SearchResponse, SearchResult
from api.services.nlp_service import nlp_service

router = APIRouter()


@router.post("/api/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Гибридный BM25 + семантический поиск по базе НПА."""
    try:
        data = nlp_service.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters
        )

        results = []
        for r in data["results"]:
            text = r.get("text", "")
            results.append(SearchResult(
                doc_id=r.get("doc_id", ""),
                title=r.get("doc_title", ""),
                excerpt=text[:300] + ("..." if len(text) > 300 else ""),
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
