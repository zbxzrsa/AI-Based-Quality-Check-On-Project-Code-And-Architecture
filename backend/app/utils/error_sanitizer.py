"""
Error sanitization utilities for secure error handling
Prevents exposure of implementation details in error messages
"""
import re


# Patterns that should never appear in error messages
SENSITIVE_PATTERNS = [
    r'bcrypt',
    r'salt',
    r'rounds?',
    r'hash',
    r'algorithm',
    r'passlib',
    r'CryptContext',
    r'pwd_context',
    r'\$2[aby]\$',  # Bcrypt hash prefix
    r'ValueError',
    r'Exception',
    r'Traceback',
    r'File "',
    r'line \d+',
]


def sanitize_password_error(error_message: str) -> str:
    """
    Sanitize password-related error messages to prevent information disclosure
    
    Removes implementation details like:
    - Bcrypt algorithm details
    - Salt information
    - Hash formats
    - Internal exception details
    - Stack traces
    
    Args:
        error_message: Original error message
        
    Returns:
        Sanitized generic error message
        
    Note:
        Requirement 2.5: Return generic error messages without exposing implementation details
    """
    # Convert to lowercase for pattern matching
    error_lower = error_message.lower()
    
    # Check if error contains sensitive information
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, error_lower, re.IGNORECASE):
            # Return generic error message
            return "An error occurred during password processing. Please try again."
    
    # If no sensitive patterns found, return original message
    # (but still be cautious with what we allow through)
    return error_message


def get_generic_auth_error() -> str:
    """
    Get generic authentication error message
    
    Used for login failures to prevent user enumeration
    Does not reveal whether email exists or password is wrong
    
    Returns:
        Generic authentication error message
        
    Note:
        Requirement 2.5: Prevent user enumeration by not revealing if email exists
    """
    return "Incorrect email or password"


def get_generic_password_error() -> str:
    """
    Get generic password operation error message
    
    Used when password hashing or verification fails unexpectedly
    
    Returns:
        Generic password error message
        
    Note:
        Requirement 2.5: Handle password hashing failures gracefully
    """
    return "An error occurred during password processing. Please try again."


def sanitize_exception_message(exception: Exception) -> str:
    """
    Sanitize exception message for safe display to users
    
    Removes technical details and stack traces
    
    Args:
        exception: Exception to sanitize
        
    Returns:
        Sanitized error message safe for user display
    """
    error_str = str(exception)
    
    # If error contains sensitive patterns, return generic message
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, error_str, re.IGNORECASE):
            return get_generic_password_error()
    
    # Remove any stack trace information
    if 'Traceback' in error_str or 'File "' in error_str:
        return get_generic_password_error()
    
    # Return sanitized message
    return error_str


def is_safe_error_message(message: str) -> bool:
    """
    Check if an error message is safe to display to users
    
    Args:
        message: Error message to check
        
    Returns:
        True if message is safe, False if it contains sensitive information
    """
    message_lower = message.lower()
    
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return False
    
    return True
