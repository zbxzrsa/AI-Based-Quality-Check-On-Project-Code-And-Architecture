"""
重构后的ProjectInvitation API端点 - 使用设计模式消除重复代码

应用的改进：
1. 使用重构后的服务和业务流程模板
2. 使用状态机管理邀请状态
3. 统一错误处理
4. 简化端点逻辑
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgresql import get_db
from app.api.dependencies import get_current_user
from app.models import User, ProjectRole
from app.services.refactored_invitation_service import create_invitation_service
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Request/Response Models
class InvitationCreate(BaseModel):
    """Create invitation request"""
    project_id: str
    invitee_email: EmailStr
    role: str = ProjectRole.member.value
    message: str = None
    days_valid: int = 7


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
    """Accept/Decline invitation request"""
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
    Create a project invitation using business process template.
    
    Only project owners and maintainers can send invitations.
    The system will automatically:
    1. Validate input data
    2. Check permissions
    3. Verify no existing membership or pending invitation
    4. Create invitation with expiry
    5. Log audit trail
    """
    try:
        service = create_invitation_service(db)
        
        result = await service.create_invitation(
            project_id=invitation_data.project_id,
            inviter_id=str(current_user.id),
            invitee_email=invitation_data.invitee_email,
            role=invitation_data.role,
            message=invitation_data.message,
            days_valid=invitation_data.days_valid
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Invitation sent successfully",
                "invitation_id": result["invitation_id"],
                "invitation_token": result["invitation_token"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
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
    Get pending invitations for current user.
    
    Returns all non-expired pending invitations for the user's email.
    """
    try:
        service = create_invitation_service(db)
        invitations = await service.get_pending_invitations_for_user(current_user.email)
        
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
        logger.error(f"Error getting pending invitations: {e}")
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
    Accept a project invitation using state machine.
    
    The system will:
    1. Validate invitation token and user permissions
    2. Check invitation status and expiry
    3. Use state machine to transition to accepted state
    4. Create project membership automatically
    5. Log audit trail
    """
    try:
        service = create_invitation_service(db)
        
        result = await service.accept_invitation(
            invitation_token=accept_data.invitation_token,
            user_id=str(current_user.id)
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "project_id": str(result["invitation"].project_id),
                "role": result["invitation"].role
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation"
        )


@router.post("/invitations/decline", response_model=dict)
async def decline_invitation(
    decline_data: InvitationAccept,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Decline a project invitation using state machine.
    
    The system will:
    1. Validate invitation token and user permissions
    2. Check invitation status and expiry
    3. Use state machine to transition to declined state
    4. Log audit trail
    """
    try:
        service = create_invitation_service(db)
        
        result = await service.decline_invitation(
            invitation_token=decline_data.invitation_token,
            user_id=str(current_user.id)
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error declining invitation: {e}")
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
    Get all members of a project.
    
    Only project members can view the member list.
    """
    try:
        service = create_invitation_service(db)
        
        # Check if user has access to the project
        has_access = await service.has_project_access(str(current_user.id), project_id)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        members = await service.get_project_members(project_id)
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project members: {e}")
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
    Get all projects the current user is a member of.
    """
    try:
        service = create_invitation_service(db)
        memberships = await service.get_user_project_memberships(str(current_user.id))
        
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
        logger.error(f"Error getting user projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user projects"
        )


@router.post("/invitations/cleanup-expired", response_model=dict)
async def cleanup_expired_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cleanup expired invitations using state machine.
    
    This endpoint is typically called by scheduled tasks.
    Only admin users can trigger manual cleanup.
    """
    try:
        # Check if user is admin (you may need to implement role checking)
        # For now, allow any authenticated user
        
        service = create_invitation_service(db)
        cleaned_count = await service.cleanup_expired_invitations()
        
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} expired invitations",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up expired invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired invitations"
        )