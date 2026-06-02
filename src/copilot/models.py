from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CopilotAnswerStatus(str, Enum):
    ANSWERED = "answered"
    REFUSED = "refused"


class CopilotUncertainty(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class CopilotAnswer:
    question: str
    answer_text: str
    status: CopilotAnswerStatus
    uncertainty: CopilotUncertainty
    citation_ids: tuple[str, ...]
    evidence_packet_id: str | None = None
    evidence_packet_hash: str | None = None
    model_run_id: str | None = None
    validation_status: str = "not_human_validated"
    legal_claim_notice: str = "AI-generated research answer; not a validated legal conclusion."

    def __post_init__(self) -> None:
        _require(self.question, "question")
        _require(self.answer_text, "answer_text")
        _require(self.validation_status, "validation_status")
        _require(self.legal_claim_notice, "legal_claim_notice")
        if self.status == CopilotAnswerStatus.ANSWERED:
            if not self.citation_ids:
                raise ValueError("answered copilot output requires at least one citation")
            _require(self.evidence_packet_id, "evidence_packet_id")
            _require(self.evidence_packet_hash, "evidence_packet_hash")
            _require(self.model_run_id, "model_run_id")
        if self.status == CopilotAnswerStatus.REFUSED:
            if self.citation_ids:
                raise ValueError("refused copilot output must not claim supporting citations")
            if self.evidence_packet_id or self.evidence_packet_hash or self.model_run_id:
                raise ValueError("refused copilot output must not link generated evidence artifacts")


def _require(value: str | None, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field_name} is required")
    return str(value).strip()
