import unittest

from src.evidence.review_workflow import ReviewStatus
from src.monitoring.models import RegulatoryAlertStatus
from src.monitoring.service import MonitoringService


class MonitoringTests(unittest.TestCase):
    def test_create_organization_profile_tracks_sectors_and_watched_documents(self):
        service = MonitoringService()

        profile = service.create_organization_profile(
            organization_id="bank_1",
            name="Bank One",
            sector_ids=("banking", "finance"),
            watched_source_ids=("adilet",),
            watched_document_ids=("doc_tax_code",),
            created_by="compliance_admin",
        )

        self.assertEqual(profile.organization_id, "bank_1")
        self.assertEqual(profile.sector_ids, ("banking", "finance"))
        self.assertEqual(profile.watched_source_ids, ("adilet",))
        self.assertEqual(profile.watched_document_ids, ("doc_tax_code",))

    def test_create_obligation_candidate_requires_citations_and_evidence_packet(self):
        service = MonitoringService()

        obligation = service.create_obligation_candidate(
            organization_id="bank_1",
            title="Report threshold changes",
            description="Candidate obligation; requires human validation.",
            affected_sector_ids=("banking",),
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
            model_run_id="model_run_1",
        )

        self.assertEqual(obligation.status, "candidate")
        self.assertEqual(obligation.validation_status, "not_human_validated")
        self.assertEqual(obligation.evidence_packet_id, "packet_1")
        self.assertEqual(obligation.citation_ids, ("citation_1",))

    def test_create_regulatory_alert_links_profile_obligation_and_evidence(self):
        service = MonitoringService()
        profile = service.create_organization_profile(
            organization_id="bank_1",
            name="Bank One",
            sector_ids=("banking",),
            watched_source_ids=("adilet",),
            watched_document_ids=("doc_tax_code",),
            created_by="compliance_admin",
        )
        obligation = service.create_obligation_candidate(
            organization_id=profile.organization_id,
            title="Candidate obligation",
            description="Requires review.",
            affected_sector_ids=("banking",),
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
        )

        alert = service.create_regulatory_alert(
            profile=profile,
            title="Tax Code changed",
            change_document_version_id="version_tax_2026",
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
            obligation_candidate_ids=(obligation.id,),
        )

        self.assertEqual(alert.status, RegulatoryAlertStatus.CANDIDATE)
        self.assertEqual(alert.organization_id, "bank_1")
        self.assertEqual(alert.obligation_candidate_ids, (obligation.id,))
        self.assertEqual(alert.evidence_packet_id, "packet_1")

    def test_create_review_task_from_alert_preserves_candidate_status(self):
        service = MonitoringService()
        profile = service.create_organization_profile(
            organization_id="bank_1",
            name="Bank One",
            sector_ids=("banking",),
            watched_source_ids=("adilet",),
            watched_document_ids=("doc_tax_code",),
            created_by="compliance_admin",
        )
        alert = service.create_regulatory_alert(
            profile=profile,
            title="Tax Code changed",
            change_document_version_id="version_tax_2026",
            evidence_packet_id="packet_1",
            citation_ids=("citation_1",),
        )

        task = service.create_review_task_from_alert(alert, created_by="compliance_admin")

        self.assertEqual(task.status, ReviewStatus.CANDIDATE)
        self.assertEqual(task.evidence_packet_id, alert.evidence_packet_id)
        self.assertEqual(task.citation_ids, alert.citation_ids)

    def test_obligation_candidate_rejects_empty_citations(self):
        service = MonitoringService()

        with self.assertRaises(ValueError):
            service.create_obligation_candidate(
                organization_id="bank_1",
                title="Invalid",
                description="Missing evidence.",
                affected_sector_ids=("banking",),
                evidence_packet_id="packet_1",
                citation_ids=(),
            )


if __name__ == "__main__":
    unittest.main()
