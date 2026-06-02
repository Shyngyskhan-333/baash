from __future__ import annotations

from typing import Any, Protocol

from src.evidence.legacy_adapter import citation_fields_for_legacy_result


class HybridRetriever(Protocol):
    def search_hybrid(self, query: str, top_k: int = 10, doc_ids: list[str] | None = None) -> list[dict[str, Any]]:
        ...


class SearchService:
    """Stable search boundary that enriches legacy retriever results with evidence IDs."""

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        doc_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        results = self.retriever.search_hybrid(
            query,
            top_k=80 if (filters or doc_ids) else top_k,
            doc_ids=doc_ids,
        )
        if filters and "doc_id" in filters:
            results = [result for result in results if result.get("doc_id") == filters["doc_id"]]

        enriched = [self._with_citation_fields(result) for result in results[:top_k]]
        return {"results": enriched}

    def _with_citation_fields(self, result: dict[str, Any]) -> dict[str, Any]:
        enriched = result.copy()
        enriched.update(citation_fields_for_legacy_result(result))
        return enriched
