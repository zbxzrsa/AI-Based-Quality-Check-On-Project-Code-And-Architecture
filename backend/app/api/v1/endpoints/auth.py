"""
Authentication endpoints
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
def get_client_ip(request) -> str:
    """安全获取客户端IP地址"""
    if request.client and request.client.host:
        # 验证IP地址格式
        ip = request.client.host
        if ip and ip != "0.0.0.0":
            return ip
    
    # 检查代理头部
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 取第一个IP地址
        ip = forwarded_for.split(",")[0].strip()
        if ip and ip != "0.0.0.0":
            return ip
    
    # 检查真实IP头部
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip != "0.0.0.0":
        return real_ip
    
    return "unknown"  # 避免使用 0.0.0.0



from app.database.postgresql import get_db
from app.models import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    PasswordChange,
    UserResponse,
    Message
)
from app.utils.password import hash_password, verify_password, validate_password_strength
from app.utils.jwt import create_access_token, create_refresh_token, verify_token
from app.api.dependencies import get_current_user
from app.services.redis_cache_service import get_cache_service
from app.utils.error_sanitizer import get_generic_auth_error
from app.core.audit_service import UnifiedAuditService as AuditService
from app.services.account_lockout_service import AccountLockoutService

logger = logging.getLogger(__name__)


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
    logger.info(f"Registering user: {user_data.email}")
    # Validate password strength before hashing (Requirement 2.3)
    is_valid, error_message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Check if user already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password with secure error handling (Requirement 2.5)
    try:
        password_hash = hash_password(user_data.password)
    except ValueError as e:
        # hash_password already sanitizes the error message
        logger.error(f"Password hashing failed during registration for {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
    # Create new user with UUID
    user = User(
        id=str(uuid.uuid4()),  # Generate UUID for new user
        email=user_data.email,
        password_hash=password_hash,
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
    
    Security: Returns generic error message to prevent user enumeration (Requirement 2.5)
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
    
    # Check account lockout first (if user exists)
    if user:
        cache = await get_cache_service()
        lockout_service = AccountLockoutService(cache.redis)
        is_locked, unlock_time = await lockout_service.is_account_locked(user.id)
        
        if is_locked:
            logger.warning(f"Login attempt for locked account: {credentials.email}")
            await AuditService.log_auth_failure(
                db=db,
                email=credentials.email,
                ip_address=client_ip,
                user_agent=request.headers.get("User-Agent"),
                failure_reason="Account locked",
                user_id=user.id
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked. Please try again after {unlock_time.strftime('%Y-%m-%d %H:%M:%S UTC') if unlock_time else 'later'}"
            )
    
    # Use generic error message to prevent user enumeration (Requirement 2.5)
    # Don't reveal whether email exists or password is wrong
    if not user or not verify_password(credentials.password, user.password_hash):
        logger.warning(f"Failed login attempt for email: {credentials.email} from IP: {client_ip}")
        
        # Record failed attempt if user exists
        if user:
            cache = await get_cache_service()
            lockout_service = AccountLockoutService(cache.redis)
            should_lock, lockout_time = await lockout_service.record_failed_attempt(user.id)
            
            if should_lock:
                # Log account lockout
                await AuditService.log_auth_failure(
                    db=db,
                    email=credentials.email,
                    ip_address=client_ip,
                    user_agent=request.headers.get("User-Agent"),
                    failure_reason="Account locked due to too many failed attempts",
                    user_id=user.id
                )
        
        # Log authentication failure to audit log (Requirement 8.8)
        await AuditService.log_auth_failure(
            db=db,
            email=credentials.email,
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent"),
            failure_reason="Invalid credentials",
            user_id=user.id if user else None
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_generic_auth_error(),  # Generic: "Incorrect email or password"
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        # This is a different error - user exists but account is inactive
        logger.warning(f"Login attempt for inactive account: {credentials.email}")
        
        # Log authentication failure to audit log (Requirement 8.8)
        await AuditService.log_auth_failure(
            db=db,
            email=credentials.email,
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent"),
            failure_reason="Account inactive",
            user_id=user.id
        )
        
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
    
    # Reset failed login attempts on successful login
    lockout_service = AccountLockoutService(cache.redis)
    await lockout_service.reset_attempts(user.id)
    
    logger.info(f"Successful login for user: {user.email}")
    
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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token with token rotation
    
    Security Features:
    - Checks refresh token not revoked (Requirement 5.1)
    - Generates new token pair on refresh (Requirement 5.2)
    - Invalidates old refresh token (rotation) (Requirement 5.2)
    - Stores new refresh token metadata in Redis (Requirement 5.5)
    - Logs refresh failures to audit log (Requirement 8.8)
    
    Token rotation ensures that each refresh token can only be used once,
    preventing token replay attacks and limiting the impact of token theft.
    """
    # Get client IP for audit logging
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    
    # Verify refresh token signature and type
    payload = verify_token(token_data.refresh_token, token_type="refresh")
    
    if not payload:
        # Log token refresh failure (Requirement 8.8)
        await AuditService.log_token_refresh_failure(
            db=db,
            user_id=None,
            ip_address=client_ip,
            user_agent=user_agent,
            failure_reason="Invalid or expired refresh token"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if refresh token has been revoked (Requirement 5.1)
    old_jti = payload.get("jti")
    if old_jti:
        from app.utils.jwt import is_token_revoked
        if await is_token_revoked(old_jti):
            logger.warning(f"Attempted reuse of revoked refresh token: {old_jti}")
            
            # Log token refresh failure (Requirement 8.8)
            user_id_str = payload.get("sub")
            user_id = uuid.UUID(user_id_str) if user_id_str else None
            await AuditService.log_token_refresh_failure(
                db=db,
                user_id=user_id,
                ip_address=client_ip,
                user_agent=user_agent,
                failure_reason="Refresh token has been revoked"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    user_id = payload.get("sub")
    
    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        # Log token refresh failure (Requirement 8.8)
        user_id_uuid = uuid.UUID(user_id) if user_id else None
        await AuditService.log_token_refresh_failure(
            db=db,
            user_id=user_id_uuid,
            ip_address=client_ip,
            user_agent=user_agent,
            failure_reason="User not found or inactive"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Invalidate old refresh token (rotation) atomically before issuing new ones (Requirement 5.2)
    # This mitigates concurrent refresh race conditions
    if old_jti:
        from app.utils.jwt import revoke_token
        old_exp = payload.get("exp")
        if old_exp:
            old_expires_at = datetime.fromtimestamp(old_exp, tz=timezone.utc)
            revoked_successfully = await revoke_token(old_jti, old_expires_at)
            
            if not revoked_successfully:
                logger.warning(f"Concurrent refresh detected and blocked for token {old_jti}")
                user_id_uuid = uuid.UUID(user_id) if user_id else None
                await AuditService.log_token_refresh_failure(
                    db=db,
                    user_id=user_id_uuid,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    failure_reason="Refresh token already used (concurrent Request)"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token already used",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            logger.info(f"Revoked old refresh token {old_jti} for user {user.id} (rotation)")
            
    # Create new token pair (Requirement 5.2)
    token_payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }
    
    new_access_token = create_access_token(token_payload)
    new_refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Store new refresh token metadata in Redis (Requirement 5.5)
    # Decode the new refresh token to get its JTI and expiration
    from app.utils.jwt import decode_token
    new_payload = decode_token(new_refresh_token)
    if new_payload:
        new_jti = new_payload.get("jti")
        new_exp = new_payload.get("exp")
        
        if new_jti and new_exp:
            from app.database.redis_db import get_redis
            redis_client = await get_redis()
            
            refresh_metadata = {
                "user_id": str(user.id),
                "jti": new_jti,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": datetime.fromtimestamp(new_exp, tz=timezone.utc).isoformat()
            }
            
            # Store with TTL matching token expiration (7 days default)
            ttl_seconds = new_exp - int(datetime.now(timezone.utc).timestamp())
            if ttl_seconds > 0:
                import json
                await redis_client.set(
                    f"refresh_token:{new_jti}",
                    json.dumps(refresh_metadata),
                    ex=ttl_seconds
                )
                logger.info(f"Stored refresh token metadata for user {user.id}, JTI: {new_jti}")
    
    logger.info(f"Successfully refreshed tokens for user {user.id}")
    
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
    Security: Uses generic error messages to prevent information disclosure (Requirement 2.5)
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        logger.warning(f"Failed password change attempt for user: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength (Requirement 2.3)
    is_valid, error_message = validate_password_strength(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Check if new password is same as current
    if verify_password(password_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Hash new password with secure error handling (Requirement 2.5)
    try:
        new_password_hash = hash_password(password_data.new_password)
    except ValueError as e:
        # hash_password already sanitizes the error message
        logger.error(f"Password hashing failed during password change for user: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
    # Update password
    current_user.password_hash = new_password_hash
    
    await db.commit()
    
    logger.info(f"Password changed successfully for user: {current_user.email}")
    
    return Message(message="Password successfully changed")
