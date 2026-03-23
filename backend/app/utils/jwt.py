"""
JWT token utilities
Handles token generation, validation, and management
"""
import logging
logger = logging.getLogger(__name__)

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import uuid

from app.database.redis_db import get_redis


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token with unique JTI for revocation support
    
    Access tokens are used for API authentication. Extended to 8 hours for
    better user experience while maintaining reasonable security.
    
    Args:
        data: Data to encode in token (typically user_id, email, role)
        expires_delta: Optional custom expiration time (default: 8 hours)
        
    Returns:
        Encoded JWT token string with:
        - Unique JTI (JWT ID) for revocation support
        - Type field set to "access"
        - Expiration time (exp)
        - All provided data fields
        
    Security Features:
        - HS256 algorithm with 256-bit secret
        - Unique JTI per token for revocation tracking
        - Type field prevents token confusion attacks
        - 8 hour expiration balances security and usability
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=8)  # Extended from 15 minutes to 8 hours
    
    # Generate unique JTI (JWT ID) for token revocation support
    jti = str(uuid.uuid4())
    
    to_encode.update({
        "exp": expire,
        "type": "access",  # Token type for validation
        "jti": jti
    })
    
    # Use main app settings for consistency
    from app.core.config import settings
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token with unique JTI for revocation support
    
    Refresh tokens are long-lived tokens (default 7 days) used to obtain new
    access tokens without re-authentication. They include a "type" field set
    to "refresh" to prevent token confusion attacks.
    
    Args:
        data: Data to encode in token (typically just user_id)
        expires_delta: Optional custom expiration time (default: 7 days)
        
    Returns:
        Encoded JWT refresh token string with:
        - Unique JTI (JWT ID) for revocation support
        - Type field set to "refresh"
        - Expiration time (exp)
        - All provided data fields
        
    Security Features:
        - HS256 algorithm with 256-bit secret
        - Unique JTI per token for revocation tracking
        - Type field prevents token confusion attacks
        - Longer expiration for user convenience
        - Should be stored securely (httpOnly cookie recommended)
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    
    # Generate unique JTI (JWT ID) for token revocation support
    jti = str(uuid.uuid4())
    
    to_encode.update({
        "exp": expire,
        "type": "refresh",  # Token type for validation
        "jti": jti
    })
    
    # Use main app settings for consistency
    from app.core.config import settings
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload if valid, None if invalid/expired
        
    Security Features:
        - Validates signature using secret key
        - Checks expiration time
        - Returns None for any validation failure
    """
    try:
        # Use main app settings for consistency
        from app.core.config import settings
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify token signature, expiration, and type
    
    This function provides comprehensive token validation including:
    - Signature verification using HS256 algorithm
    - Expiration time checking
    - Token type validation to prevent token confusion attacks
    
    Token type validation ensures that access tokens cannot be used as refresh
    tokens and vice versa, preventing token confusion attacks where an attacker
    might try to use a short-lived access token in place of a long-lived refresh
    token or vice versa.
    
    Args:
        token: JWT token string to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Decoded payload if valid and type matches, None otherwise
        
    Security Notes:
        - Returns None for any validation failure (signature, expiration, or type)
        - Token type mismatch is treated as a security violation
        - All tokens must include a "type" field in their payload
    """
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    # Validate token type matches expected type
    # This prevents token confusion attacks
    if payload.get("type") != token_type:
        return None
    
    return payload


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get expiration time from token
    
    Args:
        token: JWT token string
        
    Returns:
        Expiration datetime or None if invalid
    """
    payload = decode_token(token)
    if payload and "exp" in payload:
        return datetime.fromtimestamp(payload["exp"])
    return None


async def revoke_token(jti: str, expires_at: datetime) -> bool:
    """
    Revoke token by adding JTI to Redis blacklist atomically.
    
    Args:
        jti: JWT ID to revoke
        expires_at: Token expiration time (used to set TTL)
        
    Returns:
        True if the token was successfully added to the blacklist (first time),
        False if it was already in the blacklist (preventing concurrent reuse).
        
    The token is added to a Redis blacklist with TTL matching the token's
    expiration time. This ensures revoked tokens are automatically cleaned
    up after they would have expired anyway.
    """
    try:
        redis_client = await get_redis()
        
        # Calculate TTL in seconds (time until token expires)
        now = datetime.now(timezone.utc)
        ttl_seconds = int((expires_at - now).total_seconds())
        
        # Only add to blacklist if token hasn't already expired
        if ttl_seconds > 0:
            # Store in Redis with key pattern: revoked:jti:{jti}
            # Use SET with NX=True to atomically ensure we're the first to revoke it
            key = f"revoked:jti:{jti}"
            result = await redis_client.set(key, "1", ex=ttl_seconds, nx=True)
            return bool(result)
        return False
    except Exception as e:
        # Log error but don't raise - revocation failure shouldn't break the flow
        logger.warning(f"Failed to revoke token {jti}: {e}")
        return False


async def is_token_revoked(jti: str) -> bool:
    """
    Check if token JTI is in revocation list
    
    Args:
        jti: JWT ID to check
        
    Returns:
        True if token is revoked, False otherwise
    """
    try:
        redis_client = await get_redis()
        key = f"revoked:jti:{jti}"
        return await redis_client.exists(key) > 0
    except Exception as e:
        # Log error and fail open - if Redis is down, allow the token
        # This prioritizes availability over strict security
        logger.warning(f"Failed to check token revocation status: {e}")
        return False  # Fail open for availability


async def verify_token_with_revocation(
    token: str,
    token_type: str = "access"
) -> Optional[Dict[str, Any]]:
    """
    Verify token and check it hasn't been revoked
    
    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Decoded payload if valid and not revoked, None otherwise
    """
    # First verify token signature and type
    payload = verify_token(token, token_type)
    
    if payload is None:
        return None
    
    # Check if token has been revoked
    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        return None
    
    return payload
