from __future__ import annotations

from typing import Any, Protocol

from src.evidence.models import SemanticChunk
from src.search.canonical_retrieval import InMemoryCanonicalRetrievalIndex
from src.search.result_formatter import CanonicalSearchResultFormatter


class CanonicalRetrievalIndex(Protocol):
    def search(self, query: str, *, top_k: int = 10, doc_ids: list[str] | None = None) -> list[SemanticChunk]:
        ...


class CanonicalSearchService:
    """Composes canonical retrieval and result formatting without touching legacy routes."""

    def __init__(
        self,
        *,
        retrieval_index: CanonicalRetrievalIndex,
        formatter: CanonicalSearchResultFormatter,
    ) -> None:
        self.retrieval_index = retrieval_index
        self.formatter = formatter

    @classmethod
    def from_repository(cls, repository: Any) -> CanonicalSearchService:
        return cls(
            retrieval_index=InMemoryCanonicalRetrievalIndex(repository),
            formatter=CanonicalSearchResultFormatter(repository),
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        doc_ids: list[str] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        chunks = self.retrieval_index.search(query, top_k=top_k, doc_ids=doc_ids)
        return {"results": self.formatter.format_chunks(chunks)}
