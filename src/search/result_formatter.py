from __future__ import annotations

from typing import Any, Protocol

from src.evidence.models import Article, Citation, LegalDocument, LegalDocumentVersion, SemanticChunk


class CanonicalResultStore(Protocol):
    def get_citation(self, citation_id: str) -> Citation | None:
        ...

    def get_document_version(self, version_id: str) -> LegalDocumentVersion | None:
        ...

    def get_document(self, document_id: str) -> LegalDocument | None:
        ...

    def list_articles(self, document_version_id: str) -> list[Article]:
        ...


class CanonicalSearchResultFormatter:
    """Formats canonical chunks as citation-aware search result dictionaries."""

    def __init__(self, repository: CanonicalResultStore):
        self.repository = repository

    def format_chunks(
        self,
        chunks: tuple[SemanticChunk, ...] | list[SemanticChunk],
        *,
        scores: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        return [self.format_chunk(chunk, score=(scores or {}).get(chunk.id)) for chunk in chunks]

    def format_chunk(self, chunk: SemanticChunk, *, score: float | None = None) -> dict[str, Any]:
        citation = self._require_citation(chunk.citation_id)
        version = self._require_version(chunk.document_version_id)
        document = self._require_document(version.document_id)
        article = self._article_for_chunk(chunk, version.id)
        result: dict[str, Any] = {
            "doc_id": document.external_id,
            "document_id": document.id,
            "document_version_id": version.id,
            "source_snapshot_id": version.source_snapshot_id,
            "doc_title": document.title,
            "article_number": article.number if article else "",
            "article_id": chunk.article_id,
            "clause_id": chunk.clause_id,
            "chunk_id": chunk.id,
            "text": chunk.text,
            "citation_id": citation.id,
            "citation_label": citation.citation_label,
            "citation_quote": citation.quote,
        }
        if score is not None:
            result["score"] = score
        return result

    def _require_citation(self, citation_id: str) -> Citation:
        citation = self.repository.get_citation(citation_id)
        if citation is None:
            raise ValueError(f"citation {citation_id} was not found")
        return citation

    def _require_version(self, version_id: str) -> LegalDocumentVersion:
        version = self.repository.get_document_version(version_id)
        if version is None:
            raise ValueError(f"document version {version_id} was not found")
        return version

    def _require_document(self, document_id: str) -> LegalDocument:
        document = self.repository.get_document(document_id)
        if document is None:
            raise ValueError(f"document {document_id} was not found")
        return document

    def _article_for_chunk(self, chunk: SemanticChunk, document_version_id: str) -> Article | None:
        if not chunk.article_id:
            return None
        for article in self.repository.list_articles(document_version_id):
            if article.id == chunk.article_id:
                return article
        return None
