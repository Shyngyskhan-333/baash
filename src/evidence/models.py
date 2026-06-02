from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


def _require(value: str | None, field_name: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _require_hash(value: str, field_name: str) -> str:
    normalized = _require(value, field_name).lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    return normalized


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


def compute_sha256(content: str | bytes) -> str:
    data = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


def make_stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}_{compute_sha256(raw)[:16]}"


class SourceType(str, Enum):
    OFFICIAL_PORTAL = "official_portal"
    GOVERNMENT_UPLOAD = "government_upload"
    ORGANIZATION_UPLOAD = "organization_upload"
    INTERNAL_FIXTURE = "internal_fixture"


class LegalDocumentStatus(str, Enum):
    ACTIVE = "active"
    HISTORICAL = "historical"
    REPEALED = "repealed"
    UNKNOWN = "unknown"


class EvidencePacketStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class ModelRunStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    name: str
    source_type: SourceType
    jurisdiction: str
    base_url: str | None = None
    authority_level: str = "official"
    language: str = "ru"

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.name, "name")
        _require(self.jurisdiction, "jurisdiction")


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    id: str
    source_id: str
    url: str
    fetched_at: datetime
    content_hash: str
    raw_content_uri: str
    http_status: int | None = None
    parser_version: str | None = None
    fetch_method: str = "http"

    @classmethod
    def from_content(
        cls,
        *,
        source_id: str,
        url: str,
        content: str | bytes,
        raw_content_uri: str,
        fetched_at: datetime | None = None,
        http_status: int | None = None,
        parser_version: str | None = None,
        fetch_method: str = "http",
    ) -> SourceSnapshot:
        content_hash = compute_sha256(content)
        return cls(
            id=make_stable_id("snapshot", source_id, url, content_hash),
            source_id=source_id,
            url=url,
            fetched_at=fetched_at or _utc_now(),
            content_hash=content_hash,
            raw_content_uri=raw_content_uri,
            http_status=http_status,
            parser_version=parser_version,
            fetch_method=fetch_method,
        )

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.source_id, "source_id")
        _require(self.url, "url")
        _require_hash(self.content_hash, "content_hash")
        _require(self.raw_content_uri, "raw_content_uri")


@dataclass(frozen=True, slots=True)
class LegalDocument:
    id: str
    external_id: str
    title: str
    jurisdiction: str
    document_type: str
    issuing_body: str | None = None
    canonical_source_id: str | None = None

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.external_id, "external_id")
        _require(self.title, "title")
        _require(self.jurisdiction, "jurisdiction")
        _require(self.document_type, "document_type")


@dataclass(frozen=True, slots=True)
class LegalDocumentVersion:
    id: str
    document_id: str
    source_snapshot_id: str
    version_label: str
    text_hash: str
    status: LegalDocumentStatus = LegalDocumentStatus.UNKNOWN
    published_at: datetime | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.document_id, "document_id")
        _require(self.source_snapshot_id, "source_snapshot_id")
        _require(self.version_label, "version_label")
        _require_hash(self.text_hash, "text_hash")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot be earlier than effective_from")


@dataclass(frozen=True, slots=True)
class Article:
    id: str
    document_version_id: str
    number: str
    text: str
    text_hash: str
    title: str | None = None
    order: int = 0

    @classmethod
    def from_text(
        cls,
        *,
        id: str,
        document_version_id: str,
        number: str,
        text: str,
        title: str | None = None,
        order: int = 0,
    ) -> Article:
        normalized = normalize_text(text)
        return cls(
            id=id,
            document_version_id=document_version_id,
            number=number,
            text=normalized,
            text_hash=compute_sha256(normalized),
            title=title,
            order=order,
        )

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.document_version_id, "document_version_id")
        _require(self.number, "number")
        _require(self.text, "text")
        _require_hash(self.text_hash, "text_hash")


@dataclass(frozen=True, slots=True)
class Clause:
    id: str
    article_id: str
    path: str
    text: str
    text_hash: str
    number: str | None = None
    order: int = 0

    @classmethod
    def from_text(
        cls,
        *,
        id: str,
        article_id: str,
        path: str,
        text: str,
        number: str | None = None,
        order: int = 0,
    ) -> Clause:
        normalized = normalize_text(text)
        return cls(
            id=id,
            article_id=article_id,
            path=path,
            text=normalized,
            text_hash=compute_sha256(normalized),
            number=number,
            order=order,
        )

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.article_id, "article_id")
        _require(self.path, "path")
        _require(self.text, "text")
        _require_hash(self.text_hash, "text_hash")


@dataclass(frozen=True, slots=True)
class Citation:
    id: str
    document_version_id: str
    quote: str
    citation_label: str
    article_id: str | None = None
    clause_id: str | None = None
    chunk_id: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.document_version_id, "document_version_id")
        _require(self.quote, "quote")
        _require(self.citation_label, "citation_label")
        if self.start_offset is not None and self.start_offset < 0:
            raise ValueError("start_offset cannot be negative")
        if self.end_offset is not None and self.end_offset < 0:
            raise ValueError("end_offset cannot be negative")
        if self.start_offset is not None and self.end_offset is not None and self.end_offset < self.start_offset:
            raise ValueError("end_offset cannot be earlier than start_offset")


@dataclass(frozen=True, slots=True)
class SemanticChunk:
    id: str
    document_version_id: str
    text: str
    chunk_hash: str
    citation_id: str
    article_id: str | None = None
    clause_id: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    strategy: str = "legacy_article_chunks"
    strategy_version: str = "1"

    @classmethod
    def from_text(
        cls,
        *,
        id: str,
        document_version_id: str,
        text: str,
        citation_id: str,
        article_id: str | None = None,
        clause_id: str | None = None,
        start_offset: int | None = None,
        end_offset: int | None = None,
        strategy: str = "legacy_article_chunks",
        strategy_version: str = "1",
    ) -> SemanticChunk:
        normalized = normalize_text(text)
        return cls(
            id=id,
            document_version_id=document_version_id,
            text=normalized,
            chunk_hash=compute_sha256(normalized),
            citation_id=citation_id,
            article_id=article_id,
            clause_id=clause_id,
            start_offset=start_offset,
            end_offset=end_offset,
            strategy=strategy,
            strategy_version=strategy_version,
        )

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.document_version_id, "document_version_id")
        _require(self.text, "text")
        _require_hash(self.chunk_hash, "chunk_hash")
        _require(self.citation_id, "citation_id")


@dataclass(frozen=True, slots=True)
class ModelRun:
    id: str
    model_name: str
    model_version: str
    prompt_hash: str
    input_citation_ids: tuple[str, ...] = field(default_factory=tuple)
    output_hash: str | None = None
    status: ModelRunStatus = ModelRunStatus.SUCCEEDED
    started_at: datetime = field(default_factory=_utc_now)
    completed_at: datetime | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.model_name, "model_name")
        _require(self.model_version, "model_version")
        _require_hash(self.prompt_hash, "prompt_hash")
        if self.output_hash is not None:
            _require_hash(self.output_hash, "output_hash")


@dataclass(frozen=True, slots=True)
class EvidencePacket:
    id: str
    title: str
    purpose: str
    citation_ids: tuple[str, ...]
    status: EvidencePacketStatus = EvidencePacketStatus.DRAFT
    source_snapshot_ids: tuple[str, ...] = field(default_factory=tuple)
    model_run_ids: tuple[str, ...] = field(default_factory=tuple)
    review_task_ids: tuple[str, ...] = field(default_factory=tuple)
    summary: str | None = None
    generated_at: datetime = field(default_factory=_utc_now)
    packet_hash: str | None = None

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "purpose": self.purpose,
            "citation_ids": list(self.citation_ids),
            "source_snapshot_ids": list(self.source_snapshot_ids),
            "model_run_ids": list(self.model_run_ids),
            "review_task_ids": list(self.review_task_ids),
            "summary": self.summary,
            "status": self.status,
        }

    def with_computed_hash(self) -> EvidencePacket:
        payload = json.dumps(self.canonical_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return EvidencePacket(
            id=self.id,
            title=self.title,
            purpose=self.purpose,
            citation_ids=self.citation_ids,
            status=self.status,
            source_snapshot_ids=self.source_snapshot_ids,
            model_run_ids=self.model_run_ids,
            review_task_ids=self.review_task_ids,
            summary=self.summary,
            generated_at=self.generated_at,
            packet_hash=compute_sha256(payload),
        )

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.title, "title")
        _require(self.purpose, "purpose")
        if not self.citation_ids:
            raise ValueError("citation_ids must contain at least one citation")
        for citation_id in self.citation_ids:
            _require(citation_id, "citation_id")
        if self.packet_hash is not None:
            _require_hash(self.packet_hash, "packet_hash")


@dataclass(frozen=True, slots=True)
class AuditLog:
    id: str
    actor_id: str
    action: str
    target_type: str
    target_id: str
    timestamp: datetime = field(default_factory=_utc_now)
    organization_id: str | None = None
    before_hash: str | None = None
    after_hash: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.actor_id, "actor_id")
        _require(self.action, "action")
        _require(self.target_type, "target_type")
        _require(self.target_id, "target_id")
        if self.before_hash is not None:
            _require_hash(self.before_hash, "before_hash")
        if self.after_hash is not None:
            _require_hash(self.after_hash, "after_hash")
