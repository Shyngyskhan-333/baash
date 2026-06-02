from __future__ import annotations

import re
from dataclasses import dataclass

from src.evidence.models import (
    LegalDocument,
    LegalDocumentStatus,
    LegalDocumentVersion,
    SourceSnapshot,
    compute_sha256,
    make_stable_id,
    normalize_text,
)
from src.ingestion.parser import ParsedSourceDocument


@dataclass(frozen=True, slots=True)
class ParsedDocumentVersionBundle:
    document: LegalDocument
    version: LegalDocumentVersion


class ParsedDocumentVersionBuilder:
    """Builds canonical document identity and legal text version from parsed source text."""

    def build(
        self,
        *,
        parsed: ParsedSourceDocument,
        snapshot: SourceSnapshot,
        jurisdiction: str = "KZ",
        document_type: str = "legal_act",
        status: LegalDocumentStatus = LegalDocumentStatus.UNKNOWN,
    ) -> ParsedDocumentVersionBundle:
        if parsed.source_snapshot_id != snapshot.id:
            raise ValueError("parsed document does not belong to source snapshot")
        text = _parsed_legal_text(parsed)
        if not text:
            raise ValueError("parsed document does not contain legal text for versioning")

        document = LegalDocument(
            id=f"doc_{_safe_token(parsed.doc_id)}",
            external_id=parsed.doc_id,
            title=parsed.title,
            jurisdiction=jurisdiction,
            document_type=document_type,
            canonical_source_id=snapshot.source_id,
        )
        version = LegalDocumentVersion(
            id=make_stable_id("version", parsed.doc_id, snapshot.content_hash, compute_sha256(text)),
            document_id=document.id,
            source_snapshot_id=snapshot.id,
            version_label=parsed.parser_version,
            text_hash=compute_sha256(text),
            status=status,
        )
        return ParsedDocumentVersionBundle(document=document, version=version)


def _parsed_legal_text(parsed: ParsedSourceDocument) -> str:
    if not parsed.legal_text_available:
        return ""
    return normalize_text("\n\n".join(str(article.get("text") or "") for article in parsed.articles))


def _safe_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or make_stable_id("id", value)
