"""
Password hashing and verification utilities
Uses bcrypt for secure password hashing with configurable salt rounds
"""
from passlib.context import CryptContext
from app.core.config import settings
from app.utils.error_sanitizer import get_generic_password_error
import logging

logger = logging.getLogger(__name__)


# Password context for bcrypt hashing with configured rounds
# Requirement 2.1: Use bcrypt with minimum 12 salt rounds
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS
)


def validate_password_config() -> None:
    """
    Validate password hashing configuration on service startup
    
    Raises:
        ValueError: If bcrypt rounds is less than 12 (security requirement)
    """
    if settings.BCRYPT_ROUNDS < 12:
        raise ValueError(
            f"BCRYPT_ROUNDS must be at least 12 for security (Requirement 2.1). "
            f"Current value: {settings.BCRYPT_ROUNDS}"
        )


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt with configured salt rounds
    
    Security features:
    - Uses bcrypt algorithm (resistant to GPU attacks)
    - Configurable salt rounds (minimum 12, default 12)
    - Automatic salt generation
    - Secure error handling (Requirement 2.5)
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
        
    Raises:
        ValueError: If password hashing fails (with sanitized error message)
        
    Note:
        Requirement 2.1: Uses bcrypt with minimum 12 salt rounds
        Requirement 2.5: Returns generic error messages without exposing implementation details
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        # Log the actual error for debugging (server-side only)
        logger.error(f"Password hashing failed: {type(e).__name__}", exc_info=False)
        
        # Return sanitized error message to user
        # Never expose bcrypt details, salt info, or internal errors
        raise ValueError(get_generic_password_error()) from None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password
    
    Security features:
    - Uses constant-time comparison (prevents timing attacks)
    - Handles invalid hash gracefully
    - Never exposes error details to prevent information disclosure
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
        
    Note:
        Requirement 2.2: Uses constant-time comparison to prevent timing attacks
        Requirement 2.5: Handles errors gracefully without exposing implementation details
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Log the error type for debugging (server-side only)
        logger.warning(f"Password verification failed: {type(e).__name__}")
        
        # Return False instead of raising - don't expose error details
        # This prevents information disclosure about hash format, bcrypt version, etc.
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength requirements
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(char in special_chars for char in password):
        return False, "Password must contain at least one special character"
    
    return True, ""
