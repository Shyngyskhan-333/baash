from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping

from src.evidence.models import (
    Citation,
    EvidencePacket,
    EvidencePacketStatus,
    make_stable_id,
    normalize_text,
)


@dataclass(frozen=True, slots=True)
class EvidencePacketBundle:
    packet: EvidencePacket
    citations: tuple[Citation, ...]


class EvidencePacketService:
    """Builds immutable, citation-backed evidence packets without choosing storage yet."""

    def build_from_search_results(
        self,
        *,
        title: str,
        purpose: str,
        results: list[Mapping[str, Any]],
        summary: str | None = None,
        source_snapshot_ids: tuple[str, ...] = (),
        model_run_ids: tuple[str, ...] = (),
        review_task_ids: tuple[str, ...] = (),
        status: EvidencePacketStatus = EvidencePacketStatus.DRAFT,
    ) -> EvidencePacketBundle:
        citations = self._citations_from_results(results)
        packet = self.build_packet(
            title=title,
            purpose=purpose,
            citation_ids=tuple(citation.id for citation in citations),
            summary=summary,
            source_snapshot_ids=source_snapshot_ids,
            model_run_ids=model_run_ids,
            review_task_ids=review_task_ids,
            status=status,
        )
        return EvidencePacketBundle(packet=packet, citations=citations)

    def build_packet(
        self,
        *,
        title: str,
        purpose: str,
        citation_ids: tuple[str, ...],
        summary: str | None = None,
        source_snapshot_ids: tuple[str, ...] = (),
        model_run_ids: tuple[str, ...] = (),
        review_task_ids: tuple[str, ...] = (),
        status: EvidencePacketStatus = EvidencePacketStatus.DRAFT,
    ) -> EvidencePacket:
        unique_citation_ids = _dedupe(citation_ids)
        packet = EvidencePacket(
            id=make_stable_id("packet", title, purpose, "|".join(unique_citation_ids)),
            title=title,
            purpose=purpose,
            citation_ids=unique_citation_ids,
            status=status,
            source_snapshot_ids=_dedupe(source_snapshot_ids),
            model_run_ids=_dedupe(model_run_ids),
            review_task_ids=_dedupe(review_task_ids),
            summary=summary,
        )
        return packet.with_computed_hash()

    def export_bundle(self, bundle: EvidencePacketBundle) -> dict[str, Any]:
        return {
            "packet": _to_jsonable(asdict(bundle.packet)),
            "citations": [_to_jsonable(asdict(citation)) for citation in bundle.citations],
        }

    def _citations_from_results(self, results: list[Mapping[str, Any]]) -> tuple[Citation, ...]:
        citations: list[Citation] = []
        seen: set[str] = set()
        for result in results:
            citation = self._citation_from_result(result)
            if citation.id in seen:
                continue
            seen.add(citation.id)
            citations.append(citation)
        if not citations:
            raise ValueError("evidence packet requires at least one cited result")
        return tuple(citations)

    def _citation_from_result(self, result: Mapping[str, Any]) -> Citation:
        citation_id = _required(result, "citation_id")
        document_version_id = _required(result, "document_version_id")
        quote = normalize_text(_required(result, "citation_quote"))
        citation_label = _required(result, "citation_label")
        return Citation(
            id=citation_id,
            document_version_id=document_version_id,
            quote=quote,
            citation_label=citation_label,
            chunk_id=_optional(result, "chunk_id"),
        )


def _required(result: Mapping[str, Any], key: str) -> str:
    value = str(result.get(key, "")).strip()
    if not value:
        raise ValueError(f"{key} is required to build an evidence packet")
    return value


def _optional(result: Mapping[str, Any], key: str) -> str | None:
    value = str(result.get(key, "")).strip()
    return value or None


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
