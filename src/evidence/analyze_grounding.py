from __future__ import annotations

from typing import Any, Mapping

from src.evidence.ai_grounding import AIGroundingService
from src.evidence.legacy_adapter import citation_fields_for_legacy_result

ANALYZE_GROUNDING_NOTICE = "AI-generated summary; not a validated legal conclusion."


def build_analyze_evidence_results(
    doc_id: str,
    doc: Mapping[str, Any],
    *,
    max_results: int = 8,
) -> list[dict[str, Any]]:
    title = str(doc.get("title") or doc_id)
    results: list[dict[str, Any]] = []

    for article_index, article in enumerate(_articles(doc)):
        article_number = _article_number(article, article_index)
        for chunk_index, chunk in enumerate(_chunks(article)):
            text = str(chunk.get("text") or "").strip()
            if not text:
                continue
            result = {
                "doc_id": doc_id,
                "doc_title": title,
                "article_number": article_number,
                "chunk_id": str(chunk.get("chunk_id") or f"{doc_id}_{article_index}_{chunk_index}"),
                "text": text,
            }
            result.update(citation_fields_for_legacy_result(result))
            results.append(result)
            if len(results) >= max_results:
                return results

    return results


def ground_analyze_summary(
    *,
    doc_id: str,
    title: str,
    doc: Mapping[str, Any],
    summary: str,
    messages: list[Mapping[str, Any]],
    system_prompt: str | None = None,
    model_name: str = "configured-ai-provider",
    model_version: str = "unknown",
    max_evidence_results: int = 8,
) -> dict[str, Any] | None:
    evidence_results = build_analyze_evidence_results(doc_id, doc, max_results=max_evidence_results)
    if not evidence_results:
        return None

    grounded = AIGroundingService().ground_answer(
        answer=summary,
        model_name=model_name,
        model_version=model_version,
        messages=messages,
        evidence_results=evidence_results,
        packet_title=f"Analyze summary: {title}",
        packet_purpose="analyze route candidate grounding",
        system_prompt=system_prompt,
    )

    packet = grounded.evidence_packet.packet
    return {
        "status": "candidate",
        "validation_status": "not_human_validated",
        "model_run_id": grounded.model_run.id,
        "model_run_status": grounded.model_run.status.value,
        "evidence_packet_id": packet.id,
        "evidence_packet_hash": packet.packet_hash,
        "citation_ids": list(packet.citation_ids),
        "legal_claim_notice": ANALYZE_GROUNDING_NOTICE,
    }


def _articles(doc: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    articles = doc.get("articles")
    if not isinstance(articles, list):
        return []
    return [article for article in articles if isinstance(article, Mapping)]


def _article_number(article: Mapping[str, Any], article_index: int) -> str:
    for key in ("article_number", "number", "title"):
        value = str(article.get(key) or "").strip()
        if value:
            return value
    return f"article_{article_index + 1}"


def _chunks(article: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    chunks = article.get("chunks")
    if isinstance(chunks, list) and chunks:
        return [chunk for chunk in chunks if isinstance(chunk, Mapping)]
    text = str(article.get("text") or "").strip()
    if text:
        return [{"text": text}]
    return []
