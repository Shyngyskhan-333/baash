from __future__ import annotations

from typing import Any, Mapping, Protocol

from src.evidence.evaluation import EvaluationCase, EvaluationCaseType, EvaluationResult, EvaluationStatus
from src.evidence.models import make_stable_id, normalize_text
from src.evidence.retrieval_evaluation import _observed_citation_ids


class SearchServiceLike(Protocol):
    def search(self, query: str, *, top_k: int = 10, doc_ids: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
        ...


class CitationAccuracyEvaluationService:
    """Deterministically verifies citation quote and document-version integrity."""

    def __init__(self, search_service: SearchServiceLike):
        self.search_service = search_service

    def evaluate(
        self,
        case: EvaluationCase,
        *,
        expected_quotes: Mapping[str, str],
        top_k: int = 10,
    ) -> EvaluationResult:
        if case.case_type != EvaluationCaseType.CITATION_ACCURACY:
            raise ValueError("CitationAccuracyEvaluationService only supports citation_accuracy cases")

        results = self.search_service.search(case.query, top_k=top_k).get("results", [])
        observed_citation_ids = _observed_citation_ids(results)
        result_by_citation_id = {
            str(result.get("citation_id", "")).strip(): result
            for result in results
            if str(result.get("citation_id", "")).strip()
        }
        failures = _citation_failures(
            expected_citation_ids=case.expected_citation_ids,
            expected_document_version_ids=case.expected_document_version_ids,
            expected_quotes=expected_quotes,
            result_by_citation_id=result_by_citation_id,
        )
        expected_count = len(case.expected_citation_ids)
        score = (expected_count - len(failures)) / expected_count
        status = EvaluationStatus.PASSED if not failures else EvaluationStatus.FAILED
        result_id = make_stable_id(
            "eval_result",
            case.id,
            "|".join(observed_citation_ids),
            f"{score:.6f}",
            "|".join(failures),
        )
        return EvaluationResult(
            id=result_id,
            case_id=case.id,
            status=status,
            observed_citation_ids=observed_citation_ids,
            score=score,
            notes="; ".join(failures) if failures else "All expected citations matched quote and version.",
        )


def _citation_failures(
    *,
    expected_citation_ids: tuple[str, ...],
    expected_document_version_ids: tuple[str, ...],
    expected_quotes: Mapping[str, str],
    result_by_citation_id: dict[str, dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    expected_versions = set(expected_document_version_ids)
    for citation_id in expected_citation_ids:
        result = result_by_citation_id.get(citation_id)
        if result is None:
            failures.append(f"{citation_id}: missing citation")
            continue
        expected_quote = expected_quotes.get(citation_id)
        if expected_quote is not None and normalize_text(str(result.get("citation_quote", ""))) != normalize_text(
            expected_quote
        ):
            failures.append(f"{citation_id}: quote mismatch")
        if expected_versions and str(result.get("document_version_id", "")).strip() not in expected_versions:
            failures.append(f"{citation_id}: version mismatch")
    return failures
