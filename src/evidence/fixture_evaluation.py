from __future__ import annotations

from pathlib import Path
from typing import Mapping

from src.evidence.ai_grounding import GroundedAIOutput
from src.evidence.citation_accuracy_evaluation import SearchServiceLike
from src.evidence.evaluation_fixture_loader import EvaluationFixtureLoader
from src.evidence.evaluation_suite import EvaluationSuiteReport, EvaluationSuiteRunner


class FixtureEvaluationRunner:
    """Runs deterministic evaluation suites from local JSON fixture files."""

    def __init__(
        self,
        *,
        suite_runner: EvaluationSuiteRunner,
        fixture_loader: EvaluationFixtureLoader | None = None,
    ) -> None:
        self.suite_runner = suite_runner
        self.fixture_loader = fixture_loader or EvaluationFixtureLoader()

    @classmethod
    def from_search_service(cls, search_service: SearchServiceLike) -> FixtureEvaluationRunner:
        return cls(suite_runner=EvaluationSuiteRunner.from_search_service(search_service))

    def run_file(
        self,
        fixture_path: str | Path,
        *,
        expected_quotes: Mapping[str, str] | None = None,
        grounded_outputs: Mapping[str, GroundedAIOutput] | None = None,
    ) -> EvaluationSuiteReport:
        cases = self.fixture_loader.load_file(fixture_path)
        return self.suite_runner.run(
            cases=cases,
            expected_quotes=expected_quotes or {},
            grounded_outputs=grounded_outputs or {},
        )
