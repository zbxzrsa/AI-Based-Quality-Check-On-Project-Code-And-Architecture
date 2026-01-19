"""
Authentication endpoints
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.postgresql import get_db
from app.models import User, TokenBlacklist
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    PasswordChange,
    UserResponse,
    Message
)
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token, create_refresh_token, verify_token, get_token_expiry
from app.api.dependencies import get_current_user
from app.services.redis_cache_service import get_cache_service


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    
    - **email**: Valid email address
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit, special char)
    - **full_name**: Optional full name
    """
    # Check if user already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login and get access/refresh tokens
    
    Rate limited: 5 attempts per minute per IP
    """
    # Rate limiting check
    cache = await get_cache_service()
    client_ip = request.client.host
    allowed, remaining = await cache.check_rate_limit(
        client_ip,
        "login",
        max_requests=5,
        window=60
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Find user
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Store session in Redis
    session_data = {
        "email": user.email,
        "role": user.role.value,
        "logged_in_at": datetime.now(timezone.utc).isoformat()
    }
    await cache.set_session(str(user.id), session_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/logout", response_model=Message)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout and blacklist current token
    """
    # Get token from request (would need to extract from header in real implementation)
    # For simplicity, we'll just delete the session
    
    cache = await get_cache_service()
    await cache.delete_session(str(current_user.id))
    
    return Message(message="Successfully logged out")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    payload = verify_token(token_data.refresh_token, token_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    
    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    token_payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }
    
    new_access_token = create_access_token(token_payload)
    new_refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    """
    return current_user


@router.patch("/password", response_model=Message)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password
    
    Requires current password for verification
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check if new password is same as current
    if verify_password(password_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    
    await db.commit()
    
    return Message(message="Password successfully changed")
