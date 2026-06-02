from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping

from src.evidence.models import (
    ModelRun,
    ModelRunStatus,
    compute_sha256,
    make_stable_id,
)
from src.evidence.packet_service import EvidencePacketBundle, EvidencePacketService


@dataclass(frozen=True, slots=True)
class GroundedAIOutput:
    answer: str
    model_run: ModelRun
    evidence_packet: EvidencePacketBundle


class AIGroundingService:
    """Creates auditable AI outputs tied to citations, model metadata, and evidence packets."""

    def __init__(self, packet_service: EvidencePacketService | None = None):
        self.packet_service = packet_service or EvidencePacketService()

    def ground_answer(
        self,
        *,
        answer: str,
        model_name: str,
        model_version: str,
        messages: list[Mapping[str, Any]],
        evidence_results: list[Mapping[str, Any]],
        packet_title: str,
        packet_purpose: str,
        system_prompt: str | None = None,
        parameters: Mapping[str, Any] | None = None,
    ) -> GroundedAIOutput:
        if not answer.strip():
            raise ValueError("answer is required for grounded AI output")

        initial_packet = self.packet_service.build_from_search_results(
            title=packet_title,
            purpose=packet_purpose,
            results=evidence_results,
            summary=answer,
            source_snapshot_ids=_source_snapshot_ids(evidence_results),
        )
        citation_ids = initial_packet.packet.citation_ids
        model_run = self.build_model_run(
            model_name=model_name,
            model_version=model_version,
            messages=messages,
            input_citation_ids=citation_ids,
            output=answer,
            system_prompt=system_prompt,
            parameters=parameters or {},
        )
        final_packet = self.packet_service.build_from_search_results(
            title=packet_title,
            purpose=packet_purpose,
            results=evidence_results,
            summary=answer,
            source_snapshot_ids=_source_snapshot_ids(evidence_results),
            model_run_ids=(model_run.id,),
        )
        return GroundedAIOutput(answer=answer, model_run=model_run, evidence_packet=final_packet)

    def build_model_run(
        self,
        *,
        model_name: str,
        model_version: str,
        messages: list[Mapping[str, Any]],
        input_citation_ids: tuple[str, ...],
        output: str | None = None,
        system_prompt: str | None = None,
        parameters: Mapping[str, Any] | None = None,
        status: ModelRunStatus = ModelRunStatus.SUCCEEDED,
    ) -> ModelRun:
        if not input_citation_ids:
            raise ValueError("input_citation_ids must contain at least one citation for grounded AI output")
        prompt_hash = self.prompt_hash(messages=messages, system_prompt=system_prompt)
        output_hash = compute_sha256(output) if output is not None else None
        model_run_id = make_stable_id(
            "model_run",
            model_name,
            model_version,
            prompt_hash,
            output_hash or "",
            "|".join(input_citation_ids),
        )
        return ModelRun(
            id=model_run_id,
            model_name=model_name,
            model_version=model_version,
            prompt_hash=prompt_hash,
            input_citation_ids=input_citation_ids,
            output_hash=output_hash,
            status=status,
            parameters=parameters or {},
        )

    def export_grounded_output(self, grounded: GroundedAIOutput) -> dict[str, Any]:
        return {
            "answer": grounded.answer,
            "model_run": _to_jsonable(asdict(grounded.model_run)),
            "evidence_packet": self.packet_service.export_bundle(grounded.evidence_packet),
        }

    def prompt_hash(self, *, messages: list[Mapping[str, Any]], system_prompt: str | None = None) -> str:
        payload = {
            "system_prompt": system_prompt,
            "messages": [
                {
                    "role": str(message.get("role", "")).strip(),
                    "content": str(message.get("content", "")),
                }
                for message in messages
            ],
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return compute_sha256(raw)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _source_snapshot_ids(evidence_results: list[Mapping[str, Any]]) -> tuple[str, ...]:
    ids: list[str] = []
    seen: set[str] = set()
    for result in evidence_results:
        source_snapshot_id = str(result.get("source_snapshot_id", "")).strip()
        if source_snapshot_id and source_snapshot_id not in seen:
            seen.add(source_snapshot_id)
            ids.append(source_snapshot_id)
    return tuple(ids)
