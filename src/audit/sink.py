from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.evidence.models import AuditLog


class JsonlAuditSink:
    """Append-only local JSONL sink for immutable audit log records."""

    def __init__(self, path: str | Path = "data/audit/audit.jsonl"):
        self.path = Path(path)

    def append(self, audit_log: AuditLog) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = _to_jsonable(asdict(audit_log))
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            file.write("\n")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
