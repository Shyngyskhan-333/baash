from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from src.evidence.evaluation import EvaluationCase, EvaluationCaseType


class EvaluationFixtureLoader:
    """Loads version-controlled evaluation cases from local JSON fixtures."""

    def load_file(self, fixture_path: str | Path) -> tuple[EvaluationCase, ...]:
        path = Path(fixture_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        cases_payload = payload.get("cases") if isinstance(payload, Mapping) else None
        if not isinstance(cases_payload, list):
            raise ValueError("evaluation fixture must contain a cases list")
        return tuple(_case_from_payload(case_payload) for case_payload in cases_payload)


def _case_from_payload(payload: Any) -> EvaluationCase:
    if not isinstance(payload, Mapping):
        raise ValueError("evaluation case payload must be an object")

    case_type = EvaluationCaseType(_required(payload, "case_type"))
    name = _required(payload, "name")
    query = _required(payload, "query")
    expected_citation_ids = _string_tuple(payload.get("expected_citation_ids"), "expected_citation_ids")
    expected_document_version_ids = _string_tuple(
        payload.get("expected_document_version_ids", []),
        "expected_document_version_ids",
        allow_empty=True,
    )
    source = str(payload.get("source") or "fixture").strip() or "fixture"
    explicit_id = str(payload.get("id") or "").strip()
    if explicit_id:
        return EvaluationCase(
            id=explicit_id,
            case_type=case_type,
            name=name,
            query=query,
            expected_citation_ids=expected_citation_ids,
            expected_document_version_ids=expected_document_version_ids,
            source=source,
        )
    return EvaluationCase.create(
        case_type=case_type,
        name=name,
        query=query,
        expected_citation_ids=expected_citation_ids,
        expected_document_version_ids=expected_document_version_ids,
        source=source,
    )


def _required(payload: Mapping[str, Any], key: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _string_tuple(value: Any, field_name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    values = tuple(str(item).strip() for item in value if str(item).strip())
    if not allow_empty and not values:
        raise ValueError(f"{field_name} must contain at least one value")
    return values
