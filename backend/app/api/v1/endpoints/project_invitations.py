"""
Project invitation endpoints for invitation-based access control
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.postgresql import get_db
from app.api.dependencies import get_current_user
from app.models import User, ProjectRole
from app.services.project_invitation_service import ProjectInvitationService


router = APIRouter()


# Request/Response Models
class InvitationCreate(BaseModel):
    """Create invitation request"""
    project_id: str
    invitee_email: EmailStr
    role: str = ProjectRole.member.value
    message: str = None


class InvitationResponse(BaseModel):
    """Invitation response"""
    id: str
    project_id: str
    project_name: str
    inviter_name: str
    inviter_email: str
    invitee_email: str
    role: str
    status: str
    message: str = None
    expires_at: str
    created_at: str


class InvitationAccept(BaseModel):
    """Accept invitation request"""
    invitation_token: str


class ProjectMemberResponse(BaseModel):
    """Project member response"""
    id: str
    project_id: str
    project_name: str
    user_id: str
    user_name: str
    user_email: str
    role: str
    joined_at: str


@router.post("/invitations", response_model=dict)
async def create_invitation(
    invitation_data: InvitationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a project invitation
    
    Only project owners and maintainers can send invitations
    """
    try:
        project_id = uuid.UUID(invitation_data.project_id)
        
        # Check if user has permission to invite (project owner or maintainer)
        has_access = await ProjectInvitationService.has_project_access(
            db, current_user.id, project_id
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to invite users to this project"
            )
        
        invitation = await ProjectInvitationService.create_invitation(
            db=db,
            project_id=project_id,
            inviter_id=current_user.id,
            invitee_email=invitation_data.invitee_email,
            role=invitation_data.role,
            message=invitation_data.message
        )
        
        return {
            "success": True,
            "message": "Invitation sent successfully",
            "invitation_id": str(invitation.id),
            "invitation_token": invitation.invitation_token
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invitation"
        )


@router.get("/invitations/pending", response_model=List[InvitationResponse])
async def get_pending_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get pending invitations for current user
    """
    try:
        invitations = await ProjectInvitationService.get_pending_invitations_for_user(
            db, current_user.email
        )
        
        return [
            InvitationResponse(
                id=str(invitation.id),
                project_id=str(invitation.project_id),
                project_name=invitation.project.name,
                inviter_name=invitation.inviter.full_name or invitation.inviter.email,
                inviter_email=invitation.inviter.email,
                invitee_email=invitation.invitee_email,
                role=invitation.role,
                status=invitation.status,
                message=invitation.message,
                expires_at=invitation.expires_at.isoformat(),
                created_at=invitation.created_at.isoformat()
            )
            for invitation in invitations
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending invitations"
        )


@router.post("/invitations/accept", response_model=dict)
async def accept_invitation(
    accept_data: InvitationAccept,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept a project invitation
    """
    try:
        member = await ProjectInvitationService.accept_invitation(
            db=db,
            invitation_token=accept_data.invitation_token,
            user_id=current_user.id
        )
        
        return {
            "success": True,
            "message": "Invitation accepted successfully",
            "project_id": str(member.project_id),
            "role": member.role
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation"
        )


@router.post("/invitations/decline", response_model=dict)
async def decline_invitation(
    accept_data: InvitationAccept,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Decline a project invitation
    """
    try:
        await ProjectInvitationService.decline_invitation(
            db=db,
            invitation_token=accept_data.invitation_token,
            user_id=current_user.id
        )
        
        return {
            "success": True,
            "message": "Invitation declined"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decline invitation"
        )


@router.get("/projects/{project_id}/members", response_model=List[ProjectMemberResponse])
async def get_project_members(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all members of a project
    
    Only project members can view the member list
    """
    try:
        project_uuid = uuid.UUID(project_id)
        
        # Check if user has access to the project
        has_access = await ProjectInvitationService.has_project_access(
            db, current_user.id, project_uuid
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        members = await ProjectInvitationService.get_project_members(db, project_uuid)
        
        return [
            ProjectMemberResponse(
                id=str(member.id),
                project_id=str(member.project_id),
                project_name=member.project.name,
                user_id=str(member.user_id),
                user_name=member.user.full_name or member.user.email,
                user_email=member.user.email,
                role=member.role,
                joined_at=member.joined_at.isoformat()
            )
            for member in members
        ]
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project members"
        )


@router.get("/my-projects", response_model=List[ProjectMemberResponse])
async def get_my_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all projects the current user is a member of
    """
    try:
        memberships = await ProjectInvitationService.get_user_project_memberships(
            db, current_user.id
        )
        
        return [
            ProjectMemberResponse(
                id=str(membership.id),
                project_id=str(membership.project_id),
                project_name=membership.project.name,
                user_id=str(membership.user_id),
                user_name=current_user.full_name or current_user.email,
                user_email=current_user.email,
                role=membership.role,
                joined_at=membership.joined_at.isoformat()
            )
            for membership in memberships
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user projects"
        )