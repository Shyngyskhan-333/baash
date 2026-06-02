from __future__ import annotations

from src.evidence.models import make_stable_id
from src.evidence.review_workflow import ReviewTask, ReviewWorkflowService
from src.monitoring.models import ObligationCandidate, OrganizationProfile, RegulatoryAlert


class MonitoringService:
    def __init__(self, review_workflow: ReviewWorkflowService | None = None):
        self.review_workflow = review_workflow or ReviewWorkflowService()

    def create_organization_profile(
        self,
        *,
        organization_id: str,
        name: str,
        sector_ids: tuple[str, ...],
        watched_source_ids: tuple[str, ...],
        watched_document_ids: tuple[str, ...],
        created_by: str,
    ) -> OrganizationProfile:
        profile_id = make_stable_id("org_profile", organization_id, name, "|".join(sector_ids))
        return OrganizationProfile(
            id=profile_id,
            organization_id=organization_id,
            name=name,
            sector_ids=_dedupe(sector_ids),
            watched_source_ids=_dedupe(watched_source_ids),
            watched_document_ids=_dedupe(watched_document_ids),
            created_by=created_by,
        )

    def create_obligation_candidate(
        self,
        *,
        organization_id: str,
        title: str,
        description: str,
        affected_sector_ids: tuple[str, ...],
        evidence_packet_id: str,
        citation_ids: tuple[str, ...],
        model_run_id: str | None = None,
    ) -> ObligationCandidate:
        unique_citations = _dedupe(citation_ids)
        return ObligationCandidate(
            id=make_stable_id("obligation_candidate", organization_id, title, evidence_packet_id),
            organization_id=organization_id,
            title=title,
            description=description,
            affected_sector_ids=_dedupe(affected_sector_ids),
            evidence_packet_id=evidence_packet_id,
            citation_ids=unique_citations,
            model_run_id=model_run_id,
        )

    def create_regulatory_alert(
        self,
        *,
        profile: OrganizationProfile,
        title: str,
        change_document_version_id: str,
        evidence_packet_id: str,
        citation_ids: tuple[str, ...],
        obligation_candidate_ids: tuple[str, ...] = (),
    ) -> RegulatoryAlert:
        unique_citations = _dedupe(citation_ids)
        return RegulatoryAlert(
            id=make_stable_id("reg_alert", profile.organization_id, title, change_document_version_id, evidence_packet_id),
            organization_id=profile.organization_id,
            title=title,
            change_document_version_id=change_document_version_id,
            evidence_packet_id=evidence_packet_id,
            citation_ids=unique_citations,
            obligation_candidate_ids=_dedupe(obligation_candidate_ids),
        )

    def create_review_task_from_alert(self, alert: RegulatoryAlert, *, created_by: str) -> ReviewTask:
        return self.review_workflow.create_task(
            title=alert.title,
            issue_type="regulatory_alert_candidate",
            evidence_packet_id=alert.evidence_packet_id,
            citation_ids=alert.citation_ids,
            created_by=created_by,
        )


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
