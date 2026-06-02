from __future__ import annotations

from typing import Protocol, TypeVar

from src.evidence.models import (
    Article,
    Citation,
    Clause,
    LegalDocument,
    LegalDocumentVersion,
    SemanticChunk,
    Source,
    SourceSnapshot,
)


class IngestionBundleLike(Protocol):
    snapshot: SourceSnapshot
    document: LegalDocument
    version: LegalDocumentVersion
    articles: tuple[Article, ...]
    clauses: tuple[Clause, ...]
    citations: tuple[Citation, ...]
    chunks: tuple[SemanticChunk, ...]


EntityT = TypeVar("EntityT")


class InMemoryEvidenceRepository:
    """Local evidence store for tests and early wiring before a durable storage decision."""

    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}
        self._snapshots: dict[str, SourceSnapshot] = {}
        self._documents: dict[str, LegalDocument] = {}
        self._versions: dict[str, LegalDocumentVersion] = {}
        self._articles: dict[str, Article] = {}
        self._clauses: dict[str, Clause] = {}
        self._citations: dict[str, Citation] = {}
        self._chunks: dict[str, SemanticChunk] = {}

    def add_ingestion_bundle(self, bundle: IngestionBundleLike) -> None:
        self.add_snapshot(bundle.snapshot)
        self.add_document(bundle.document)
        self.add_document_version(bundle.version)
        for article in bundle.articles:
            self.add_article(article)
        for clause in bundle.clauses:
            self.add_clause(clause)
        for citation in bundle.citations:
            self.add_citation(citation)
        for chunk in bundle.chunks:
            self.add_chunk(chunk)

    def get_source(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def add_source(self, source: Source) -> None:
        _put_unique(self._sources, source.id, source, "Source")

    def get_snapshot(self, snapshot_id: str) -> SourceSnapshot | None:
        return self._snapshots.get(snapshot_id)

    def add_snapshot(self, snapshot: SourceSnapshot) -> None:
        _put_unique(self._snapshots, snapshot.id, snapshot, "SourceSnapshot")

    def get_document(self, document_id: str) -> LegalDocument | None:
        return self._documents.get(document_id)

    def add_document(self, document: LegalDocument) -> None:
        _put_unique(self._documents, document.id, document, "LegalDocument")

    def get_document_version(self, version_id: str) -> LegalDocumentVersion | None:
        return self._versions.get(version_id)

    def add_document_version(self, version: LegalDocumentVersion) -> None:
        _put_unique(self._versions, version.id, version, "LegalDocumentVersion")

    def list_articles(self, document_version_id: str) -> list[Article]:
        articles = [article for article in self._articles.values() if article.document_version_id == document_version_id]
        return sorted(articles, key=lambda article: (article.order, article.number, article.id))

    def add_article(self, article: Article) -> None:
        _put_unique(self._articles, article.id, article, "Article")

    def list_clauses(self, article_id: str) -> list[Clause]:
        clauses = [clause for clause in self._clauses.values() if clause.article_id == article_id]
        return sorted(clauses, key=lambda clause: (clause.order, clause.path, clause.id))

    def add_clause(self, clause: Clause) -> None:
        _put_unique(self._clauses, clause.id, clause, "Clause")

    def get_citation(self, citation_id: str) -> Citation | None:
        return self._citations.get(citation_id)

    def list_citations_for_version(self, document_version_id: str) -> list[Citation]:
        citations = [
            citation for citation in self._citations.values() if citation.document_version_id == document_version_id
        ]
        return sorted(citations, key=lambda citation: (citation.start_offset is None, citation.start_offset or 0, citation.id))

    def add_citation(self, citation: Citation) -> None:
        _put_unique(self._citations, citation.id, citation, "Citation")

    def list_chunks_for_version(self, document_version_id: str) -> list[SemanticChunk]:
        chunks = [chunk for chunk in self._chunks.values() if chunk.document_version_id == document_version_id]
        return sorted(chunks, key=lambda chunk: (chunk.start_offset is None, chunk.start_offset or 0, chunk.id))

    def add_chunk(self, chunk: SemanticChunk) -> None:
        _put_unique(self._chunks, chunk.id, chunk, "SemanticChunk")


def _put_unique(store: dict[str, EntityT], entity_id: str, entity: EntityT, entity_name: str) -> None:
    existing = store.get(entity_id)
    if existing is not None and existing != entity:
        raise ValueError(f"{entity_name} with id {entity_id} already exists with different content")
    store[entity_id] = entity
