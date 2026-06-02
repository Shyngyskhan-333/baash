import unittest

from src.security.rbac import (
    AuthContext,
    PermissionDenied,
    ProtectedAction,
    Role,
    can_perform,
    require_permission,
)


class RBACTests(unittest.TestCase):
    def test_platform_and_organization_admin_can_manage_ai_settings(self):
        for role in (Role.PLATFORM_ADMIN, Role.ORGANIZATION_ADMIN):
            actor = AuthContext(actor_id=f"{role.value}_1", role=role, organization_id="org_1")

            self.assertTrue(can_perform(actor, ProtectedAction.MANAGE_AI_SETTINGS))

    def test_non_admin_roles_cannot_manage_ai_settings(self):
        for role in (
            Role.LEGAL_REVIEWER,
            Role.COMPLIANCE_OFFICER,
            Role.RESEARCHER,
            Role.VIEWER,
            Role.EXTERNAL_AUDITOR,
        ):
            actor = AuthContext(actor_id=f"{role.value}_1", role=role, organization_id="org_1")

            self.assertFalse(can_perform(actor, ProtectedAction.MANAGE_AI_SETTINGS))

    def test_development_mode_allows_missing_actor_for_legacy_behavior(self):
        self.assertIsNone(
            require_permission(
                None,
                ProtectedAction.MANAGE_AI_SETTINGS,
                production_mode=False,
            )
        )

    def test_production_mode_rejects_missing_actor(self):
        with self.assertRaises(PermissionDenied) as ctx:
            require_permission(
                None,
                ProtectedAction.MANAGE_AI_SETTINGS,
                production_mode=True,
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Authentication required", ctx.exception.detail)

    def test_production_mode_rejects_wrong_role(self):
        actor = AuthContext(actor_id="reviewer_1", role=Role.LEGAL_REVIEWER, organization_id="org_1")

        with self.assertRaises(PermissionDenied) as ctx:
            require_permission(
                actor,
                ProtectedAction.MANAGE_AI_SETTINGS,
                production_mode=True,
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not permitted", ctx.exception.detail)

    def test_production_mode_allows_admin_role(self):
        actor = AuthContext(actor_id="admin_1", role=Role.ORGANIZATION_ADMIN, organization_id="org_1")

        self.assertIsNone(
            require_permission(
                actor,
                ProtectedAction.MANAGE_AI_SETTINGS,
                production_mode=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
