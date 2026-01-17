"""
Security Audit Service
Handles storage and retrieval of security scan results and audit logs in Neo4j
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from app.database.neo4j_db import get_neo4j_driver
from app.schemas.security_models import (
    SecurityScanResult,
    AuditLogEntry,
    ProjectQualityMetrics,
    QualityGrade,
    ScanTool
)
from app.core.config import settings


class SecurityAuditService:
    """
    Service for managing security audit logs and compliance data in Neo4j
    """

    async def create_audit_log_entry(
        self,
        project_id: str,
        commit_sha: str,
        developer_id: Optional[str] = None,
        developer_email: Optional[str] = None,
        action: str = "security_scan",
        entity_type: str = "security_scan",
        entity_id: str = "",
        scan_result: Optional[SecurityScanResult] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        compliance_framework: Optional[str] = None,
        regulatory_requirements: Optional[List[str]] = None
    ) -> str:
        """
        Create an audit log entry in Neo4j linked to Commit and Developer

        Args:
            project_id: Project identifier
            commit_sha: Git commit SHA
            developer_id: Developer/user identifier
            developer_email: Developer email
            action: Action performed (scan, review, etc.)
            entity_type: Entity type (security_scan, pr_review, etc.)
            entity_id: Entity identifier
            scan_result: Security scan results
            changes: What changed
            metadata: Additional context
            compliance_framework: Compliance framework (GDPR, HIPAA, etc.)
            regulatory_requirements: Regulatory requirements addressed

        Returns:
            Audit log entry ID
        """
        audit_id = str(uuid4())

        # Prepare scan result data for Neo4j storage
        scan_data = None
        if scan_result:
            scan_data = {
                "scan_id": scan_result.scan_id,
                "tool": scan_result.tool.value,
                "target": scan_result.target,
                "timestamp": scan_result.timestamp.isoformat(),
                "duration_seconds": scan_result.duration_seconds,
                "total_issues": scan_result.total_issues,
                "critical_issues": scan_result.critical_issues,
                "high_issues": scan_result.high_issues,
                "medium_issues": scan_result.medium_issues,
                "low_issues": scan_result.low_issues,
                "info_issues": scan_result.info_issues,
                "scan_version": scan_result.scan_version,
                "bandit_issues_count": len(scan_result.bandit_issues),
                "trufflehog_findings_count": len(scan_result.trufflehog_findings),
                "safety_vulnerabilities_count": len(scan_result.safety_vulnerabilities),
                "pip_audit_count": len(scan_result.pip_audit_vulnerabilities),
                "npm_audit_count": len(scan_result.npm_audit_vulnerabilities),
                "eslint_issues_count": len(scan_result.eslint_issues),
                "codeql_alerts_count": len(scan_result.codeql_alerts),
                "trivy_vulnerabilities_count": len(scan_result.trivy_vulnerabilities)
            }

        # Cypher query to create audit log node
        cypher_query = """
        MATCH (p:Project {projectId: $projectId})

        // Create or match Commit node
        MERGE (c:Commit {sha: $commitSha})
        SET c.projectId = $projectId,
            c.createdAt = datetime()

        // Create audit log entry
        CREATE (audit:AuditLog {
            auditId: $auditId,
            action: $action,
            entityType: $entityType,
            entityId: $entityId,
            timestamp: datetime($timestamp),
            complianceFramework: $complianceFramework
        })

        // Link to project and commit
        CREATE (p)-[:HAS_AUDIT_LOG]->(audit)
        CREATE (c)-[:HAS_AUDIT_LOG]->(audit)

        // Link to developer if provided
        FOREACH (_ IN CASE WHEN $developerId IS NOT NULL THEN [1] ELSE [] END |
            MERGE (dev:Developer {developerId: $developerId})
            SET dev.email = $developerEmail,
                dev.lastSeen = datetime($timestamp)
            CREATE (audit)-[:PERFORMED_BY]->(dev)
        )

        // Add scan result data if provided
        FOREACH (_ IN CASE WHEN $scanData IS NOT NULL THEN [1] ELSE [] END |
            SET audit.scanData = $scanData,
                audit.totalIssues = $scanData.total_issues,
                audit.criticalIssues = $scanData.critical_issues,
                audit.highIssues = $scanData.high_issues
        )

        // Add changes and metadata
        SET audit.changes = $changes,
            audit.metadata = $metadata,
            audit.regulatoryRequirements = $regulatoryRequirements

        RETURN audit.auditId AS auditId
        """

        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(cypher_query, {
                "projectId": project_id,
                "commitSha": commit_sha,
                "auditId": audit_id,
                "action": action,
                "entityType": entity_type,
                "entityId": entity_id,
                "timestamp": datetime.utcnow().isoformat(),
                "developerId": developer_id,
                "developerEmail": developer_email,
                "scanData": scan_data,
                "changes": changes or {},
                "metadata": metadata or {},
                "complianceFramework": compliance_framework,
                "regulatoryRequirements": regulatory_requirements or []
            })

            record = await result.single()
            return record["auditId"] if record else audit_id

    async def store_security_scan_result(
        self,
        project_id: str,
        commit_sha: str,
        scan_result: SecurityScanResult,
        developer_id: Optional[str] = None,
        developer_email: Optional[str] = None
    ) -> str:
        """
        Store comprehensive security scan results and create audit log

        Args:
            project_id: Project identifier
            commit_sha: Git commit SHA
            scan_result: Complete security scan results
            developer_id: Developer who triggered the scan
            developer_email: Developer email

        Returns:
            Audit log entry ID
        """
        # Calculate summary stats
        scan_result.calculate_summary_stats()

        # Prepare detailed changes for audit
        changes = {
            "scan_tool": scan_result.tool.value,
            "scan_target": scan_result.target,
            "issues_found": scan_result.total_issues,
            "critical_issues": scan_result.critical_issues,
            "high_issues": scan_result.high_issues,
            "scan_duration": scan_result.duration_seconds
        }

        # Add tool-specific issue counts
        if scan_result.bandit_issues:
            changes["bandit_issues"] = len(scan_result.bandit_issues)
        if scan_result.trufflehog_findings:
            changes["secrets_found"] = len(scan_result.trufflehog_findings)
        if scan_result.safety_vulnerabilities:
            changes["dependency_vulnerabilities"] = len(scan_result.safety_vulnerabilities)

        # Metadata for compliance tracking
        metadata = {
            "scan_version": scan_result.scan_version,
            "scan_config": scan_result.scan_config,
            "raw_output_available": scan_result.raw_output is not None
        }

        # Determine compliance framework based on scan tool
        compliance_framework = None
        regulatory_requirements = []

        if scan_result.tool == ScanTool.TRUFFLEHOG:
            compliance_framework = "GDPR"
            regulatory_requirements = ["data_protection", "access_control"]
        elif scan_result.tool in [ScanTool.SAFETY, ScanTool.PIP_AUDIT, ScanTool.NPM_AUDIT]:
            compliance_framework = "OWASP"
            regulatory_requirements = ["secure_dependencies", "vulnerability_management"]
        elif scan_result.tool == ScanTool.BANDIT:
            compliance_framework = "OWASP"
            regulatory_requirements = ["secure_coding", "sast_scanning"]

        return await self.create_audit_log_entry(
            project_id=project_id,
            commit_sha=commit_sha,
            developer_id=developer_id,
            developer_email=developer_email,
            action=f"security_scan_{scan_result.tool.value}",
            entity_type="security_scan",
            entity_id=scan_result.scan_id,
            scan_result=scan_result,
            changes=changes,
            metadata=metadata,
            compliance_framework=compliance_framework,
            regulatory_requirements=regulatory_requirements
        )

    async def get_project_quality_metrics(
        self,
        project_id: str
    ) -> ProjectQualityMetrics:
        """
        Calculate and return project quality metrics based on recent security scans

        Args:
            project_id: Project identifier

        Returns:
            Project quality metrics
        """
        # Query to get recent security scan data
        cypher_query = """
        MATCH (p:Project {projectId: $projectId})-[:HAS_AUDIT_LOG]->(audit:AuditLog)
        WHERE audit.entityType = 'security_scan'
        AND audit.timestamp >= datetime() - duration({days: 30})
        AND audit.scanData IS NOT NULL

        WITH audit
        ORDER BY audit.timestamp DESC
        LIMIT 10

        RETURN
            collect(audit.scanData.totalIssues) AS totalIssues,
            collect(audit.scanData.criticalIssues) AS criticalIssues,
            collect(audit.scanData.highIssues) AS highIssues,
            collect(audit.timestamp) AS scanTimestamps,
            max(audit.timestamp) AS lastScanDate
        """

        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(cypher_query, {"projectId": project_id})
            record = await result.single()

            if not record:
                # Return default metrics if no scans found
                return ProjectQualityMetrics(
                    project_id=project_id,
                    last_scan_date=None,
                    quality_grade=QualityGrade.F,
                    grade_score=0
                )

            # Extract data from recent scans
            total_issues_list = record.get("totalIssues", [])
            critical_issues_list = record.get("criticalIssues", [])
            high_issues_list = record.get("highIssues", [])
            scan_timestamps = record.get("scanTimestamps", [])
            last_scan_date = record.get("lastScanDate")

            # Use most recent scan for current metrics
            current_total = total_issues_list[0] if total_issues_list else 0
            current_critical = critical_issues_list[0] if critical_issues_list else 0
            current_high = high_issues_list[0] if high_issues_list else 0

            # Calculate compliance score (inverse of issues, max 100)
            base_compliance = 100
            compliance_deduction = (current_critical * 15) + (current_high * 5) + (current_total * 1)
            compliance_score = max(0, base_compliance - compliance_deduction)

            # Create metrics object with initial values
            metrics = ProjectQualityMetrics(
                project_id=project_id,
                last_scan_date=last_scan_date,
                quality_grade=QualityGrade.F,  # Will be updated
                grade_score=0,  # Will be updated
                total_vulnerabilities=current_total,
                critical_vulnerabilities=current_critical,
                high_vulnerabilities=current_high,
                compliance_score=compliance_score,
                frameworks_compliant=["OWASP", "GDPR"] if compliance_score >= 80 else []
            )

            # Calculate grade
            metrics.update_grade()

            # Add trend data if multiple scans available
            if len(total_issues_list) > 1:
                trend_data = []
                for i, (total, critical, high, timestamp) in enumerate(zip(
                    total_issues_list, critical_issues_list, high_issues_list, scan_timestamps
                )):
                    trend_data.append({
                        "scan_number": i + 1,
                        "total_issues": total,
                        "critical_issues": critical,
                        "high_issues": high,
                        "timestamp": timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
                    })
                metrics.vulnerability_trend = trend_data

            return metrics

    async def get_audit_trail(
        self,
        project_id: str,
        limit: int = 50,
        entity_type: Optional[str] = None,
        developer_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for a project with filtering options

        Args:
            project_id: Project identifier
            limit: Maximum number of entries to return
            entity_type: Filter by entity type
            developer_id: Filter by developer
            start_date: Filter from this date
            end_date: Filter to this date

        Returns:
            List of audit log entries
        """
        # Build dynamic WHERE clauses
        where_clauses = ["p.projectId = $projectId"]

        if entity_type:
            where_clauses.append("audit.entityType = $entityType")
        if developer_id:
            where_clauses.append("dev.developerId = $developerId")
        if start_date:
            where_clauses.append("audit.timestamp >= datetime($startDate)")
        if end_date:
            where_clauses.append("audit.timestamp <= datetime($endDate)")

        where_clause = " AND ".join(where_clauses)

        cypher_query = f"""
        MATCH (p:Project)-[:HAS_AUDIT_LOG]->(audit:AuditLog)
        OPTIONAL MATCH (audit)-[:PERFORMED_BY]->(dev:Developer)
        OPTIONAL MATCH (c:Commit)-[:HAS_AUDIT_LOG]->(audit)
        WHERE {where_clause}
        RETURN
            audit.auditId AS auditId,
            audit.action AS action,
            audit.entityType AS entityType,
            audit.entityId AS entityId,
            audit.timestamp AS timestamp,
            audit.changes AS changes,
            audit.metadata AS metadata,
            audit.complianceFramework AS complianceFramework,
            audit.regulatoryRequirements AS regulatoryRequirements,
            c.sha AS commitSha,
            dev.developerId AS developerId,
            dev.email AS developerEmail,
            audit.scanData AS scanData
        ORDER BY audit.timestamp DESC
        LIMIT $limit
        """

        parameters = {
            "projectId": project_id,
            "limit": limit
        }

        if entity_type:
            parameters["entityType"] = entity_type
        if developer_id:
            parameters["developerId"] = developer_id
        if start_date:
            parameters["startDate"] = start_date.isoformat()
        if end_date:
            parameters["endDate"] = end_date.isoformat()

        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(cypher_query, parameters)
            records = await result.data()

            # Convert to more readable format
            audit_trail = []
            for record in records:
                entry = {
                    "audit_id": record.get("auditId"),
                    "action": record.get("action"),
                    "entity_type": record.get("entityType"),
                    "entity_id": record.get("entityId"),
                    "timestamp": record.get("timestamp"),
                    "commit_sha": record.get("commitSha"),
                    "developer_id": record.get("developerId"),
                    "developer_email": record.get("developerEmail"),
                    "changes": record.get("changes", {}),
                    "metadata": record.get("metadata", {}),
                    "compliance_framework": record.get("complianceFramework"),
                    "regulatory_requirements": record.get("regulatoryRequirements", [])
                }

                # Add scan data summary if present
                scan_data = record.get("scanData")
                if scan_data:
                    entry["scan_summary"] = {
                        "tool": scan_data.get("tool"),
                        "total_issues": scan_data.get("totalIssues", 0),
                        "critical_issues": scan_data.get("criticalIssues", 0),
                        "high_issues": scan_data.get("highIssues", 0)
                    }

                audit_trail.append(entry)

            return audit_trail

    async def get_security_compliance_report(
        self,
        project_id: str,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive security compliance report

        Args:
            project_id: Project identifier
            days_back: Number of days to look back

        Returns:
            Compliance report with metrics and trends
        """
        cypher_query = """
        MATCH (p:Project {projectId: $projectId})-[:HAS_AUDIT_LOG]->(audit:AuditLog)
        WHERE audit.entityType = 'security_scan'
        AND audit.timestamp >= datetime() - duration({days: $daysBack})

        WITH audit
        ORDER BY audit.timestamp DESC

        RETURN
            count(audit) AS totalScans,
            avg(audit.scanData.totalIssues) AS avgTotalIssues,
            avg(audit.scanData.criticalIssues) AS avgCriticalIssues,
            avg(audit.scanData.highIssues) AS avgHighIssues,
            min(audit.scanData.totalIssues) AS minIssues,
            max(audit.scanData.totalIssues) AS maxIssues,
            collect(DISTINCT audit.scanData.tool) AS toolsUsed,
            collect(audit.complianceFramework) AS frameworks,
            collect(audit.timestamp) AS scanTimestamps
        """

        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(cypher_query, {
                "projectId": project_id,
                "daysBack": days_back
            })
            record = await result.single()

            if not record:
                return {
                    "project_id": project_id,
                    "period_days": days_back,
                    "status": "no_data",
                    "message": "No security scans found in the specified period"
                }

            # Calculate compliance score
            avg_critical = record.get("avgCriticalIssues", 0) or 0
            avg_high = record.get("avgHighIssues", 0) or 0
            avg_total = record.get("avgTotalIssues", 0) or 0

            # Compliance score: 100 - penalties for issues
            compliance_score = 100
            compliance_score -= avg_critical * 20  # -20 per critical issue
            compliance_score -= avg_high * 5       # -5 per high issue
            compliance_score -= avg_total * 1      # -1 per total issue
            compliance_score = max(0, min(100, compliance_score))

            # Determine overall grade
            if compliance_score >= 95:
                grade = "A+"
            elif compliance_score >= 90:
                grade = "A"
            elif compliance_score >= 80:
                grade = "B"
            elif compliance_score >= 70:
                grade = "C"
            elif compliance_score >= 60:
                grade = "D"
            else:
                grade = "F"

            return {
                "project_id": project_id,
                "period_days": days_back,
                "status": "completed",
                "total_scans": record.get("totalScans", 0),
                "average_issues": {
                    "total": round(avg_total, 1),
                    "critical": round(avg_critical, 1),
                    "high": round(avg_high, 1)
                },
                "issue_range": {
                    "min": record.get("minIssues", 0),
                    "max": record.get("maxIssues", 0)
                },
                "tools_used": list(set(record.get("toolsUsed", []))),
                "compliance_frameworks": list(set(record.get("frameworks", []))),
                "compliance_score": round(compliance_score, 1),
                "quality_grade": grade,
                "scan_timestamps": [ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
                                  for ts in record.get("scanTimestamps", [])]
            }

    async def get_quality_grade_for_dashboard(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get quality grade and metrics for dashboard display

        Args:
            project_id: Project identifier

        Returns:
            Quality grade and supporting metrics for dashboard
        """
        metrics = await self.get_project_quality_metrics(project_id)
        
        # Get recent scan summary for dashboard
        recent_scan_query = """
        MATCH (p:Project {projectId: $projectId})-[:HAS_AUDIT_LOG]->(audit:AuditLog)
        WHERE audit.entityType = 'security_scan'
        AND audit.timestamp >= datetime() - duration({days: 7})
        AND audit.scanData IS NOT NULL
        RETURN audit.scanData AS scanData, audit.timestamp AS timestamp
        ORDER BY audit.timestamp DESC
        LIMIT 1
        """

        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(recent_scan_query, {"projectId": project_id})
            recent_scan = await result.single()

        recent_scan_info = None
        if recent_scan:
            scan_data = recent_scan.get("scanData")
            recent_scan_info = {
                "timestamp": recent_scan.get("timestamp"),
                "tool": scan_data.get("tool"),
                "total_issues": scan_data.get("totalIssues", 0),
                "critical_issues": scan_data.get("criticalIssues", 0),
                "high_issues": scan_data.get("highIssues", 0)
            }

        return {
            "project_id": project_id,
            "quality_grade": metrics.quality_grade.value,
            "grade_score": metrics.grade_score,
            "total_vulnerabilities": metrics.total_vulnerabilities,
            "critical_vulnerabilities": metrics.critical_vulnerabilities,
            "high_vulnerabilities": metrics.high_vulnerabilities,
            "compliance_score": metrics.compliance_score,
            "frameworks_compliant": metrics.frameworks_compliant,
            "last_scan_date": metrics.last_scan_date,
            "recent_scan": recent_scan_info,
            "vulnerability_trend": metrics.vulnerability_trend
        }
