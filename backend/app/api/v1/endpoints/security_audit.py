"""
Security Audit API Endpoints
RESTful API for security audit and compliance management
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from app.core.dependencies import get_current_user
from app.schemas.security_models import (
    SecurityScanResult,
    AuditLogEntry,
    ProjectQualityMetrics,
    QualityGrade,
    ScanTool
)
from app.services.security_audit_service import SecurityAuditService
from app.models.user import User

router = APIRouter(
    prefix="/security-audit",
    tags=["Security Audit"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/audit-log", response_model=dict)
async def create_audit_log(
    project_id: str,
    commit_sha: str,
    action: str = "security_scan",
    entity_type: str = "security_scan",
    entity_id: str = "",
    scan_result: Optional[SecurityScanResult] = None,
    changes: Optional[dict] = None,
    metadata: Optional[dict] = None,
    compliance_framework: Optional[str] = None,
    regulatory_requirements: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Create an audit log entry for security and compliance events
    
    Args:
        project_id: Project identifier
        commit_sha: Git commit SHA
        action: Action performed (scan, review, etc.)
        entity_type: Entity type (security_scan, pr_review, etc.)
        entity_id: Entity identifier
        scan_result: Security scan results
        changes: What changed
        metadata: Additional context
        compliance_framework: Compliance framework (GDPR, HIPAA, etc.)
        regulatory_requirements: Regulatory requirements addressed
        current_user: Current authenticated user
    """
    service = SecurityAuditService()
    
    try:
        audit_id = await service.create_audit_log_entry(
            project_id=project_id,
            commit_sha=commit_sha,
            developer_id=current_user.user_id,
            developer_email=current_user.email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            scan_result=scan_result,
            changes=changes,
            metadata=metadata,
            compliance_framework=compliance_framework,
            regulatory_requirements=regulatory_requirements
        )
        
        return {
            "success": True,
            "audit_id": audit_id,
            "message": "Audit log entry created successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create audit log entry: {str(e)}"
        )


@router.post("/scan-results", response_model=dict)
async def store_scan_results(
    project_id: str,
    commit_sha: str,
    scan_result: SecurityScanResult,
    current_user: User = Depends(get_current_user)
):
    """
    Store comprehensive security scan results and create audit log
    
    Args:
        project_id: Project identifier
        commit_sha: Git commit SHA
        scan_result: Complete security scan results
        current_user: Current authenticated user
    """
    service = SecurityAuditService()
    
    try:
        audit_id = await service.store_security_scan_result(
            project_id=project_id,
            commit_sha=commit_sha,
            scan_result=scan_result,
            developer_id=current_user.user_id,
            developer_email=current_user.email
        )
        
        return {
            "success": True,
            "audit_id": audit_id,
            "scan_id": scan_result.scan_id,
            "total_issues": scan_result.total_issues,
            "critical_issues": scan_result.critical_issues,
            "message": "Security scan results stored successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store scan results: {str(e)}"
        )


@router.get("/quality-metrics/{project_id}", response_model=ProjectQualityMetrics)
async def get_quality_metrics(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get project quality metrics based on recent security scans
    
    Args:
        project_id: Project identifier
        current_user: Current authenticated user
    """
    service = SecurityAuditService()
    
    try:
        metrics = await service.get_project_quality_metrics(project_id)
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quality metrics: {str(e)}"
        )


@router.get("/quality-grade/{project_id}", response_model=dict)
async def get_quality_grade(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get quality grade and metrics for dashboard display
    
    Args:
        project_id: Project identifier
        current_user: Current authenticated user
    """
    service = SecurityAuditService()
    
    try:
        grade_data = await service.get_quality_grade_for_dashboard(project_id)
        return grade_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quality grade: {str(e)}"
        )


@router.get("/audit-trail/{project_id}", response_model=List[dict])
async def get_audit_trail(
    project_id: str,
    limit: int = Query(50, ge=1, le=1000),
    entity_type: Optional[str] = None,
    developer_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get audit trail for a project with filtering options
    
    Args:
        project_id: Project identifier
        limit: Maximum number of entries to return
        entity_type: Filter by entity type
        developer_id: Filter by developer
        start_date: Filter from this date
        end_date: Filter to this date
        current_user: Current authenticated user
    """
    service = SecurityAuditService()
    
    try:
        audit_trail = await service.get_audit_trail(
            project_id=project_id,
            limit=limit,
            entity_type=entity_type,
            developer_id=developer_id,
            start_date=start_date,
            end_date=end_date
        )
        return audit_trail
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit trail: {str(e)}"
        )


@router.get("/compliance-report/{project_id}", response_model=dict)
async def get_compliance_report(
    project_id: str,
    days_back: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a comprehensive security compliance report
    
    Args:
        project_id: Project identifier
        days_back: Number of days to look back
        current_user: Current authenticated user
    """
    service = SecurityAuditService()
    
    try:
        report = await service.get_security_compliance_report(
            project_id=project_id,
            days_back=days_back
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate compliance report: {str(e)}"
        )


@router.get("/scan-summary/{project_id}", response_model=dict)
async def get_scan_summary(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get summary of recent security scans for a project
    
    Args:
        project_id: Project identifier
        current_user: Current authenticated user
    """
    service = SecurityAuditService()
    
    try:
        # Get recent scan data
        recent_scan_query = """
        MATCH (p:Project {projectId: $projectId})-[:HAS_AUDIT_LOG]->(audit:AuditLog)
        WHERE audit.entityType = 'security_scan'
        AND audit.timestamp >= datetime() - duration({days: 7})
        AND audit.scanData IS NOT NULL
        RETURN audit.scanData AS scanData, audit.timestamp AS timestamp, audit.action AS action
        ORDER BY audit.timestamp DESC
        LIMIT 5
        """

        from app.database.neo4j_db import get_neo4j_driver
        from app.core.config import settings
        
        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(recent_scan_query, {"projectId": project_id})
            records = await result.data()

        # Process scan summary
        scan_summary = []
        total_issues = 0
        critical_issues = 0
        high_issues = 0
        
        for record in records:
            scan_data = record.get("scanData", {})
            scan_summary.append({
                "timestamp": record.get("timestamp"),
                "action": record.get("action"),
                "tool": scan_data.get("tool"),
                "total_issues": scan_data.get("totalIssues", 0),
                "critical_issues": scan_data.get("criticalIssues", 0),
                "high_issues": scan_data.get("highIssues", 0)
            })
            
            total_issues += scan_data.get("totalIssues", 0)
            critical_issues += scan_data.get("criticalIssues", 0)
            high_issues += scan_data.get("highIssues", 0)

        # Get quality metrics
        metrics = await service.get_project_quality_metrics(project_id)

        return {
            "project_id": project_id,
            "scan_summary": scan_summary,
            "total_issues_found": total_issues,
            "critical_issues_found": critical_issues,
            "high_issues_found": high_issues,
            "quality_metrics": {
                "quality_grade": metrics.quality_grade.value,
                "grade_score": metrics.grade_score,
                "compliance_score": metrics.compliance_score,
                "frameworks_compliant": metrics.frameworks_compliant
            },
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scan summary: {str(e)}"
        )


@router.get("/tools/{project_id}", response_model=List[str])
async def get_used_tools(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get list of security scanning tools used for a project
    
    Args:
        project_id: Project identifier
        current_user: Current authenticated user
    """
    service = SecurityAuditService()
    
    try:
        # Query to get distinct tools used
        cypher_query = """
        MATCH (p:Project {projectId: $projectId})-[:HAS_AUDIT_LOG]->(audit:AuditLog)
        WHERE audit.entityType = 'security_scan'
        AND audit.scanData IS NOT NULL
        RETURN DISTINCT audit.scanData.tool AS tool
        ORDER BY tool
        """

        from app.database.neo4j_db import get_neo4j_driver
        from app.core.config import settings
        
        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(cypher_query, {"projectId": project_id})
            records = await result.data()

        tools = [record.get("tool") for record in records if record.get("tool")]
        return tools
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get used tools: {str(e)}"
        )


@router.delete("/audit-log/{audit_id}", response_model=dict)
async def delete_audit_log(
    audit_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete an audit log entry (for cleanup or data retention)
    
    Args:
        audit_id: Audit log entry ID
        current_user: Current authenticated user
    """
    try:
        # Note: In a real implementation, you might want to implement soft deletion
        # or check permissions before deletion. For now, we'll just return a success message.
        
        return {
            "success": True,
            "audit_id": audit_id,
            "message": "Audit log entry marked for deletion (implementation pending)"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete audit log: {str(e)}"
        )
