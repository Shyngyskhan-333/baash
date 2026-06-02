from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum

from src.evidence.models import AuditLog, make_stable_id


class ReviewStatus(str, Enum):
    CANDIDATE = "candidate"
    UNDER_REVIEW = "under_review"
    VALIDATED = "validated"
    REJECTED = "rejected"
    NEEDS_EVIDENCE = "needs_evidence"
    SUPERSEDED = "superseded"


class ReviewDecision(str, Enum):
    START_REVIEW = "start_review"
    VALIDATE = "validate"
    REJECT = "reject"
    REQUEST_EVIDENCE = "request_evidence"
    SUPERSEDE = "supersede"


@dataclass(frozen=True, slots=True)
class ReviewTask:
    id: str
    title: str
    issue_type: str
    evidence_packet_id: str
    citation_ids: tuple[str, ...]
    status: ReviewStatus
    validation_status: str
    created_by: str
    created_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.title, "title")
        _require(self.issue_type, "issue_type")
        _require(self.evidence_packet_id, "evidence_packet_id")
        _require(self.created_by, "created_by")
        if not self.citation_ids:
            raise ValueError("citation_ids must contain at least one citation")
        for citation_id in self.citation_ids:
            _require(citation_id, "citation_id")


class ReviewWorkflowService:
    def create_task(
        self,
        *,
        title: str,
        issue_type: str,
        evidence_packet_id: str,
        citation_ids: tuple[str, ...],
        created_by: str,
    ) -> ReviewTask:
        unique_citations = _dedupe(citation_ids)
        task_id = make_stable_id("review_task", title, issue_type, evidence_packet_id, "|".join(unique_citations))
        return ReviewTask(
            id=task_id,
            title=title,
            issue_type=issue_type,
            evidence_packet_id=evidence_packet_id,
            citation_ids=unique_citations,
            status=ReviewStatus.CANDIDATE,
            validation_status="not_human_validated",
            created_by=created_by,
            created_at=_utc_now(),
        )

    def transition(
        self,
        task: ReviewTask,
        *,
        decision: ReviewDecision,
        actor_id: str,
        note: str,
    ) -> tuple[ReviewTask, AuditLog]:
        actor_id = _require(actor_id, "actor_id")
        note = _require(note, "note")
        new_status = self._next_status(task.status, decision)
        validation_status = _validation_status_for(new_status)
        now = _utc_now()
        updated = replace(
            task,
            status=new_status,
            validation_status=validation_status,
            reviewed_by=actor_id,
            reviewed_at=now,
            note=note,
        )
        audit = AuditLog(
            id=make_stable_id("audit", task.id, decision.value, actor_id, now.isoformat()),
            actor_id=actor_id,
            action=f"review_task.{new_status.value}",
            target_type="ReviewTask",
            target_id=task.id,
            timestamp=now,
            reason=note,
        )
        return updated, audit

    def _next_status(self, current: ReviewStatus, decision: ReviewDecision) -> ReviewStatus:
        allowed = {
            ReviewStatus.CANDIDATE: {
                ReviewDecision.START_REVIEW: ReviewStatus.UNDER_REVIEW,
                ReviewDecision.SUPERSEDE: ReviewStatus.SUPERSEDED,
            },
            ReviewStatus.UNDER_REVIEW: {
                ReviewDecision.VALIDATE: ReviewStatus.VALIDATED,
                ReviewDecision.REJECT: ReviewStatus.REJECTED,
                ReviewDecision.REQUEST_EVIDENCE: ReviewStatus.NEEDS_EVIDENCE,
                ReviewDecision.SUPERSEDE: ReviewStatus.SUPERSEDED,
            },
            ReviewStatus.NEEDS_EVIDENCE: {
                ReviewDecision.START_REVIEW: ReviewStatus.UNDER_REVIEW,
                ReviewDecision.SUPERSEDE: ReviewStatus.SUPERSEDED,
            },
        }
        next_status = allowed.get(current, {}).get(decision)
        if next_status is None:
            raise ValueError(f"cannot apply decision {decision.value} from status {current.value}")
        return next_status


def _validation_status_for(status: ReviewStatus) -> str:
    if status == ReviewStatus.VALIDATED:
        return "human_validated"
    if status == ReviewStatus.REJECTED:
        return "human_rejected"
    return "not_human_validated"


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = _require(value, "citation_id")
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return tuple(unique)


def _require(value: str | None, field_name: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
