from __future__ import annotations

from typing import Any, Protocol

from src.evidence.evaluation import EvaluationCase, EvaluationCaseType, EvaluationResult, EvaluationStatus
from src.evidence.models import make_stable_id


class SearchServiceLike(Protocol):
    def search(self, query: str, *, top_k: int = 10, doc_ids: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
        ...


class RetrievalEvaluationService:
    """Deterministically evaluates canonical retrieval recall against expected citations."""

    def __init__(self, search_service: SearchServiceLike):
        self.search_service = search_service

    def evaluate(self, case: EvaluationCase, *, top_k: int = 10) -> EvaluationResult:
        if case.case_type != EvaluationCaseType.RETRIEVAL_RECALL:
            raise ValueError("RetrievalEvaluationService only supports retrieval_recall cases")

        response = self.search_service.search(case.query, top_k=top_k)
        observed_citation_ids = _observed_citation_ids(response.get("results", []))
        expected = set(case.expected_citation_ids)
        observed = set(observed_citation_ids)
        matched_count = len(expected.intersection(observed))
        score = matched_count / len(expected)
        status = EvaluationStatus.PASSED if score == 1.0 else EvaluationStatus.FAILED
        result_id = make_stable_id(
            "eval_result",
            case.id,
            "|".join(observed_citation_ids),
            f"{score:.6f}",
        )
        return EvaluationResult(
            id=result_id,
            case_id=case.id,
            status=status,
            observed_citation_ids=observed_citation_ids,
            score=score,
            notes=f"Retrieved {matched_count}/{len(expected)} expected citations.",
        )


def _observed_citation_ids(results: list[dict[str, Any]]) -> tuple[str, ...]:
    observed: list[str] = []
    seen: set[str] = set()
    for result in results:
        citation_id = str(result.get("citation_id", "")).strip()
        if citation_id and citation_id not in seen:
            seen.add(citation_id)
            observed.append(citation_id)
    return tuple(observed)
