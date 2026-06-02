from __future__ import annotations

import re
from typing import Protocol

from src.evidence.models import LegalDocumentVersion, SemanticChunk


class CanonicalEvidenceStore(Protocol):
    def get_document_version(self, version_id: str) -> LegalDocumentVersion | None:
        ...

    def list_chunks_for_version(self, document_version_id: str) -> list[SemanticChunk]:
        ...


class InMemoryCanonicalRetrievalIndex:
    """Deterministic retrieval adapter over canonical evidence chunks."""

    def __init__(self, repository: CanonicalEvidenceStore):
        self.repository = repository

    def search(self, query: str, *, top_k: int = 10, doc_ids: list[str] | None = None) -> list[SemanticChunk]:
        query_tokens = _tokens(query)
        if not query_tokens:
            raise ValueError("query is required")

        scored: list[tuple[int, str, SemanticChunk]] = []
        for chunk in self._all_chunks_for_doc_ids(doc_ids):
            score = _score(query_tokens, _tokens(chunk.text))
            if score > 0:
                scored.append((-score, chunk.id, chunk))

        scored.sort(key=lambda item: (item[0], item[1]))
        return [chunk for _, _, chunk in scored[:top_k]]

    def _all_chunks_for_doc_ids(self, doc_ids: list[str] | None) -> list[SemanticChunk]:
        chunks: list[SemanticChunk] = []
        version_ids = _repository_version_ids(self.repository)
        for version_id in version_ids:
            version = self.repository.get_document_version(version_id)
            if version is None:
                continue
            if doc_ids and version.document_id not in doc_ids:
                continue
            chunks.extend(self.repository.list_chunks_for_version(version.id))
        return chunks


def _repository_version_ids(repository: CanonicalEvidenceStore) -> list[str]:
    versions = getattr(repository, "_versions", {})
    if isinstance(versions, dict):
        return sorted(str(version_id) for version_id in versions.keys())
    raise TypeError("repository must expose canonical document versions for in-memory retrieval")


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\wА-Яа-яӘәҒғҚқҢңӨөҰұҮүҺһІі]+", text.lower(), re.UNICODE))


def _score(query_tokens: set[str], chunk_tokens: set[str]) -> int:
    return len(query_tokens.intersection(chunk_tokens))
