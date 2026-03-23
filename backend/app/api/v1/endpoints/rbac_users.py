"""
RBAC User Management endpoints.
"""
from datetime import datetime, timezone
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.postgresql import get_db
from app.auth import (
    User,
    Role,
    Permission,
    AuthService,
    RBACService,
    AuditService,
    TokenPayload,
    require_role,
    require_permission,
)


router = APIRouter()


# Request/Response Models
class CreateUserRequest(BaseModel):
    """Create user request model."""
    username: str
    password: str
    role: str


class UpdateUserRoleRequest(BaseModel):
    """Update user role request model."""
    role: str


class UserResponse(BaseModel):
    """User response model."""
    id: str
    username: str
    role: str
    created_at: str
    updated_at: str
    last_login: Optional[str] = None
    is_active: bool


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    current_user: Annotated[TokenPayload, Depends(require_permission(Permission.CREATE_USER))],
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user (Admin only).
    
    - **username**: Unique username
    - **password**: User's password (will be hashed)
    - **role**: User role (ADMIN, PROGRAMMER, or VISITOR)
    
    Requires CREATE_USER permission (Admin only).
    """
    # Validate role
    if not RBACService.validate_role(user_data.role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {user_data.role}"
        )
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Hash password
    password_hash = AuthService.hash_password(user_data.password)
    
    # Create user
    now = datetime.now(timezone.utc)
    new_user = User(
        id=str(uuid.uuid4()),
        username=user_data.username,
        password_hash=password_hash,
        role=Role(user_data.role),
        created_at=now,
        updated_at=now,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log action
    ip_address = request.client.host if request.client else "0.0.0.0"
    AuditService.log_action(
        db=db,
        user_id=current_user.user_id,
        username=current_user.username,
        action="CREATE_USER",
        ip_address=ip_address,
        success=True,
        resource_type="User",
        resource_id=new_user.id
    )
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        role=new_user.role.value,
        created_at=new_user.created_at.isoformat(),
        updated_at=new_user.updated_at.isoformat(),
        last_login=new_user.last_login.isoformat() if new_user.last_login else None,
        is_active=new_user.is_active
    )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: Annotated[TokenPayload, Depends(require_permission(Permission.VIEW_USER))],
    db: AsyncSession = Depends(get_db)
):
    """
    List all users (Admin only).
    
    Requires VIEW_USER permission (Admin only).
    """
    users = db.query(User).all()
    
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            role=user.role.value,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
            is_active=user.is_active
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: Annotated[TokenPayload, Depends(require_permission(Permission.VIEW_USER))],
    db: AsyncSession = Depends(get_db)
):
    """
    Get user details by ID (Admin only).
    
    Requires VIEW_USER permission (Admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role.value,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
        is_active=user.is_active
    )


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    role_data: UpdateUserRoleRequest,
    current_user: Annotated[TokenPayload, Depends(require_role(Role.ADMIN))],
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Update user role (Admin only).
    
    - **role**: New role (ADMIN, PROGRAMMER, or VISITOR)
    
    Requires ADMIN role.
    """
    # Validate role
    if not RBACService.validate_role(role_data.role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role_data.role}"
        )
    
    # Assign role
    success = RBACService.assign_role(
        db=db,
        user_id=user_id,
        new_role=Role(role_data.role),
        assigned_by=current_user.user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update user role"
        )
    
    # Get updated user
    user = db.query(User).filter(User.id == user_id).first()
    
    # Log action
    ip_address = request.client.host if request.client else "0.0.0.0"
    AuditService.log_action(
        db=db,
        user_id=current_user.user_id,
        username=current_user.username,
        action="UPDATE_USER_ROLE",
        ip_address=ip_address,
        success=True,
        resource_type="User",
        resource_id=user_id
    )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role.value,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
        is_active=user.is_active
    )


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: str,
    current_user: Annotated[TokenPayload, Depends(require_permission(Permission.DELETE_USER))],
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user (Admin only).
    
    Requires DELETE_USER permission (Admin only).
    Prevents deletion of the last admin user.
    """
    # Get user to delete
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if this is the last admin
    if user.role == Role.ADMIN:
        admin_count = db.query(User).filter(User.role == Role.ADMIN).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin user"
            )
    
    # Invalidate all user sessions
    AuthService.invalidate_all_user_sessions(db, user_id)
    
    # Delete user
    db.delete(user)
    db.commit()
    
    # Log action
    ip_address = request.client.host if request.client else "0.0.0.0"
    AuditService.log_action(
        db=db,
        user_id=current_user.user_id,
        username=current_user.username,
        action="DELETE_USER",
        ip_address=ip_address,
        success=True,
        resource_type="User",
        resource_id=user_id
    )
    
    return MessageResponse(message=f"User {user.username} deleted successfully")
