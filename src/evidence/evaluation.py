from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from src.evidence.models import compute_sha256, make_stable_id


class EvaluationCaseType(str, Enum):
    RETRIEVAL_RECALL = "retrieval_recall"
    CITATION_ACCURACY = "citation_accuracy"
    ANSWER_GROUNDING = "answer_grounding"
    HALLUCINATION = "hallucination"
    CONTRADICTION_CANDIDATE = "contradiction_candidate"


class EvaluationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    id: str
    case_type: EvaluationCaseType
    name: str
    query: str
    expected_citation_ids: tuple[str, ...]
    expected_document_version_ids: tuple[str, ...] = field(default_factory=tuple)
    source: str = "manual"
    input_hash: str | None = None

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.name, "name")
        _require(self.query, "query")
        if not self.expected_citation_ids:
            raise ValueError("expected_citation_ids must contain at least one citation")
        for citation_id in self.expected_citation_ids:
            _require(citation_id, "expected_citation_id")
        if self.input_hash is None:
            object.__setattr__(self, "input_hash", compute_sha256(self.query))
        _require_hash(self.input_hash, "input_hash")

    @classmethod
    def create(
        cls,
        *,
        case_type: EvaluationCaseType,
        name: str,
        query: str,
        expected_citation_ids: tuple[str, ...],
        expected_document_version_ids: tuple[str, ...] = (),
        source: str = "manual",
    ) -> EvaluationCase:
        return cls(
            id=make_stable_id("eval_case", case_type.value, name, query, "|".join(expected_citation_ids)),
            case_type=case_type,
            name=name,
            query=query,
            expected_citation_ids=expected_citation_ids,
            expected_document_version_ids=expected_document_version_ids,
            source=source,
        )


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    id: str
    case_id: str
    status: EvaluationStatus
    observed_citation_ids: tuple[str, ...]
    observed_model_run_id: str | None = None
    score: float | None = None
    notes: str | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require(self.id, "id")
        _require(self.case_id, "case_id")
        for citation_id in self.observed_citation_ids:
            _require(citation_id, "observed_citation_id")
        if self.observed_model_run_id is not None:
            _require(self.observed_model_run_id, "observed_model_run_id")
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")


def _require(value: str | None, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _require_hash(value: str | None, field_name: str) -> str:
    normalized = _require(value, field_name).lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    return normalized
