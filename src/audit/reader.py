from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.security.rbac import AuthContext, ProtectedAction, Role, require_permission


class JsonlAuditReader:
    """Reads local append-only audit records without treating malformed lines as fatal."""

    def __init__(self, path: str | Path = "data/audit/audit.jsonl"):
        self.path = Path(path)

    def list_records(self, *, limit: int | None = None, organization_id: str | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            record = _parse_record(line)
            if record is None:
                continue
            if not _matches_organization(record, organization_id):
                continue
            records.append(record)

        if limit is not None:
            return records[-max(limit, 0) :]
        return records


class AuditReadService:
    def __init__(self, reader: JsonlAuditReader | None = None):
        self.reader = reader or JsonlAuditReader()

    def list_records(
        self,
        *,
        actor: AuthContext | None,
        production_mode: bool,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        require_permission(actor, ProtectedAction.VIEW_AUDIT_LOG, production_mode=production_mode)
        organization_id = _organization_scope(actor)
        return self.reader.list_records(limit=limit, organization_id=organization_id)


def _parse_record(line: str) -> dict[str, Any] | None:
    if not line.strip():
        return None
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict):
        return None
    return record


def _matches_organization(record: dict[str, Any], organization_id: str | None) -> bool:
    if organization_id is None:
        return True
    record_org = record.get("organization_id")
    return record_org is None or record_org == organization_id


def _organization_scope(actor: AuthContext | None) -> str | None:
    if actor is None or actor.role == Role.PLATFORM_ADMIN:
        return None
    return actor.organization_id
