"""
Compatibility service for legacy project invitation imports.

The canonical implementation now lives in `refactored_invitation_service`.
This wrapper preserves the historical static API while delegating the
business flow to the refactored service so we only maintain one invitation
implementation.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectInvitation, ProjectMember, ProjectRole, User
from app.services.refactored_invitation_service import create_invitation_service


class ProjectInvitationService:
    """Legacy-compatible wrapper around the refactored invitation service."""

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        project_id: uuid.UUID,
        inviter_id: uuid.UUID,
        invitee_email: str,
        role: str = ProjectRole.member.value,
        message: Optional[str] = None,
        days_valid: int = 7,
    ) -> ProjectInvitation:
        service = create_invitation_service(db)
        result = await service.create_invitation(
            project_id=str(project_id),
            inviter_id=str(inviter_id),
            invitee_email=invitee_email,
            role=role,
            message=message,
            days_valid=days_valid,
        )
        if not result.get("success"):
            raise ValueError(result.get("error", "Failed to create invitation"))
        return result["invitation"]

    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        invitation_token: str,
        user_id: uuid.UUID,
    ) -> ProjectMember:
        service = create_invitation_service(db)
        result = await service.accept_invitation(
            invitation_token=invitation_token,
            user_id=str(user_id),
        )
        if not result.get("success"):
            raise ValueError(result.get("error", "Failed to accept invitation"))

        invitation = result["invitation"]
        member_result = await db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == invitation.project_id,
                    ProjectMember.user_id == user_id,
                )
            )
        )
        member = member_result.scalar_one_or_none()
        if member is None:
            raise ValueError("Invitation accepted but project membership was not created")
        return member

    @staticmethod
    async def decline_invitation(
        db: AsyncSession,
        invitation_token: str,
        user_id: uuid.UUID,
    ) -> ProjectInvitation:
        service = create_invitation_service(db)
        result = await service.decline_invitation(
            invitation_token=invitation_token,
            user_id=str(user_id),
        )
        if not result.get("success"):
            raise ValueError(result.get("error", "Failed to decline invitation"))
        return result["invitation"]

    @staticmethod
    async def get_project_member(
        db: AsyncSession,
        project_id: uuid.UUID,
        user_email: str,
    ) -> Optional[ProjectMember]:
        result = await db.execute(
            select(ProjectMember)
            .join(User, ProjectMember.user_id == User.id)
            .where(
                and_(
                    ProjectMember.project_id == project_id,
                    User.email == user_email,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_project_memberships(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[ProjectMember]:
        service = create_invitation_service(db)
        return await service.get_user_project_memberships(str(user_id))

    @staticmethod
    async def get_project_members(
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> List[ProjectMember]:
        service = create_invitation_service(db)
        return await service.get_project_members(str(project_id))

    @staticmethod
    async def get_pending_invitations_for_user(
        db: AsyncSession,
        user_email: str,
    ) -> List[ProjectInvitation]:
        service = create_invitation_service(db)
        return await service.get_pending_invitations_for_user(user_email)

    @staticmethod
    async def cleanup_expired_invitations(db: AsyncSession) -> int:
        service = create_invitation_service(db)
        return await service.cleanup_expired_invitations()

    @staticmethod
    async def has_project_access(
        db: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> bool:
        service = create_invitation_service(db)
        return await service.has_project_access(str(user_id), str(project_id))
