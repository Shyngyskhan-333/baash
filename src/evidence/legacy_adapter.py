from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from src.evidence.models import (
    Article,
    Citation,
    LegalDocument,
    LegalDocumentStatus,
    LegalDocumentVersion,
    SemanticChunk,
    Source,
    SourceSnapshot,
    SourceType,
    compute_sha256,
    make_stable_id,
    normalize_text,
)

ADILET_SOURCE_ID = "adilet"
LEGACY_PARSER_VERSION = "legacy-json-v1"
LEGACY_CHUNK_STRATEGY = "legacy_article_chunks"
PARSE_QUALITY_FULL_TEXT = "full_text"
PARSE_QUALITY_METADATA_ONLY = "metadata_only"


@dataclass(frozen=True, slots=True)
class LegacyEvidenceImport:
    source: Source
    snapshot: SourceSnapshot
    document: LegalDocument
    version: LegalDocumentVersion
    articles: tuple[Article, ...]
    citations: tuple[Citation, ...]
    chunks: tuple[SemanticChunk, ...]
    raw_payload: str
    parse_quality: str
    legal_text_available: bool


def import_legacy_parsed_dir(parsed_dir: str | Path = "data/parsed") -> list[LegacyEvidenceImport]:
    root = Path(parsed_dir)
    if not root.exists():
        return []

    imports: list[LegacyEvidenceImport] = []
    for file_path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            imports.append(import_legacy_document(payload, raw_content_uri=str(file_path)))
        except (OSError, TypeError, json.JSONDecodeError, ValueError):
            continue
    return imports


def import_legacy_document(
    payload: Mapping[str, Any],
    *,
    raw_content_uri: str,
    source_id: str = ADILET_SOURCE_ID,
) -> LegacyEvidenceImport:
    doc_id = _required_text(payload, "doc_id")
    title = _text(payload.get("title")) or doc_id
    source_url = _source_url(payload, doc_id)
    raw_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    full_text = _document_text(payload)
    parse_quality = _parse_quality(payload, full_text)
    if parse_quality == PARSE_QUALITY_METADATA_ONLY and full_text:
        raise ValueError("metadata_only parsed documents must not contain citable legal text")

    source = Source(
        id=source_id,
        name="Adilet",
        source_type=SourceType.OFFICIAL_PORTAL,
        jurisdiction="KZ",
        base_url="https://adilet.zan.kz",
        language=_text(payload.get("language")) or "ru",
    )
    snapshot = SourceSnapshot.from_content(
        source_id=source.id,
        url=source_url,
        content=raw_payload,
        raw_content_uri=raw_content_uri,
        parser_version=LEGACY_PARSER_VERSION,
        fetch_method="legacy_parsed_json",
    )
    document = LegalDocument(
        id=_document_id(doc_id),
        external_id=doc_id,
        title=title,
        jurisdiction="KZ",
        document_type=_text(payload.get("document_type")) or "legal_act",
        issuing_body=_text(payload.get("issuing_body")),
        canonical_source_id=source.id,
    )
    version = LegalDocumentVersion(
        id=_version_id(doc_id, snapshot.content_hash, full_text),
        document_id=document.id,
        source_snapshot_id=snapshot.id,
        version_label=_text(payload.get("version_label")) or "legacy-current",
        text_hash=compute_sha256(full_text),
        status=LegalDocumentStatus.UNKNOWN,
    )

    articles: list[Article] = []
    citations: list[Citation] = []
    chunks: list[SemanticChunk] = []

    for article_index, article_payload in enumerate(_articles(payload)):
        article_number = _article_number(article_payload, article_index)
        article_text = _article_text(article_payload)
        if not article_text:
            continue

        article_id = make_stable_id("article", version.id, article_number, article_text)
        article = Article.from_text(
            id=article_id,
            document_version_id=version.id,
            number=article_number,
            title=_text(article_payload.get("title")),
            text=article_text,
            order=article_index,
        )
        articles.append(article)

        for chunk_index, chunk_payload in enumerate(_chunks(article_payload, article_text)):
            chunk_text = normalize_text(_text(chunk_payload.get("text")) or "")
            if not chunk_text:
                continue

            legacy_chunk_id = _text(chunk_payload.get("chunk_id")) or f"{doc_id}_{article_index}_{chunk_index}"
            chunk_id = make_stable_id("chunk", version.id, legacy_chunk_id, chunk_text)
            start_offset = article.text.find(chunk_text)
            start_offset = start_offset if start_offset >= 0 else None
            end_offset = start_offset + len(chunk_text) if start_offset is not None else None
            citation_id = citation_id_for_legacy_chunk(
                doc_id=doc_id,
                document_version_id=version.id,
                article_number=article.number,
                chunk_id=legacy_chunk_id,
                text=chunk_text,
            )
            citation = Citation(
                id=citation_id,
                document_version_id=version.id,
                article_id=article.id,
                chunk_id=chunk_id,
                quote=chunk_text,
                citation_label=citation_label(title, article.number),
                start_offset=start_offset,
                end_offset=end_offset,
            )
            chunk = SemanticChunk.from_text(
                id=chunk_id,
                document_version_id=version.id,
                text=chunk_text,
                citation_id=citation.id,
                article_id=article.id,
                start_offset=start_offset,
                end_offset=end_offset,
                strategy=LEGACY_CHUNK_STRATEGY,
                strategy_version="1",
            )
            citations.append(citation)
            chunks.append(chunk)

    return LegacyEvidenceImport(
        source=source,
        snapshot=snapshot,
        document=document,
        version=version,
        articles=tuple(articles),
        citations=tuple(citations),
        chunks=tuple(chunks),
        raw_payload=raw_payload,
        parse_quality=parse_quality,
        legal_text_available=bool(citations),
    )


def citation_fields_for_legacy_result(result: Mapping[str, Any]) -> dict[str, str]:
    doc_id = _text(result.get("doc_id")) or "unknown"
    title = _text(result.get("doc_title")) or _text(result.get("title")) or doc_id
    article_number = _text(result.get("article_number")) or "document"
    chunk_id = _text(result.get("chunk_id")) or make_stable_id("legacy_chunk", doc_id, result.get("text", ""))
    text = normalize_text(_text(result.get("text")) or "")
    document_version_id = _legacy_result_version_id(doc_id)
    return {
        "document_version_id": document_version_id,
        "citation_id": citation_id_for_legacy_chunk(
            doc_id=doc_id,
            document_version_id=document_version_id,
            article_number=article_number,
            chunk_id=chunk_id,
            text=text,
        ),
        "citation_label": citation_label(title, article_number),
        "citation_quote": text,
    }


def citation_id_for_legacy_chunk(
    *,
    doc_id: str,
    document_version_id: str,
    article_number: str,
    chunk_id: str,
    text: str,
) -> str:
    return make_stable_id("citation", doc_id, document_version_id, article_number, chunk_id, normalize_text(text))


def citation_label(title: str, article_number: str) -> str:
    article = article_number.strip() if article_number else "document"
    return f"{title}, {article}"


def _legacy_result_version_id(doc_id: str) -> str:
    return make_stable_id("version", doc_id, "legacy-search-result")


def _document_id(doc_id: str) -> str:
    return f"doc_{_safe_token(doc_id)}"


def _version_id(doc_id: str, snapshot_hash: str, text: str) -> str:
    return make_stable_id("version", doc_id, snapshot_hash, compute_sha256(text))


def _source_url(payload: Mapping[str, Any], doc_id: str) -> str:
    return _text(payload.get("source_url")) or _text(payload.get("url")) or f"https://adilet.zan.kz/rus/docs/{doc_id}"


def _document_text(payload: Mapping[str, Any]) -> str:
    explicit_text = normalize_text(_text(payload.get("text")) or "")
    if explicit_text:
        return explicit_text
    return normalize_text("\n\n".join(_article_text(article) for article in _articles(payload)))


def _parse_quality(payload: Mapping[str, Any], full_text: str) -> str:
    value = _text(payload.get("parse_quality"))
    if value == PARSE_QUALITY_METADATA_ONLY:
        return PARSE_QUALITY_METADATA_ONLY
    if value:
        return value
    return PARSE_QUALITY_FULL_TEXT if full_text else PARSE_QUALITY_METADATA_ONLY


def _articles(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    articles = payload.get("articles")
    if not isinstance(articles, list):
        return []
    return [article for article in articles if isinstance(article, Mapping)]


def _article_number(article: Mapping[str, Any], article_index: int) -> str:
    return (
        _text(article.get("article_number"))
        or _text(article.get("number"))
        or _text(article.get("title"))
        or f"article_{article_index + 1}"
    )


def _article_text(article: Mapping[str, Any]) -> str:
    explicit_text = normalize_text(_text(article.get("text")) or "")
    if explicit_text:
        return explicit_text
    chunk_texts = [_text(chunk.get("text")) for chunk in _chunks(article, "")]
    return normalize_text("\n".join(text for text in chunk_texts if text))


def _chunks(article: Mapping[str, Any], fallback_text: str) -> list[Mapping[str, Any]]:
    chunks = article.get("chunks")
    if isinstance(chunks, list) and chunks:
        return [chunk for chunk in chunks if isinstance(chunk, Mapping)]
    if normalize_text(fallback_text):
        return [{"text": fallback_text}]
    return []


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = _text(payload.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or make_stable_id("id", value)
