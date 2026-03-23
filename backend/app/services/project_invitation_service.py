"""
Project invitation service for managing project access through invitations
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ProjectInvitation, ProjectMember, User, Project, 
    InvitationStatus, ProjectRole
)
from app.core.audit_service import UnifiedAuditService as AuditService


class ProjectInvitationService:
    """Service for managing project invitations and memberships"""
    
    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        project_id: uuid.UUID,
        inviter_id: uuid.UUID,
        invitee_email: str,
        role: str = ProjectRole.member.value,
        message: Optional[str] = None,
        days_valid: int = 7
    ) -> ProjectInvitation:
        """
        Create a new project invitation
        
        Args:
            db: Database session
            project_id: Project to invite to
            inviter_id: User sending the invitation
            invitee_email: Email of user to invite
            role: Role to assign (member, maintainer)
            message: Optional invitation message
            days_valid: Days until invitation expires
            
        Returns:
            Created ProjectInvitation
        """
        # Check if user is already a member
        existing_member = await ProjectInvitationService.get_project_member(
            db, project_id, invitee_email
        )
        if existing_member:
            raise ValueError("User is already a member of this project")
        
        # Check for existing pending invitation
        existing_invitation = await db.execute(
            select(ProjectInvitation).where(
                and_(
                    ProjectInvitation.project_id == project_id,
                    ProjectInvitation.invitee_email == invitee_email,
                    ProjectInvitation.status == InvitationStatus.pending.value
                )
            )
        )
        if existing_invitation.scalar_one_or_none():
            raise ValueError("Pending invitation already exists for this user")
        
        # Create invitation
        invitation = ProjectInvitation.create_with_expiry(
            project_id=project_id,
            inviter_id=inviter_id,
            invitee_email=invitee_email,
            role=role,
            message=message,
            days_valid=days_valid
        )
        
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        
        # Log invitation creation
        await AuditService.log_project_invitation_sent(
            db=db,
            project_id=project_id,
            inviter_id=inviter_id,
            invitee_email=invitee_email,
            role=role
        )
        
        return invitation
    
    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        invitation_token: str,
        user_id: uuid.UUID
    ) -> ProjectMember:
        """
        Accept a project invitation
        
        Args:
            db: Database session
            invitation_token: Invitation token
            user_id: User accepting the invitation
            
        Returns:
            Created ProjectMember
        """
        # Get invitation
        result = await db.execute(
            select(ProjectInvitation).where(
                ProjectInvitation.invitation_token == invitation_token
            ).options(selectinload(ProjectInvitation.project))
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        if not invitation.can_be_accepted():
            raise ValueError("Invitation cannot be accepted (expired or already processed)")
        
        # Get user to verify email matches
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or user.email != invitation.invitee_email:
            raise ValueError("User email does not match invitation")
        
        # Check if user is already a member
        existing_member = await db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == invitation.project_id,
                    ProjectMember.user_id == user_id
                )
            )
        )
        if existing_member.scalar_one_or_none():
            raise ValueError("User is already a member of this project")
        
        # Create project membership
        member = ProjectMember(
            project_id=invitation.project_id,
            user_id=user_id,
            role=invitation.role
        )
        
        # Update invitation status
        invitation.status = InvitationStatus.accepted.value
        invitation.invitee_id = user_id
        invitation.accepted_at = datetime.now(timezone.utc)
        
        db.add(member)
        await db.commit()
        await db.refresh(member)
        
        # Log invitation acceptance
        await AuditService.log_project_invitation_accepted(
            db=db,
            project_id=invitation.project_id,
            user_id=user_id,
            role=invitation.role
        )
        
        return member
    
    @staticmethod
    async def decline_invitation(
        db: AsyncSession,
        invitation_token: str,
        user_id: uuid.UUID
    ) -> ProjectInvitation:
        """
        Decline a project invitation
        
        Args:
            db: Database session
            invitation_token: Invitation token
            user_id: User declining the invitation
            
        Returns:
            Updated ProjectInvitation
        """
        # Get invitation
        result = await db.execute(
            select(ProjectInvitation).where(
                ProjectInvitation.invitation_token == invitation_token
            )
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        if invitation.status != InvitationStatus.pending.value:
            raise ValueError("Invitation has already been processed")
        
        # Get user to verify email matches
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or user.email != invitation.invitee_email:
            raise ValueError("User email does not match invitation")
        
        # Update invitation status
        invitation.status = InvitationStatus.declined.value
        invitation.invitee_id = user_id
        
        await db.commit()
        
        return invitation
    
    @staticmethod
    async def get_project_member(
        db: AsyncSession,
        project_id: uuid.UUID,
        user_email: str
    ) -> Optional[ProjectMember]:
        """Get project member by email"""
        result = await db.execute(
            select(ProjectMember)
            .join(User, ProjectMember.user_id == User.id)
            .where(
                and_(
                    ProjectMember.project_id == project_id,
                    User.email == user_email
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_project_memberships(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> List[ProjectMember]:
        """Get all project memberships for a user"""
        result = await db.execute(
            select(ProjectMember)
            .where(ProjectMember.user_id == user_id)
            .options(selectinload(ProjectMember.project))
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_project_members(
        db: AsyncSession,
        project_id: uuid.UUID
    ) -> List[ProjectMember]:
        """Get all members of a project"""
        result = await db.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .options(selectinload(ProjectMember.user))
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_pending_invitations_for_user(
        db: AsyncSession,
        user_email: str
    ) -> List[ProjectInvitation]:
        """Get pending invitations for a user by email"""
        result = await db.execute(
            select(ProjectInvitation)
            .where(
                and_(
                    ProjectInvitation.invitee_email == user_email,
                    ProjectInvitation.status == InvitationStatus.pending.value,
                    ProjectInvitation.expires_at > datetime.now(timezone.utc)
                )
            )
            .options(
                selectinload(ProjectInvitation.project),
                selectinload(ProjectInvitation.inviter)
            )
        )
        return result.scalars().all()
    
    @staticmethod
    async def cleanup_expired_invitations(db: AsyncSession) -> int:
        """Mark expired invitations as expired"""
        result = await db.execute(
            select(ProjectInvitation).where(
                and_(
                    ProjectInvitation.status == InvitationStatus.pending.value,
                    ProjectInvitation.expires_at <= datetime.now(timezone.utc)
                )
            )
        )
        expired_invitations = result.scalars().all()
        
        for invitation in expired_invitations:
            invitation.status = InvitationStatus.expired.value
        
        await db.commit()
        return len(expired_invitations)
    
    @staticmethod
    async def has_project_access(
        db: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID
    ) -> bool:
        """Check if user has access to a project"""
        # Check if user is project owner
        project_result = await db.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.owner_id == user_id
                )
            )
        )
        if project_result.scalar_one_or_none():
            return True
        
        # Check if user is project member
        member_result = await db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id
                )
            )
        )
        return member_result.scalar_one_or_none() is not None