from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RegulatoryAlertStatus(str, Enum):
    CANDIDATE = "candidate"
    UNDER_REVIEW = "under_review"
    DISMISSED = "dismissed"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class OrganizationProfile:
    id: str
    organization_id: str
    name: str
    sector_ids: tuple[str, ...]
    watched_source_ids: tuple[str, ...]
    watched_document_ids: tuple[str, ...]
    created_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.organization_id, "organization_id")
        _require(self.name, "name")
        _require_tuple(self.sector_ids, "sector_ids")
        _require_tuple(self.watched_source_ids, "watched_source_ids")
        _require_tuple(self.watched_document_ids, "watched_document_ids")
        _require(self.created_by, "created_by")


@dataclass(frozen=True, slots=True)
class ObligationCandidate:
    id: str
    organization_id: str
    title: str
    description: str
    affected_sector_ids: tuple[str, ...]
    evidence_packet_id: str
    citation_ids: tuple[str, ...]
    status: str = "candidate"
    validation_status: str = "not_human_validated"
    model_run_id: str | None = None

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.organization_id, "organization_id")
        _require(self.title, "title")
        _require(self.description, "description")
        _require_tuple(self.affected_sector_ids, "affected_sector_ids")
        _require(self.evidence_packet_id, "evidence_packet_id")
        _require_tuple(self.citation_ids, "citation_ids")
        if self.status != "candidate":
            raise ValueError("obligation candidate status must remain candidate until human review")
        if self.validation_status != "not_human_validated":
            raise ValueError("obligation candidate cannot be marked validated without review workflow")


@dataclass(frozen=True, slots=True)
class RegulatoryAlert:
    id: str
    organization_id: str
    title: str
    change_document_version_id: str
    evidence_packet_id: str
    citation_ids: tuple[str, ...]
    status: RegulatoryAlertStatus = RegulatoryAlertStatus.CANDIDATE
    obligation_candidate_ids: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.organization_id, "organization_id")
        _require(self.title, "title")
        _require(self.change_document_version_id, "change_document_version_id")
        _require(self.evidence_packet_id, "evidence_packet_id")
        _require_tuple(self.citation_ids, "citation_ids")


def _require(value: str | None, field_name: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _require_tuple(values: tuple[str, ...], field_name: str) -> None:
    if not values:
        raise ValueError(f"{field_name} must contain at least one item")
    for value in values:
        _require(value, field_name)
