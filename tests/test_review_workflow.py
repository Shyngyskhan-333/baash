import unittest

from src.evidence.review_workflow import (
    ReviewDecision,
    ReviewStatus,
    ReviewWorkflowService,
)


class ReviewWorkflowTests(unittest.TestCase):
    def test_create_task_starts_as_candidate_with_evidence_packet(self):
        service = ReviewWorkflowService()

        task = service.create_task(
            title="Potential conflict",
            issue_type="conflict_candidate",
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
            created_by="system",
        )

        self.assertEqual(task.status, ReviewStatus.CANDIDATE)
        self.assertEqual(task.validation_status, "not_human_validated")
        self.assertEqual(task.evidence_packet_id, "packet_1")
        self.assertEqual(task.citation_ids, ("citation_1",))

    def test_validate_requires_human_reviewer_and_note(self):
        service = ReviewWorkflowService()
        task = service.create_task(
            title="Potential issue",
            issue_type="duplicate_candidate",
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
            created_by="system",
        )
        under_review, _audit = service.transition(
            task,
            decision=ReviewDecision.START_REVIEW,
            actor_id="reviewer_1",
            note="Taking ownership.",
        )

        validated, audit = service.transition(
            under_review,
            decision=ReviewDecision.VALIDATE,
            actor_id="reviewer_1",
            note="Confirmed after legal review.",
        )

        self.assertEqual(validated.status, ReviewStatus.VALIDATED)
        self.assertEqual(validated.validation_status, "human_validated")
        self.assertEqual(validated.reviewed_by, "reviewer_1")
        self.assertEqual(audit.action, "review_task.validated")
        self.assertEqual(audit.target_id, task.id)

    def test_validate_from_candidate_without_review_is_rejected(self):
        service = ReviewWorkflowService()
        task = service.create_task(
            title="Potential issue",
            issue_type="outdated_norm_candidate",
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
            created_by="system",
        )

        with self.assertRaises(ValueError):
            service.transition(
                task,
                decision=ReviewDecision.VALIDATE,
                actor_id="reviewer_1",
                note="Trying to skip review.",
            )

    def test_reject_and_needs_evidence_keep_task_not_validated(self):
        service = ReviewWorkflowService()
        task = service.create_task(
            title="Potential issue",
            issue_type="conflict_candidate",
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
            created_by="system",
        )
        under_review, _audit = service.transition(
            task,
            decision=ReviewDecision.START_REVIEW,
            actor_id="reviewer_1",
            note="Reviewing.",
        )

        needs_evidence, _audit = service.transition(
            under_review,
            decision=ReviewDecision.REQUEST_EVIDENCE,
            actor_id="reviewer_1",
            note="Need source date proof.",
        )
        rejected, _audit = service.transition(
            under_review,
            decision=ReviewDecision.REJECT,
            actor_id="reviewer_1",
            note="False positive.",
        )

        self.assertEqual(needs_evidence.status, ReviewStatus.NEEDS_EVIDENCE)
        self.assertEqual(needs_evidence.validation_status, "not_human_validated")
        self.assertEqual(rejected.status, ReviewStatus.REJECTED)
        self.assertEqual(rejected.validation_status, "human_rejected")


if __name__ == "__main__":
    unittest.main()
