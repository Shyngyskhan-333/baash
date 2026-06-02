from __future__ import annotations

from src.evidence.ai_grounding import GroundedAIOutput
from src.evidence.evaluation import EvaluationCase, EvaluationCaseType, EvaluationResult, EvaluationStatus
from src.evidence.models import make_stable_id


class GroundingEvaluationService:
    """Evaluates whether grounded AI output preserves required evidence traceability."""

    def evaluate(self, case: EvaluationCase, grounded: GroundedAIOutput) -> EvaluationResult:
        if case.case_type != EvaluationCaseType.ANSWER_GROUNDING:
            raise ValueError("GroundingEvaluationService only supports answer_grounding cases")

        observed_citation_ids = grounded.model_run.input_citation_ids
        failures = _grounding_failures(case=case, grounded=grounded, observed_citation_ids=observed_citation_ids)
        expected = set(case.expected_citation_ids)
        observed = set(observed_citation_ids)
        matched_count = len(expected.intersection(observed))
        score = matched_count / len(expected) if not failures else 0.0
        status = EvaluationStatus.PASSED if not failures else EvaluationStatus.FAILED
        result_id = make_stable_id(
            "eval_result",
            case.id,
            grounded.model_run.id,
            "|".join(observed_citation_ids),
            "|".join(failures),
        )
        return EvaluationResult(
            id=result_id,
            case_id=case.id,
            status=status,
            observed_citation_ids=observed_citation_ids,
            observed_model_run_id=grounded.model_run.id,
            score=score,
            notes="; ".join(failures) if failures else "Grounded output traceability matched expected citations.",
        )


def _grounding_failures(
    *,
    case: EvaluationCase,
    grounded: GroundedAIOutput,
    observed_citation_ids: tuple[str, ...],
) -> list[str]:
    failures: list[str] = []
    expected = set(case.expected_citation_ids)
    observed = set(observed_citation_ids)
    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    if missing:
        failures.append(f"missing expected citations: {', '.join(missing)}")
    if unexpected:
        failures.append(f"unexpected citations: {', '.join(unexpected)}")
    packet = grounded.evidence_packet.packet
    if grounded.model_run.id not in packet.model_run_ids:
        failures.append("packet missing model run link")
    if set(packet.citation_ids) != observed:
        failures.append("packet citations do not match model input citations")
    if not grounded.model_run.output_hash:
        failures.append("model run missing output hash")
    return failures
