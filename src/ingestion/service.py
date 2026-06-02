from __future__ import annotations

from dataclasses import dataclass

from src.evidence.models import Article, Citation, Clause, LegalDocument, LegalDocumentVersion, SemanticChunk, SourceSnapshot
from src.ingestion.chunk_builder import CitationChunkBuilder
from src.ingestion.citation_builder import ParsedCitationBuilder
from src.ingestion.document_builder import ParsedDocumentVersionBuilder
from src.ingestion.parser import ParsedSourceDocument, SourceParser
from src.ingestion.snapshot import FetchedSourceContent, SourceSnapshotBuilder


@dataclass(frozen=True, slots=True)
class EvidenceIngestionBundle:
    snapshot: SourceSnapshot
    parsed: ParsedSourceDocument
    document: LegalDocument
    version: LegalDocumentVersion
    articles: tuple[Article, ...]
    clauses: tuple[Clause, ...]
    citations: tuple[Citation, ...]
    chunks: tuple[SemanticChunk, ...]


class EvidenceIngestionService:
    """Composes ingestion boundaries into a citable evidence bundle without persistence."""

    def __init__(
        self,
        *,
        snapshot_builder: SourceSnapshotBuilder | None = None,
        parser: SourceParser | None = None,
        document_builder: ParsedDocumentVersionBuilder | None = None,
        citation_builder: ParsedCitationBuilder | None = None,
        chunk_builder: CitationChunkBuilder | None = None,
    ) -> None:
        self.snapshot_builder = snapshot_builder or SourceSnapshotBuilder()
        self.parser = parser or SourceParser()
        self.document_builder = document_builder or ParsedDocumentVersionBuilder()
        self.citation_builder = citation_builder or ParsedCitationBuilder()
        self.chunk_builder = chunk_builder or CitationChunkBuilder()

    def ingest_fetched(self, fetched: FetchedSourceContent) -> EvidenceIngestionBundle:
        snapshot = self.snapshot_builder.build(fetched)
        parsed = self.parser.parse(snapshot=snapshot, raw_content=fetched.content)
        document_bundle = self.document_builder.build(parsed=parsed, snapshot=snapshot)
        citation_bundle = self.citation_builder.build(
            parsed=parsed,
            document_version_id=document_bundle.version.id,
            citation_title=document_bundle.document.title,
        )
        chunks = self.chunk_builder.build(citations=citation_bundle.citations)
        return EvidenceIngestionBundle(
            snapshot=snapshot,
            parsed=parsed,
            document=document_bundle.document,
            version=document_bundle.version,
            articles=citation_bundle.articles,
            clauses=citation_bundle.clauses,
            citations=citation_bundle.citations,
            chunks=chunks,
        )
