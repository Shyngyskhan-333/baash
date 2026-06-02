from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from src.evidence.ai_grounding import GroundedAIOutput
from src.evidence.citation_accuracy_evaluation import CitationAccuracyEvaluationService, SearchServiceLike
from src.evidence.evaluation import EvaluationCase, EvaluationCaseType, EvaluationResult, EvaluationStatus
from src.evidence.grounding_evaluation import GroundingEvaluationService
from src.evidence.retrieval_evaluation import RetrievalEvaluationService


@dataclass(frozen=True, slots=True)
class EvaluationSuiteReport:
    results: tuple[EvaluationResult, ...]

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def passed_cases(self) -> int:
        return sum(1 for result in self.results if result.status == EvaluationStatus.PASSED)

    @property
    def failed_cases(self) -> int:
        return sum(1 for result in self.results if result.status == EvaluationStatus.FAILED)


class EvaluationSuiteRunner:
    """Runs explicitly supplied deterministic evaluation cases."""

    def __init__(
        self,
        *,
        retrieval_evaluator: RetrievalEvaluationService,
        citation_evaluator: CitationAccuracyEvaluationService,
        grounding_evaluator: GroundingEvaluationService | None = None,
    ) -> None:
        self.retrieval_evaluator = retrieval_evaluator
        self.citation_evaluator = citation_evaluator
        self.grounding_evaluator = grounding_evaluator or GroundingEvaluationService()

    @classmethod
    def from_search_service(cls, search_service: SearchServiceLike) -> EvaluationSuiteRunner:
        return cls(
            retrieval_evaluator=RetrievalEvaluationService(search_service),
            citation_evaluator=CitationAccuracyEvaluationService(search_service),
        )

    def run(
        self,
        *,
        cases: tuple[EvaluationCase, ...],
        expected_quotes: Mapping[str, str] | None = None,
        grounded_outputs: Mapping[str, GroundedAIOutput] | None = None,
    ) -> EvaluationSuiteReport:
        results: list[EvaluationResult] = []
        for case in cases:
            results.append(
                self._evaluate_case(
                    case,
                    expected_quotes=expected_quotes or {},
                    grounded_outputs=grounded_outputs or {},
                )
            )
        return EvaluationSuiteReport(results=tuple(results))

    def _evaluate_case(
        self,
        case: EvaluationCase,
        *,
        expected_quotes: Mapping[str, str],
        grounded_outputs: Mapping[str, GroundedAIOutput],
    ) -> EvaluationResult:
        if case.case_type == EvaluationCaseType.RETRIEVAL_RECALL:
            return self.retrieval_evaluator.evaluate(case)
        if case.case_type == EvaluationCaseType.CITATION_ACCURACY:
            return self.citation_evaluator.evaluate(case, expected_quotes=expected_quotes)
        if case.case_type == EvaluationCaseType.ANSWER_GROUNDING:
            grounded = grounded_outputs.get(case.id)
            if grounded is None:
                raise ValueError(f"grounded output is required for evaluation case {case.id}")
            return self.grounding_evaluator.evaluate(case, grounded)
        raise ValueError(f"unsupported evaluation case type: {case.case_type}")
