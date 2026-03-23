"""
Unified API response models
"""
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response format.
    
    Generic type T represents the data type being returned.
    """
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Response message")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")
    meta: Optional[APIMetadata] = Field(None, description="Metadata about the request")


class APIMetadata(BaseModel):
    """
    API response metadata.
    """
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    page: Optional[int] = Field(None, description="Current page number (for paginated responses)")
    page_size: Optional[int] = Field(None, description="Number of items per page")
    total_items: Optional[int] = Field(None, description="Total number of items (for paginated responses)")
    total_pages: Optional[int] = Field(None, description="Total number of pages (for paginated responses)")


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.
    """
    page: int = Field(1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page (max 100)")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Sort order: 'asc' or 'desc'")


class PaginatedResponse(APIResponse[list[T]]):
    """
    Paginated API response.
    """
    data: list[T] = Field(..., description="List of items")
    meta: APIMetadata = Field(..., description="Pagination metadata")


class ErrorDetail(BaseModel):
    """
    Detailed error information.
    """
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error (for validation errors)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    """
    success: bool = Field(False, description="Always false for error responses")
    error: ErrorDetail = Field(..., description="Error details")
    meta: Optional[APIMetadata] = Field(None, description="Request metadata")


# Error codes
class ErrorCode:
    """Error code constants."""
    
    # General errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Authentication errors
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # User errors
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    USER_INACTIVE = "USER_INACTIVE"
    USER_LOCKED = "USER_LOCKED"
    
    # Project errors
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_ACCESS_DENIED = "PROJECT_ACCESS_DENIED"
    
    # Code review errors
    REVIEW_NOT_FOUND = "REVIEW_NOT_FOUND"
    REVIEW_IN_PROGRESS = "REVIEW_IN_PROGRESS"
    
    # GitHub errors
    GITHUB_TOKEN_INVALID = "GITHUB_TOKEN_INVALID"
    GITHUB_API_ERROR = "GITHUB_API_ERROR"
    GITHUB_RATE_LIMIT = "GITHUB_RATE_LIMIT"


def create_success_response(
    data: Any,
    message: Optional[str] = None,
    meta: Optional[APIMetadata] = None
) -> APIResponse[Any]:
    """
    Create a successful API response.
    
    Args:
        data: Response data
        message: Success message
        meta: Response metadata
        
    Returns:
        APIResponse with success=True
    """
    return APIResponse(
        success=True,
        data=data,
        message=message or "Request successful",
        meta=meta or APIMetadata()
    )


def create_error_response(
    error_code: str,
    message: str,
    field: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """
    Create an error API response.
    
    Args:
        error_code: Error code
        message: Error message
        field: Field that caused the error
        details: Additional error details
        
    Returns:
        ErrorResponse with success=False
    """
    return ErrorResponse(
        error=ErrorDetail(
            code=error_code,
            message=message,
            field=field,
            details=details
        ),
        meta=APIMetadata()
    )


def create_paginated_response(
    data: list[Any],
    page: int,
    page_size: int,
    total_items: int,
    message: Optional[str] = None
) -> PaginatedResponse[Any]:
    """
    Create a paginated API response.
    
    Args:
        data: List of items
        page: Current page number
        page_size: Number of items per page
        total_items: Total number of items
        message: Success message
        
    Returns:
        PaginatedResponse with metadata
    """
    total_pages = (total_items + page_size - 1) // page_size
    
    return PaginatedResponse(
        success=True,
        data=data,
        message=message or "Request successful",
        meta=APIMetadata(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages
        )
    )
