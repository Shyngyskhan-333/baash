from __future__ import annotations

from typing import Protocol

from src.evidence.models import (
    Article,
    Citation,
    Clause,
    EvidencePacket,
    LegalDocument,
    LegalDocumentVersion,
    ModelRun,
    SemanticChunk,
    Source,
    SourceSnapshot,
)


class SourceRepository(Protocol):
    def get_source(self, source_id: str) -> Source | None:
        ...

    def get_snapshot(self, snapshot_id: str) -> SourceSnapshot | None:
        ...

    def add_snapshot(self, snapshot: SourceSnapshot) -> None:
        ...


class LegalDocumentRepository(Protocol):
    def get_document(self, document_id: str) -> LegalDocument | None:
        ...

    def get_document_version(self, version_id: str) -> LegalDocumentVersion | None:
        ...

    def list_articles(self, document_version_id: str) -> list[Article]:
        ...

    def list_clauses(self, article_id: str) -> list[Clause]:
        ...


class CitationRepository(Protocol):
    def get_citation(self, citation_id: str) -> Citation | None:
        ...

    def list_citations_for_version(self, document_version_id: str) -> list[Citation]:
        ...


class RetrievalIndex(Protocol):
    def search(self, query: str, *, top_k: int = 10, doc_ids: list[str] | None = None) -> list[SemanticChunk]:
        ...


class EvidencePacketRepository(Protocol):
    def get_packet(self, packet_id: str) -> EvidencePacket | None:
        ...

    def add_packet(self, packet: EvidencePacket) -> None:
        ...


class ModelRunRepository(Protocol):
    def add_model_run(self, model_run: ModelRun) -> None:
        ...
