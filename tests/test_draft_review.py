import unittest

from src.draft_review.models import DraftReviewStatus
from src.draft_review.service import DraftReviewService
from src.evidence.review_workflow import ReviewStatus


class DraftReviewTests(unittest.TestCase):
    def test_create_draft_review_references_snapshot_and_scope(self):
        service = DraftReviewService()

        review = service.create_review(
            title="Draft amendments to civil procedure",
            draft_source_snapshot_id="snapshot_draft_1",
            target_document_version_ids=("version_current_1", "version_current_2"),
            created_by="gov_user_1",
            organization_id="ministry_justice",
        )

        self.assertEqual(review.status, DraftReviewStatus.DRAFT)
        self.assertEqual(review.draft_source_snapshot_id, "snapshot_draft_1")
        self.assertEqual(review.target_document_version_ids, ("version_current_1", "version_current_2"))
        self.assertEqual(review.organization_id, "ministry_justice")

    def test_add_candidate_issue_requires_evidence_packet_and_citations(self):
        service = DraftReviewService()
        review = service.create_review(
            title="Draft review",
            draft_source_snapshot_id="snapshot_draft_1",
            target_document_version_ids=("version_current_1",),
            created_by="gov_user_1",
            organization_id="ministry_justice",
        )

        updated, candidate = service.add_candidate_issue(
            review,
            issue_type="conflict_candidate",
            title="Potential conflict with Article 1",
            description="Candidate only; requires human review.",
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
            model_run_id="model_run_1",
        )

        self.assertEqual(updated.candidate_issue_ids, (candidate.id,))
        self.assertEqual(candidate.status, "candidate")
        self.assertEqual(candidate.validation_status, "not_human_validated")
        self.assertEqual(candidate.evidence_packet_id, "packet_1")
        self.assertEqual(candidate.citation_ids, ("citation_1",))

    def test_create_review_task_from_candidate_links_task_back_to_review(self):
        service = DraftReviewService()
        review = service.create_review(
            title="Draft review",
            draft_source_snapshot_id="snapshot_draft_1",
            target_document_version_ids=("version_current_1",),
            created_by="gov_user_1",
            organization_id="ministry_justice",
        )
        review, candidate = service.add_candidate_issue(
            review,
            issue_type="outdated_reference_candidate",
            title="Potential outdated reference",
            description="Candidate only.",
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
        )

        updated, task = service.create_review_task_from_candidate(
            review,
            candidate,
            created_by="gov_user_1",
        )

        self.assertEqual(updated.review_task_ids, (task.id,))
        self.assertEqual(task.status, ReviewStatus.CANDIDATE)
        self.assertEqual(task.evidence_packet_id, candidate.evidence_packet_id)
        self.assertEqual(task.citation_ids, candidate.citation_ids)

    def test_draft_review_rejects_empty_scope(self):
        service = DraftReviewService()

        with self.assertRaises(ValueError):
            service.create_review(
                title="Invalid review",
                draft_source_snapshot_id="snapshot_draft_1",
                target_document_version_ids=(),
                created_by="gov_user_1",
                organization_id="ministry_justice",
            )


if __name__ == "__main__":
    unittest.main()
