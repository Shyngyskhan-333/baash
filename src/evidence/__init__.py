"""Evidence core domain models for LexLens V2."""

from src.evidence.models import (
    AuditLog,
    Citation,
    Clause,
    EvidencePacket,
    EvidencePacketStatus,
    LegalDocument,
    LegalDocumentVersion,
    ModelRun,
    SemanticChunk,
    Source,
    SourceSnapshot,
    SourceType,
    compute_sha256,
    make_stable_id,
)
from src.evidence.legacy_adapter import (
    LegacyEvidenceImport,
    citation_fields_for_legacy_result,
    import_legacy_document,
    import_legacy_parsed_dir,
)
from src.evidence.packet_service import EvidencePacketBundle, EvidencePacketService
from src.evidence.ai_grounding import AIGroundingService, GroundedAIOutput
from src.evidence.analyze_grounding import build_analyze_evidence_results, ground_analyze_summary
from src.evidence.citation_accuracy_evaluation import CitationAccuracyEvaluationService
from src.evidence.evaluation import EvaluationCase, EvaluationCaseType, EvaluationResult, EvaluationStatus
from src.evidence.evaluation_fixture_loader import EvaluationFixtureLoader
from src.evidence.evaluation_suite import EvaluationSuiteReport, EvaluationSuiteRunner
from src.evidence.fixture_evaluation import FixtureEvaluationRunner
from src.evidence.grounding_evaluation import GroundingEvaluationService
from src.evidence.review_workflow import ReviewDecision, ReviewStatus, ReviewTask, ReviewWorkflowService
from src.evidence.retrieval_evaluation import RetrievalEvaluationService
from src.evidence.interfaces import (
    CitationRepository,
    EvidencePacketRepository,
    LegalDocumentRepository,
    ModelRunRepository,
    RetrievalIndex,
    SourceRepository,
)
from src.evidence.memory_repository import InMemoryEvidenceRepository

__all__ = [
    "AuditLog",
    "Citation",
    "CitationAccuracyEvaluationService",
    "Clause",
    "EvidencePacket",
    "EvidencePacketStatus",
    "EvaluationCase",
    "EvaluationCaseType",
    "EvaluationResult",
    "EvaluationFixtureLoader",
    "EvaluationSuiteReport",
    "EvaluationSuiteRunner",
    "EvaluationStatus",
    "FixtureEvaluationRunner",
    "LegalDocument",
    "LegalDocumentVersion",
    "ModelRun",
    "SemanticChunk",
    "Source",
    "SourceSnapshot",
    "SourceType",
    "compute_sha256",
    "make_stable_id",
    "LegacyEvidenceImport",
    "citation_fields_for_legacy_result",
    "import_legacy_document",
    "import_legacy_parsed_dir",
    "EvidencePacketBundle",
    "EvidencePacketService",
    "AIGroundingService",
    "GroundedAIOutput",
    "GroundingEvaluationService",
    "build_analyze_evidence_results",
    "ground_analyze_summary",
    "ReviewDecision",
    "ReviewStatus",
    "ReviewTask",
    "ReviewWorkflowService",
    "CitationRepository",
    "EvidencePacketRepository",
    "InMemoryEvidenceRepository",
    "LegalDocumentRepository",
    "ModelRunRepository",
    "RetrievalIndex",
    "RetrievalEvaluationService",
    "SourceRepository",
]
