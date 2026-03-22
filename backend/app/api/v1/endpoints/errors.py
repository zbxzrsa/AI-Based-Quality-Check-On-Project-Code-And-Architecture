"""
Client Error Reporting Endpoint

Receives error reports from frontend clients for centralized logging and monitoring.
Requirement 7.4: Client-side error reporting
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


def _sanitize_log_input(value: object, max_length: int = 120) -> str:
    """Mask control chars and truncate user-controlled data for logs."""
    sanitized = str(value).replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    if len(sanitized) > max_length:
        return sanitized[:max_length] + "...[truncated]"
    return sanitized


class ClientErrorReport(BaseModel):
    """Client error report model"""

    type: str = Field(..., description="Error type (NETWORK_ERROR, TIMEOUT_ERROR, etc.)")
    message: str = Field(..., description="Error message")
    statusCode: int | None = Field(None, description="HTTP status code if applicable")
    timestamp: str = Field(..., description="ISO 8601 timestamp when error occurred")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    userAgent: str = Field(..., description="User agent string")
    url: str = Field(..., description="URL where error occurred")


@router.post("/errors/client", status_code=201)
async def report_client_error(error_report: ClientErrorReport, request: Request) -> dict[str, str]:
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

        # Create structured log entry with sanitized values only
        log_data = {
            "event": "client_error",
            "error_type": _sanitize_log_input(error_report.type, max_length=64),
            "message": _sanitize_log_input(error_report.message),
            "status_code": error_report.statusCode,
            "timestamp": _sanitize_log_input(error_report.timestamp, max_length=64),
            "client_url": _sanitize_log_input(error_report.url),
            "user_agent": _sanitize_log_input(error_report.userAgent),
            "client_ip": _sanitize_log_input(client_ip, max_length=64),
            "has_details": bool(error_report.details),
            "server_timestamp": datetime.utcnow().isoformat(),
        }

        # Log the error
        logger.error("Client error reported", extra={"structured_data": log_data})

        # Generate error ID for tracking
        error_id = f"client-{datetime.utcnow().timestamp()}"

        return {"status": "success", "message": "Error report received", "error_id": error_id}

    except Exception:
        logger.error("Failed to process client error report")
        raise HTTPException(status_code=500, detail="Failed to process error report")


@router.get("/errors/health", status_code=200)
async def error_reporting_health() -> dict[str, str]:
    """
    Health check endpoint for error reporting service

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "error-reporting"}
