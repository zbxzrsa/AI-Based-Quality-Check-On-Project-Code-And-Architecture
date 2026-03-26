import sys
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.project_invitation_service import ProjectInvitationService


class ProjectInvitationServiceCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_invitation_returns_legacy_invitation_object(self):
        db = AsyncMock()
        project_id = uuid.uuid4()
        inviter_id = uuid.uuid4()
        invitation = SimpleNamespace(id=uuid.uuid4(), project_id=project_id)
        service = SimpleNamespace(
            create_invitation=AsyncMock(return_value={"success": True, "invitation": invitation})
        )

        with patch("app.services.project_invitation_service.create_invitation_service", return_value=service):
            result = await ProjectInvitationService.create_invitation(
                db=db,
                project_id=project_id,
                inviter_id=inviter_id,
                invitee_email="dev@example.com",
                role="member",
                message="hello",
                days_valid=14,
            )

        self.assertIs(result, invitation)
        service.create_invitation.assert_awaited_once_with(
            project_id=str(project_id),
            inviter_id=str(inviter_id),
            invitee_email="dev@example.com",
            role="member",
            message="hello",
            days_valid=14,
        )

    async def test_create_invitation_raises_value_error_when_refactored_service_fails(self):
        db = AsyncMock()
        service = SimpleNamespace(
            create_invitation=AsyncMock(return_value={"success": False, "error": "Pending invitation already exists"})
        )

        with patch("app.services.project_invitation_service.create_invitation_service", return_value=service):
            with self.assertRaisesRegex(ValueError, "Pending invitation already exists"):
                await ProjectInvitationService.create_invitation(
                    db=db,
                    project_id=uuid.uuid4(),
                    inviter_id=uuid.uuid4(),
                    invitee_email="dev@example.com",
                )

    async def test_accept_invitation_returns_member_after_refactored_acceptance(self):
        db = AsyncMock()
        user_id = uuid.uuid4()
        invitation = SimpleNamespace(project_id=uuid.uuid4())
        member = SimpleNamespace(project_id=invitation.project_id, user_id=user_id)
        db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: member))
        service = SimpleNamespace(
            accept_invitation=AsyncMock(return_value={"success": True, "invitation": invitation})
        )

        with patch("app.services.project_invitation_service.create_invitation_service", return_value=service):
            result = await ProjectInvitationService.accept_invitation(
                db=db,
                invitation_token="invite-token",
                user_id=user_id,
            )

        self.assertIs(result, member)
        service.accept_invitation.assert_awaited_once_with(
            invitation_token="invite-token",
            user_id=str(user_id),
        )
        db.execute.assert_awaited_once()

    async def test_accept_invitation_raises_when_membership_is_missing(self):
        db = AsyncMock()
        user_id = uuid.uuid4()
        invitation = SimpleNamespace(project_id=uuid.uuid4())
        db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
        service = SimpleNamespace(
            accept_invitation=AsyncMock(return_value={"success": True, "invitation": invitation})
        )

        with patch("app.services.project_invitation_service.create_invitation_service", return_value=service):
            with self.assertRaisesRegex(ValueError, "project membership was not created"):
                await ProjectInvitationService.accept_invitation(
                    db=db,
                    invitation_token="invite-token",
                    user_id=user_id,
                )

    async def test_decline_invitation_returns_legacy_invitation_object(self):
        db = AsyncMock()
        user_id = uuid.uuid4()
        invitation = SimpleNamespace(id=uuid.uuid4(), status="declined")
        service = SimpleNamespace(
            decline_invitation=AsyncMock(return_value={"success": True, "invitation": invitation})
        )

        with patch("app.services.project_invitation_service.create_invitation_service", return_value=service):
            result = await ProjectInvitationService.decline_invitation(
                db=db,
                invitation_token="invite-token",
                user_id=user_id,
            )

        self.assertIs(result, invitation)
        service.decline_invitation.assert_awaited_once_with(
            invitation_token="invite-token",
            user_id=str(user_id),
        )

    async def test_uuid_passthrough_helpers_keep_old_return_shapes(self):
        db = AsyncMock()
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()
        members = [SimpleNamespace(project_id=project_id)]
        memberships = [SimpleNamespace(user_id=user_id)]
        invitations = [SimpleNamespace(invitee_email="dev@example.com")]
        service = SimpleNamespace(
            get_project_members=AsyncMock(return_value=members),
            get_user_project_memberships=AsyncMock(return_value=memberships),
            get_pending_invitations_for_user=AsyncMock(return_value=invitations),
            cleanup_expired_invitations=AsyncMock(return_value=3),
            has_project_access=AsyncMock(return_value=True),
        )

        with patch("app.services.project_invitation_service.create_invitation_service", return_value=service):
            self.assertIs(await ProjectInvitationService.get_project_members(db, project_id), members)
            self.assertIs(await ProjectInvitationService.get_user_project_memberships(db, user_id), memberships)
            self.assertIs(
                await ProjectInvitationService.get_pending_invitations_for_user(db, "dev@example.com"),
                invitations,
            )
            self.assertEqual(await ProjectInvitationService.cleanup_expired_invitations(db), 3)
            self.assertTrue(await ProjectInvitationService.has_project_access(db, user_id, project_id))

        service.get_project_members.assert_awaited_once_with(str(project_id))
        service.get_user_project_memberships.assert_awaited_once_with(str(user_id))
        service.get_pending_invitations_for_user.assert_awaited_once_with("dev@example.com")
        service.cleanup_expired_invitations.assert_awaited_once_with()
        service.has_project_access.assert_awaited_once_with(str(user_id), str(project_id))


if __name__ == "__main__":
    unittest.main()
