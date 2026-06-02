from __future__ import annotations

from dataclasses import replace

from src.draft_review.models import DraftCandidateIssue, DraftLawReview
from src.evidence.models import make_stable_id
from src.evidence.review_workflow import ReviewTask, ReviewWorkflowService


class DraftReviewService:
    def __init__(self, review_workflow: ReviewWorkflowService | None = None):
        self.review_workflow = review_workflow or ReviewWorkflowService()

    def create_review(
        self,
        *,
        title: str,
        draft_source_snapshot_id: str,
        target_document_version_ids: tuple[str, ...],
        created_by: str,
        organization_id: str,
    ) -> DraftLawReview:
        review_id = make_stable_id(
            "draft_review",
            title,
            draft_source_snapshot_id,
            "|".join(target_document_version_ids),
            organization_id,
        )
        return DraftLawReview(
            id=review_id,
            title=title,
            draft_source_snapshot_id=draft_source_snapshot_id,
            target_document_version_ids=_dedupe(target_document_version_ids),
            created_by=created_by,
            organization_id=organization_id,
        )

    def add_candidate_issue(
        self,
        review: DraftLawReview,
        *,
        issue_type: str,
        title: str,
        description: str,
        evidence_packet_id: str,
        citation_ids: tuple[str, ...],
        model_run_id: str | None = None,
    ) -> tuple[DraftLawReview, DraftCandidateIssue]:
        unique_citations = _dedupe(citation_ids)
        candidate = DraftCandidateIssue(
            id=make_stable_id("draft_candidate", review.id, issue_type, title, evidence_packet_id),
            draft_review_id=review.id,
            issue_type=issue_type,
            title=title,
            description=description,
            evidence_packet_id=evidence_packet_id,
            citation_ids=unique_citations,
            model_run_id=model_run_id,
        )
        updated = replace(review, candidate_issue_ids=_append_unique(review.candidate_issue_ids, candidate.id))
        return updated, candidate

    def create_review_task_from_candidate(
        self,
        review: DraftLawReview,
        candidate: DraftCandidateIssue,
        *,
        created_by: str,
    ) -> tuple[DraftLawReview, ReviewTask]:
        if candidate.draft_review_id != review.id:
            raise ValueError("candidate does not belong to draft review")
        task = self.review_workflow.create_task(
            title=candidate.title,
            issue_type=candidate.issue_type,
            evidence_packet_id=candidate.evidence_packet_id,
            citation_ids=candidate.citation_ids,
            created_by=created_by,
        )
        updated = replace(review, review_task_ids=_append_unique(review.review_task_ids, task.id))
        return updated, task


def _append_unique(values: tuple[str, ...], value: str) -> tuple[str, ...]:
    if value in values:
        return values
    return values + (value,)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return tuple(unique)
