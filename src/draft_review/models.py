from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class DraftReviewStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class DraftLawReview:
    id: str
    title: str
    draft_source_snapshot_id: str
    target_document_version_ids: tuple[str, ...]
    created_by: str
    organization_id: str
    status: DraftReviewStatus = DraftReviewStatus.DRAFT
    candidate_issue_ids: tuple[str, ...] = field(default_factory=tuple)
    review_task_ids: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.title, "title")
        _require(self.draft_source_snapshot_id, "draft_source_snapshot_id")
        _require(self.created_by, "created_by")
        _require(self.organization_id, "organization_id")
        _require_tuple(self.target_document_version_ids, "target_document_version_ids")


@dataclass(frozen=True, slots=True)
class DraftCandidateIssue:
    id: str
    draft_review_id: str
    issue_type: str
    title: str
    description: str
    evidence_packet_id: str
    citation_ids: tuple[str, ...]
    status: str = "candidate"
    validation_status: str = "not_human_validated"
    model_run_id: str | None = None

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.draft_review_id, "draft_review_id")
        _require(self.issue_type, "issue_type")
        _require(self.title, "title")
        _require(self.description, "description")
        _require(self.evidence_packet_id, "evidence_packet_id")
        _require_tuple(self.citation_ids, "citation_ids")
        if self.status != "candidate":
            raise ValueError("draft candidate issue status must remain candidate until human review")
        if self.validation_status != "not_human_validated":
            raise ValueError("draft candidate issue cannot be marked validated without review workflow")


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
