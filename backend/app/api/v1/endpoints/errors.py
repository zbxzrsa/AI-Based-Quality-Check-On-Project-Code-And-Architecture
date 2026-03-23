"""
Client Error Reporting Endpoint

Receives error reports from frontend clients for centralized logging and monitoring.
Requirement 7.4: Client-side error reporting
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ClientErrorReport(BaseModel):
    """Client error report model"""
    type: str = Field(..., description="Error type (NETWORK_ERROR, TIMEOUT_ERROR, etc.)")
    message: str = Field(..., description="Error message")
    statusCode: Optional[int] = Field(None, description="HTTP status code if applicable")
    timestamp: str = Field(..., description="ISO 8601 timestamp when error occurred")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    userAgent: str = Field(..., description="User agent string")
    url: str = Field(..., description="URL where error occurred")


@router.post("/errors/client", status_code=201)
async def report_client_error(
    error_report: ClientErrorReport,
    request: Request
) -> Dict[str, str]:
    """
    Receive and log client-side errors
    
    This endpoint receives error reports from frontend clients and logs them
    to the backend logging system for centralized monitoring and analysis.
    
    Args:
        error_report: Client error report data
        request: FastAPI request object
        
    Returns:
        Success message with error ID
    """
    try:
        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        
        # Create structured log entry
        log_data = {
            "event": "client_error",
            "error_type": error_report.type,
            "message": error_report.message,
            "status_code": error_report.statusCode,
            "timestamp": error_report.timestamp,
            "client_url": error_report.url,
            "user_agent": error_report.userAgent,
            "client_ip": client_ip,
            "details": error_report.details,
            "server_timestamp": datetime.utcnow().isoformat(),
        }
        
        # Log the error
        logger.error(
            f"Client error reported: {error_report.type} - {error_report.message}",
            extra={"structured_data": log_data}
        )
        
        # Generate error ID for tracking
        error_id = f"client-{datetime.utcnow().timestamp()}"
        
        return {
            "status": "success",
            "message": "Error report received",
            "error_id": error_id
        }
        
    except Exception as e:
        logger.error(f"Failed to process client error report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process error report"
        )


@router.get("/errors/health", status_code=200)
async def error_reporting_health() -> Dict[str, str]:
    """
    Health check endpoint for error reporting service
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "error-reporting"
    }
