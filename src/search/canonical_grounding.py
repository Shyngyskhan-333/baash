from __future__ import annotations

from typing import Any, Mapping

from src.evidence.ai_grounding import AIGroundingService, GroundedAIOutput
from src.search.canonical_service import CanonicalSearchService


class CanonicalSearchGroundingService:
    """Grounds AI output using canonical evidence-core search results."""

    def __init__(
        self,
        *,
        search_service: CanonicalSearchService,
        grounding_service: AIGroundingService | None = None,
    ) -> None:
        self.search_service = search_service
        self.grounding_service = grounding_service or AIGroundingService()

    @classmethod
    def from_repository(cls, repository: Any) -> CanonicalSearchGroundingService:
        return cls(search_service=CanonicalSearchService.from_repository(repository))

    def ground_answer(
        self,
        *,
        query: str,
        answer: str,
        model_name: str,
        model_version: str,
        messages: list[Mapping[str, Any]],
        packet_title: str,
        packet_purpose: str,
        top_k: int = 10,
        doc_ids: list[str] | None = None,
        system_prompt: str | None = None,
        parameters: Mapping[str, Any] | None = None,
    ) -> GroundedAIOutput:
        search_response = self.search_service.search(query, top_k=top_k, doc_ids=doc_ids)
        evidence_results = search_response["results"]
        if not evidence_results:
            raise ValueError("canonical search returned no cited evidence for grounded AI output")
        return self.grounding_service.ground_answer(
            answer=answer,
            model_name=model_name,
            model_version=model_version,
            messages=messages,
            evidence_results=evidence_results,
            packet_title=packet_title,
            packet_purpose=packet_purpose,
            system_prompt=system_prompt,
            parameters=parameters or {},
        )
