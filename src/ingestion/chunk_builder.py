from __future__ import annotations

from src.evidence.models import Citation, SemanticChunk, make_stable_id

CHUNK_STRATEGY_CITATION_CLAUSE = "citation_clause_chunks"
CHUNK_STRATEGY_VERSION = "1"


class CitationChunkBuilder:
    """Builds retrieval chunks from canonical citations without indexing them."""

    def build(self, *, citations: tuple[Citation, ...]) -> tuple[SemanticChunk, ...]:
        if not citations:
            raise ValueError("citations must contain at least one citation")

        chunks: list[SemanticChunk] = []
        for citation in citations:
            chunk_id = make_stable_id("chunk", citation.document_version_id, citation.id, citation.quote)
            chunks.append(
                SemanticChunk.from_text(
                    id=chunk_id,
                    document_version_id=citation.document_version_id,
                    text=citation.quote,
                    citation_id=citation.id,
                    article_id=citation.article_id,
                    clause_id=citation.clause_id,
                    start_offset=citation.start_offset,
                    end_offset=citation.end_offset,
                    strategy=CHUNK_STRATEGY_CITATION_CLAUSE,
                    strategy_version=CHUNK_STRATEGY_VERSION,
                )
            )
        return tuple(chunks)
