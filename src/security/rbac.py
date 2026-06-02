from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    ORGANIZATION_ADMIN = "organization_admin"
    LEGAL_REVIEWER = "legal_reviewer"
    COMPLIANCE_OFFICER = "compliance_officer"
    RESEARCHER = "researcher"
    VIEWER = "viewer"
    EXTERNAL_AUDITOR = "external_auditor"


class ProtectedAction(str, Enum):
    MANAGE_AI_SETTINGS = "manage_ai_settings"
    REVIEW_CANDIDATE = "review_candidate"
    EXPORT_EVIDENCE_PACKET = "export_evidence_packet"
    MANAGE_ORGANIZATION_PROFILE = "manage_organization_profile"
    VIEW_AUDIT_LOG = "view_audit_log"


class PermissionDenied(Exception):
    def __init__(self, detail: str, status_code: int = 403):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class AuthContext:
    actor_id: str
    role: Role
    organization_id: str | None = None

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise ValueError("actor_id is required")


ROLE_PERMISSIONS: dict[Role, frozenset[ProtectedAction]] = {
    Role.PLATFORM_ADMIN: frozenset(action for action in ProtectedAction),
    Role.ORGANIZATION_ADMIN: frozenset(
        {
            ProtectedAction.MANAGE_AI_SETTINGS,
            ProtectedAction.REVIEW_CANDIDATE,
            ProtectedAction.EXPORT_EVIDENCE_PACKET,
            ProtectedAction.MANAGE_ORGANIZATION_PROFILE,
            ProtectedAction.VIEW_AUDIT_LOG,
        }
    ),
    Role.LEGAL_REVIEWER: frozenset(
        {
            ProtectedAction.REVIEW_CANDIDATE,
            ProtectedAction.EXPORT_EVIDENCE_PACKET,
        }
    ),
    Role.COMPLIANCE_OFFICER: frozenset(
        {
            ProtectedAction.REVIEW_CANDIDATE,
            ProtectedAction.EXPORT_EVIDENCE_PACKET,
            ProtectedAction.MANAGE_ORGANIZATION_PROFILE,
        }
    ),
    Role.RESEARCHER: frozenset(),
    Role.VIEWER: frozenset(),
    Role.EXTERNAL_AUDITOR: frozenset({ProtectedAction.VIEW_AUDIT_LOG}),
}


def can_perform(actor: AuthContext | None, action: ProtectedAction) -> bool:
    if actor is None:
        return False
    return action in ROLE_PERMISSIONS.get(actor.role, frozenset())


def require_permission(
    actor: AuthContext | None,
    action: ProtectedAction,
    *,
    production_mode: bool,
) -> None:
    if not production_mode:
        return
    if actor is None:
        raise PermissionDenied(f"Authentication required for action: {action.value}")
    if not can_perform(actor, action):
        raise PermissionDenied(f"Role '{actor.role.value}' is not permitted to perform action: {action.value}")
