from __future__ import annotations

from dataclasses import asdict
from enum import Enum
from typing import Any, Mapping

from src.copilot.models import CopilotAnswer, CopilotAnswerStatus, CopilotUncertainty
from src.evidence.ai_grounding import AIGroundingService


class CopilotGroundingService:
    """Creates copilot answer contracts without changing the current chat API."""

    def __init__(self, grounding_service: AIGroundingService | None = None):
        self.grounding_service = grounding_service or AIGroundingService()

    def create_grounded_answer(
        self,
        *,
        question: str,
        answer_text: str,
        model_name: str,
        model_version: str,
        messages: list[Mapping[str, Any]],
        evidence_results: list[Mapping[str, Any]],
        uncertainty: CopilotUncertainty = CopilotUncertainty.MEDIUM,
        system_prompt: str | None = None,
        parameters: Mapping[str, Any] | None = None,
    ) -> CopilotAnswer:
        _require(question, "question")
        _require(answer_text, "answer_text")
        if not evidence_results:
            raise ValueError("evidence_results must contain cited evidence for a grounded copilot answer")

        grounded = self.grounding_service.ground_answer(
            answer=answer_text,
            model_name=model_name,
            model_version=model_version,
            messages=messages,
            evidence_results=evidence_results,
            packet_title=f"Legal Research Copilot: {question}",
            packet_purpose="legal research copilot answer",
            system_prompt=system_prompt,
            parameters=parameters or {},
        )
        packet = grounded.evidence_packet.packet
        return CopilotAnswer(
            question=question,
            answer_text=answer_text,
            status=CopilotAnswerStatus.ANSWERED,
            uncertainty=uncertainty,
            citation_ids=packet.citation_ids,
            evidence_packet_id=packet.id,
            evidence_packet_hash=packet.packet_hash,
            model_run_id=grounded.model_run.id,
        )

    def create_refusal(self, *, question: str, reason: str) -> CopilotAnswer:
        _require(question, "question")
        _require(reason, "reason")
        return CopilotAnswer(
            question=question,
            answer_text=f"Insufficient cited legal evidence to answer: {reason}",
            status=CopilotAnswerStatus.REFUSED,
            uncertainty=CopilotUncertainty.INSUFFICIENT_EVIDENCE,
            citation_ids=(),
            legal_claim_notice="No legal conclusion was generated because cited evidence was insufficient.",
        )

    def export_answer(self, answer: CopilotAnswer) -> dict[str, Any]:
        return _to_jsonable(asdict(answer))


def _require(value: str, field_name: str) -> str:
    if not str(value).strip():
        raise ValueError(f"{field_name} is required")
    return str(value).strip()


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value
