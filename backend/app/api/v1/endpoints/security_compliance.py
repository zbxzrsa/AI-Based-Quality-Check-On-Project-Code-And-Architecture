#!/usr/bin/env python3
"""
Security Compliance API Endpoints
Provides REST API endpoints for the Security and Audit Compliance module.
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_security_compliance_service
from app.schemas.security_models import ComplianceReport
from app.services.security_compliance_service import SecurityComplianceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/security-compliance", tags=["security-compliance"], responses={404: {"description": "Not found"}}
)


def _sanitize_log_input(value: object, max_length: int = 80) -> str:
    """Sanitize user-controlled values before logging."""
    sanitized = str(value).replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    if len(sanitized) > max_length:
        return sanitized[:max_length] + "...[truncated]"
    return sanitized


class AuditRequest(BaseModel):
    """Request model for processing npm audit JSON."""

    project_id: str
    audit_json: dict[str, Any]
    commit_sha: str | None = None
    developer_id: str | None = None


class ComplianceSummary(BaseModel):
    """Summary of compliance status for multiple projects."""

    total_projects: int
    compliant_projects: int
    non_compliant_projects: int
    average_compliance_score: float
    risk_distribution: dict[str, int]


@router.post("/process-audit", response_model=ComplianceReport)
async def process_audit_report(
    request: AuditRequest,
    background_tasks: BackgroundTasks,
    service: SecurityComplianceService = Depends(get_security_compliance_service),
):
    """
    Process npm audit JSON and generate compliance report.

    Args:
        request: Audit request containing project ID and audit JSON
        background_tasks: FastAPI background tasks for async processing
        service: Security compliance service dependency

    Returns:
        ComplianceReport with vulnerability analysis and compliance score
    """
    try:
        safe_project_id = _sanitize_log_input(request.project_id)
        logger.info("Processing audit request", extra={"project_id": safe_project_id})

        # Process the audit report
        compliance_report = service.process_audit_report(request.project_id, request.audit_json)

        # Add additional metadata
        if request.commit_sha:
            compliance_report.scan_tools_used.append(f"commit:{request.commit_sha}")

        if request.developer_id:
            compliance_report.scan_tools_used.append(f"developer:{request.developer_id}")

        logger.info(
            "Audit processed successfully",
            extra={"project_id": safe_project_id, "compliance_score": compliance_report.compliance_score},
        )

        return compliance_report

    except Exception:
        logger.error("Error processing audit report", extra={"project_id": _sanitize_log_input(request.project_id)})
        raise HTTPException(status_code=500, detail="Failed to process audit report")


@router.get("/report/{project_id}", response_model=ComplianceReport)
async def get_compliance_report(
    project_id: str, service: SecurityComplianceService = Depends(get_security_compliance_service)
):
    """
    Get compliance report for a specific project.

    Args:
        project_id: Unique identifier for the project
        service: Security compliance service dependency

    Returns:
        ComplianceReport with current compliance status
    """
    try:
        report = service.get_compliance_report(project_id)

        if not report:
            raise HTTPException(status_code=404, detail=f"Compliance report not found for project {project_id}")

        logger.info("Retrieved compliance report", extra={"project_id": _sanitize_log_input(project_id)})
        return report

    except HTTPException:
        raise
    except Exception:
        logger.error("Error retrieving compliance report", extra={"project_id": _sanitize_log_input(project_id)})
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance report")


@router.get("/trends/{project_id}")
async def get_vulnerability_trends(
    project_id: str, days: int = 30, service: SecurityComplianceService = Depends(get_security_compliance_service)
):
    """
    Get vulnerability trends for a project over time.

    Args:
        project_id: Unique identifier for the project
        days: Number of days to look back (default: 30)
        service: Security compliance service dependency

    Returns:
        Dictionary containing vulnerability trends data
    """
    try:
        trends = service.get_vulnerability_trends(project_id, days)

        if not trends:
            raise HTTPException(status_code=404, detail=f"No vulnerability trends found for project {project_id}")

        logger.info(
            "Retrieved vulnerability trends",
            extra={"project_id": _sanitize_log_input(project_id), "days": days},
        )
        return trends

    except HTTPException:
        raise
    except Exception:
        logger.error("Error retrieving vulnerability trends", extra={"project_id": _sanitize_log_input(project_id)})
        raise HTTPException(status_code=500, detail="Failed to retrieve vulnerability trends")


@router.get("/summary", response_model=ComplianceSummary)
async def get_compliance_summary(service: SecurityComplianceService = Depends(get_security_compliance_service)):
    """
    Get compliance summary across all projects.

    Args:
        service: Security compliance service dependency

    Returns:
        ComplianceSummary with aggregate compliance metrics
    """
    try:
        # This would need to be implemented in the service
        # For now, return a placeholder implementation
        summary = ComplianceSummary(
            total_projects=0,
            compliant_projects=0,
            non_compliant_projects=0,
            average_compliance_score=0.0,
            risk_distribution={"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
        )

        logger.info("Retrieved compliance summary")
        return summary

    except Exception:
        logger.error("Error retrieving compliance summary")
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance summary")


@router.get("/projects")
async def list_projects_with_compliance(service: SecurityComplianceService = Depends(get_security_compliance_service)):
    """
    List all projects with their compliance scores.

    Args:
        service: Security compliance service dependency

    Returns:
        List of projects with compliance information
    """
    try:
        # This would need to be implemented in the service
        # For now, return a placeholder implementation
        projects = []

        logger.info("Retrieved list of projects with compliance scores")
        return projects

    except Exception:
        logger.error("Error retrieving projects list")
        raise HTTPException(status_code=500, detail="Failed to retrieve projects list")


@router.delete("/project/{project_id}")
async def delete_project_compliance_data(
    project_id: str, service: SecurityComplianceService = Depends(get_security_compliance_service)
):
    """
    Delete compliance data for a specific project.

    Args:
        project_id: Unique identifier for the project
        service: Security compliance service dependency

    Returns:
        Success message
    """
    try:
        # This would need to be implemented in the service
        # For now, return a placeholder implementation
        logger.info("Deleted compliance data", extra={"project_id": _sanitize_log_input(project_id)})
        return {"message": f"Compliance data deleted for project {project_id}"}

    except Exception:
        logger.error("Error deleting compliance data", extra={"project_id": _sanitize_log_input(project_id)})
        raise HTTPException(status_code=500, detail="Failed to delete compliance data")


@router.post("/bulk-process")
async def bulk_process_audit_reports(
    requests: list[AuditRequest],
    background_tasks: BackgroundTasks,
    service: SecurityComplianceService = Depends(get_security_compliance_service),
):
    """
    Process multiple audit reports in bulk.

    Args:
        requests: List of audit requests
        background_tasks: FastAPI background tasks for async processing
        service: Security compliance service dependency

    Returns:
        Summary of processing results
    """
    try:
        results = []
        success_count = 0
        error_count = 0

        for request in requests:
            try:
                report = service.process_audit_report(request.project_id, request.audit_json)
                results.append(
                    {
                        "project_id": request.project_id,
                        "status": "success",
                        "compliance_score": report.compliance_score,
                        "vulnerability_count": report.vulnerability_count,
                    }
                )
                success_count += 1
            except Exception as e:
                results.append({"project_id": request.project_id, "status": "error", "error": str(e)})
                error_count += 1

        logger.info(
            "Bulk processed audit reports",
            extra={
                "total_processed": len(requests),
                "success_count": success_count,
                "error_count": error_count,
            },
        )

        return {
            "total_processed": len(requests),
            "success_count": success_count,
            "error_count": error_count,
            "results": results,
        }

    except Exception:
        logger.error("Error in bulk audit processing")
        raise HTTPException(status_code=500, detail="Failed to process bulk audit reports")


# Example usage endpoints for testing
@router.post("/example-process")
async def example_process_audit(
    background_tasks: BackgroundTasks, service: SecurityComplianceService = Depends(get_security_compliance_service)
):
    """
    Example endpoint to demonstrate audit processing with sample data.
    """
    try:
        # Example npm audit JSON structure
        example_audit_json = {
            "vulnerabilities": {
                "axios": {
                    "name": "axios",
                    "severity": "high",
                    "title": "Server-Side Request Forgery in axios",
                    "overview": "axios is vulnerable to SSRF.",
                    "cwe": ["CWE-918"],
                    "cvss": {"score": 7.5},
                },
                "lodash": {
                    "name": "lodash",
                    "severity": "moderate",
                    "title": "Prototype Pollution in lodash",
                    "overview": "lodash is vulnerable to prototype pollution.",
                    "cwe": ["CWE-1321"],
                    "cvss": {"score": 6.1},
                },
                "minimist": {
                    "name": "minimist",
                    "severity": "low",
                    "title": "Prototype Pollution",
                    "overview": "Prototype pollution in minimist",
                    "cwe": ["CWE-1321"],
                    "cvss": {"score": 3.7},
                },
            }
        }

        # Process with example project
        compliance_report = service.process_audit_report("example-project", example_audit_json)

        logger.info(
            "Example audit processed",
            extra={"compliance_score": compliance_report.compliance_score},
        )

        return {"message": "Example audit processed successfully", "report": compliance_report}

    except Exception:
        logger.error("Error in example audit processing")
        raise HTTPException(status_code=500, detail="Failed to process example audit")


@router.get("/health")
async def security_compliance_health():
    """
    Health check endpoint for the security compliance module.
    """
    return {
        "status": "healthy",
        "module": "security-compliance",
        "features": [
            "npm audit processing",
            "compliance scoring",
            "vulnerability tracking",
            "Neo4j integration",
            "REST API endpoints",
        ],
    }
