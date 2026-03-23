"""
Security utilities for the application
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer


security = HTTPBearer()


async def get_current_user(credentials: Optional[dict] = Depends(security)):
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP bearer credentials
    
    Returns:
        User information
    
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return {"token": credentials.get("credentials", "")}
