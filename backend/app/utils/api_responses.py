"""
Unified API Response Builder

Provides consistent response formatting across all API endpoints:
- Success responses
- Error responses
- Paginated responses
- Validation error responses
- Standard HTTP status codes
"""
from typing import Any, Optional, Dict, List
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime


class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[Dict[str, Any]]] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.utcnow()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ResponseBuilder:
    """
    Builder for creating consistent API responses.
    
    Provides methods for common response patterns:
    - Success responses
    - Error responses
    - Paginated responses
    - Validation errors
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        meta: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_200_OK
    ) -> JSONResponse:
        """
        Create a success response.
        
        Args:
            data: Response data
            message: Success message
            meta: Additional metadata
            status_code: HTTP status code
            
        Returns:
            JSON response
            
        Example:
            return ResponseBuilder.success(
                data={"user_id": 123},
                message="User created successfully"
            )
        """
        response = APIResponse(
            success=True,
            message=message,
            data=data,
            meta=meta
        )
        return JSONResponse(
            content=response.dict(exclude_none=True),
            status_code=status_code
        )
    
    @staticmethod
    def error(
        message: str,
        errors: Optional[List[Dict[str, Any]]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        meta: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Create an error response.
        
        Args:
            message: Error message
            errors: List of detailed errors
            status_code: HTTP status code
            meta: Additional metadata
            
        Returns:
            JSON response
            
        Example:
            return ResponseBuilder.error(
                message="Validation failed",
                errors=[{"field": "email", "message": "Invalid email"}],
                status_code=422
            )
        """
        response = APIResponse(
            success=False,
            message=message,
            errors=errors,
            meta=meta
        )
        return JSONResponse(
            content=response.dict(exclude_none=True),
            status_code=status_code
        )
    
    @staticmethod
    def paginated(
        items: List[Any],
        page: int,
        page_size: int,
        total_items: int,
        message: str = "Success",
        additional_meta: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Create a paginated response.
        
        Args:
            items: List of items for current page
            page: Current page number (1-indexed)
            page_size: Number of items per page
            total_items: Total number of items
            message: Success message
            additional_meta: Additional metadata
            
        Returns:
            JSON response
            
        Example:
            return ResponseBuilder.paginated(
                items=users,
                page=1,
                page_size=20,
                total_items=100
            )
        """
        total_pages = (total_items + page_size - 1) // page_size
        
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
        meta = {"pagination": pagination.dict()}
        if additional_meta:
            meta.update(additional_meta)
        
        return ResponseBuilder.success(
            data=items,
            message=message,
            meta=meta
        )
    
    @staticmethod
    def created(
        data: Any,
        message: str = "Resource created successfully",
        meta: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Create a 201 Created response.
        
        Args:
            data: Created resource data
            message: Success message
            meta: Additional metadata
            
        Returns:
            JSON response
        """
        return ResponseBuilder.success(
            data=data,
            message=message,
            meta=meta,
            status_code=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def no_content(
        message: str = "Operation completed successfully"
    ) -> JSONResponse:
        """
        Create a 204 No Content response.
        
        Args:
            message: Success message
            
        Returns:
            JSON response
        """
        return ResponseBuilder.success(
            message=message,
            status_code=status.HTTP_204_NO_CONTENT
        )
    
    @staticmethod
    def not_found(
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[Any] = None
    ) -> JSONResponse:
        """
        Create a 404 Not Found response.
        
        Args:
            message: Error message
            resource_type: Type of resource not found
            resource_id: ID of resource not found
            
        Returns:
            JSON response
        """
        meta = {}
        if resource_type:
            meta["resource_type"] = resource_type
        if resource_id:
            meta["resource_id"] = str(resource_id)
        
        return ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            meta=meta if meta else None
        )
    
    @staticmethod
    def unauthorized(
        message: str = "Authentication required"
    ) -> JSONResponse:
        """
        Create a 401 Unauthorized response.
        
        Args:
            message: Error message
            
        Returns:
            JSON response
        """
        return ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(
        message: str = "Access forbidden",
        required_permission: Optional[str] = None
    ) -> JSONResponse:
        """
        Create a 403 Forbidden response.
        
        Args:
            message: Error message
            required_permission: Required permission that was missing
            
        Returns:
            JSON response
        """
        meta = {}
        if required_permission:
            meta["required_permission"] = required_permission
        
        return ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            meta=meta if meta else None
        )
    
    @staticmethod
    def validation_error(
        errors: List[Dict[str, Any]],
        message: str = "Validation failed"
    ) -> JSONResponse:
        """
        Create a 422 Unprocessable Entity response for validation errors.
        
        Args:
            errors: List of validation errors
            message: Error message
            
        Returns:
            JSON response
            
        Example:
            return ResponseBuilder.validation_error(
                errors=[
                    {"field": "email", "message": "Invalid email format"},
                    {"field": "password", "message": "Password too short"}
                ]
            )
        """
        return ResponseBuilder.error(
            message=message,
            errors=errors,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    
    @staticmethod
    def conflict(
        message: str = "Resource conflict",
        conflict_field: Optional[str] = None
    ) -> JSONResponse:
        """
        Create a 409 Conflict response.
        
        Args:
            message: Error message
            conflict_field: Field that caused the conflict
            
        Returns:
            JSON response
        """
        meta = {}
        if conflict_field:
            meta["conflict_field"] = conflict_field
        
        return ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            meta=meta if meta else None
        )
    
    @staticmethod
    def rate_limited(
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ) -> JSONResponse:
        """
        Create a 429 Too Many Requests response.
        
        Args:
            message: Error message
            retry_after: Seconds until rate limit resets
            
        Returns:
            JSON response
        """
        meta = {}
        if retry_after:
            meta["retry_after"] = retry_after
        
        response = ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            meta=meta if meta else None
        )
        
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        
        return response
    
    @staticmethod
    def server_error(
        message: str = "Internal server error",
        error_id: Optional[str] = None
    ) -> JSONResponse:
        """
        Create a 500 Internal Server Error response.
        
        Args:
            message: Error message
            error_id: Unique error identifier for tracking
            
        Returns:
            JSON response
        """
        meta = {}
        if error_id:
            meta["error_id"] = error_id
        
        return ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            meta=meta if meta else None
        )
    
    @staticmethod
    def service_unavailable(
        message: str = "Service temporarily unavailable",
        retry_after: Optional[int] = None
    ) -> JSONResponse:
        """
        Create a 503 Service Unavailable response.
        
        Args:
            message: Error message
            retry_after: Seconds until service is expected to be available
            
        Returns:
            JSON response
        """
        meta = {}
        if retry_after:
            meta["retry_after"] = retry_after
        
        response = ResponseBuilder.error(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            meta=meta if meta else None
        )
        
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        
        return response


# Convenience functions
def success_response(*args, **kwargs) -> JSONResponse:
    """Shorthand for ResponseBuilder.success()"""
    return ResponseBuilder.success(*args, **kwargs)


def error_response(*args, **kwargs) -> JSONResponse:
    """Shorthand for ResponseBuilder.error()"""
    return ResponseBuilder.error(*args, **kwargs)


def paginated_response(*args, **kwargs) -> JSONResponse:
    """Shorthand for ResponseBuilder.paginated()"""
    return ResponseBuilder.paginated(*args, **kwargs)
