"""
Standardized API response models for consistent error handling.
"""
from typing import Any, Dict, Generic, Optional, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field


T = TypeVar('T')


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    field: Optional[str] = Field(None, description="Field name for validation errors")


class ResponseMeta(BaseModel):
    """Response metadata."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    version: str = Field(default="1.0", description="API version")


class APIResponse(BaseModel, Generic[T]):
    """
    Standardized API response format.
    
    Example success response:
    {
        "status": "success",
        "data": {...},
        "meta": {
            "timestamp": "2024-01-15T10:00:00Z",
            "request_id": "abc-123"
        }
    }
    
    Example error response:
    {
        "status": "error",
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid input data",
            "details": {...}
        },
        "meta": {
            "timestamp": "2024-01-15T10:00:00Z",
            "request_id": "abc-123"
        }
    }
    """
    status: str = Field(..., description="Response status: 'success' or 'error'")
    data: Optional[T] = Field(None, description="Response data for successful requests")
    error: Optional[ErrorDetail] = Field(None, description="Error details for failed requests")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {"id": 1, "name": "Example"},
                "meta": {
                    "timestamp": "2024-01-15T10:00:00Z",
                    "request_id": "abc-123",
                    "version": "1.0"
                }
            }
        }


def success_response(
    data: Any,
    request_id: Optional[str] = None
) -> APIResponse:
    """Create a success response."""
    return APIResponse(
        status="success",
        data=data,
        meta=ResponseMeta(request_id=request_id)
    )


def error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    field: Optional[str] = None,
    request_id: Optional[str] = None
) -> APIResponse:
    """Create an error response."""
    return APIResponse(
        status="error",
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
            field=field
        ),
        meta=ResponseMeta(request_id=request_id)
    )


# Common error codes
class ErrorCodes:
    """Standard error codes."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
