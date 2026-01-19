#!/usr/bin/env python3
"""
Security Compliance Service
Parses npm audit JSON reports and maps vulnerabilities to compliance scores.
Implements the Security and Audit Compliance module (Chapter 8.2.1).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.database.neo4j_db import Neo4jDB
from app.schemas.security_models import (
    SecurityScanResult, 
    NpmAuditVulnerability, 
    Severity,
    ProjectQualityMetrics,
    ComplianceReport
)

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Severity levels from npm audit."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VulnerabilityScore:
    """Vulnerability with calculated compliance impact."""
    id: str
    package: str
    severity: SeverityLevel
    title: str
    description: str
    cwe: List[str]
    cvss_score: Optional[float]
    compliance_impact: int  # 0-100 impact on compliance score


class SecurityComplianceService:
    """Service for handling security compliance and vulnerability management."""
    
    def __init__(self, neo4j_db: Neo4jDB):
        self.neo4j_db = neo4j_db
        self.severity_weights = {
            SeverityLevel.LOW: 5,
            SeverityLevel.MODERATE: 15,
            SeverityLevel.HIGH: 40,
            SeverityLevel.CRITICAL: 80
        }
    
    def parse_npm_audit_json(self, audit_json: Dict) -> List[VulnerabilityScore]:
        """
        Parse npm audit JSON report and convert to vulnerability objects.
        
        Args:
            audit_json: Parsed JSON from npm audit --json output
            
        Returns:
            List of vulnerability objects with compliance impact scores
        """
        vulnerabilities = []
        
        if 'vulnerabilities' not in audit_json:
            logger.warning("No vulnerabilities found in audit report")
            return vulnerabilities
        
        for vuln_id, vuln_data in audit_json['vulnerabilities'].items():
            try:
                vulnerability = self._create_vulnerability_score(vuln_id, vuln_data)
                vulnerabilities.append(vulnerability)
            except Exception as e:
                # Sanitize user-controlled data before logging
                safe_vuln_id = str(vuln_id).replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                logger.error(f"Error parsing vulnerability {safe_vuln_id}: {e}")
                continue
        
        # Sanitize the count before logging
        safe_count = str(len(vulnerabilities)).replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        logger.info(f"Parsed {safe_count} vulnerabilities from audit report")
        return vulnerabilities
    
    def _create_vulnerability_score(self, vuln_id: str, vuln_data: Dict) -> VulnerabilityScore:
        """Create a VulnerabilityScore object from npm audit data."""
        
        # Extract severity and convert to enum
        severity_str = vuln_data.get('severity', 'low').lower()
        try:
            severity = SeverityLevel(severity_str)
        except ValueError:
            logger.warning(f"Unknown severity level: {severity_str}, defaulting to low")
            severity = SeverityLevel.LOW
        
        # Extract other fields
        package = vuln_data.get('name', 'unknown')
        title = vuln_data.get('title', 'No title')
        description = vuln_data.get('overview', 'No description')
        
        # Extract CWE information
        cwe = vuln_data.get('cwe', [])
        if isinstance(cwe, str):
            cwe = [cwe]
        
        # Extract CVSS score if available
        cvss_score = None
        if 'cvss' in vuln_data and 'score' in vuln_data['cvss']:
            cvss_score = vuln_data['cvss']['score']
        
        # Calculate compliance impact based on severity
        compliance_impact = self.severity_weights.get(severity, 5)
        
        return VulnerabilityScore(
            id=vuln_id,
            package=package,
            severity=severity,
            title=title,
            description=description,
            cwe=cwe,
            cvss_score=cvss_score,
            compliance_impact=compliance_impact
        )
    
    def calculate_compliance_score(self, vulnerabilities: List[VulnerabilityScore]) -> int:
        """
        Calculate overall compliance score based on vulnerabilities.
        
        Args:
            vulnerabilities: List of vulnerabilities with compliance impact
            
        Returns:
            Compliance score (0-100)
        """
        if not vulnerabilities:
            return 100  # Perfect score if no vulnerabilities
        
        # Calculate total impact
        total_impact = sum(vuln.compliance_impact for vuln in vulnerabilities)
        
        # Apply exponential penalty for critical vulnerabilities
        critical_count = sum(1 for vuln in vulnerabilities if vuln.severity == SeverityLevel.CRITICAL)
        high_count = sum(1 for vuln in vulnerabilities if vuln.severity == SeverityLevel.HIGH)
        
        # Calculate score with weighted penalties
        base_penalty = total_impact
        critical_penalty = critical_count * 20  # Heavy penalty for critical
        high_penalty = high_count * 10  # Moderate penalty for high
        
        total_penalty = base_penalty + critical_penalty + high_penalty
        
        # Ensure score stays within bounds
        compliance_score = max(0, 100 - total_penalty)
        
        logger.info(f"Calculated compliance score: {compliance_score} "
                   f"(base: {base_penalty}, critical: {critical_penalty}, high: {high_penalty})")
        
        return compliance_score
    
    def save_vulnerabilities_to_neo4j(self, project_id: str, vulnerabilities: List[VulnerabilityScore]) -> bool:
        """
        Save vulnerabilities to Neo4j database using Cypher queries.
        
        Args:
            project_id: Unique identifier for the project
            vulnerabilities: List of vulnerabilities to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.neo4j_db.get_session() as session:
                # Create or update project node
                session.run("""
                    MERGE (p:Project {id: $project_id})
                    SET p.last_audit = $audit_time,
                        p.vulnerability_count = $vuln_count
                    RETURN p
                """, {
                    'project_id': project_id,
                    'audit_time': datetime.now(timezone.utc).isoformat(),
                    'vuln_count': len(vulnerabilities)
                })
                
                # Create vulnerability nodes and relationships
                for vuln in vulnerabilities:
                    session.run("""
                        MERGE (v:Vulnerability {id: $vuln_id})
                        SET v.package = $package,
                            v.severity = $severity,
                            v.title = $title,
                            v.description = $description,
                            v.cwe = $cwe,
                            v.cvss_score = $cvss_score,
                            v.compliance_impact = $compliance_impact,
                            v.created_at = $created_at
                        WITH v
                        MATCH (p:Project {id: $project_id})
                        MERGE (p)-[r:HAS_VULNERABILITY]->(v)
                        SET r.discovered_at = $discovered_at
                        RETURN v
                    """, {
                        'vuln_id': vuln.id,
                        'package': vuln.package,
                        'severity': vuln.severity.value,
                        'title': vuln.title,
                        'description': vuln.description,
                        'cwe': vuln.cwe,
                        'cvss_score': vuln.cvss_score,
                        'compliance_impact': vuln.compliance_impact,
                        'project_id': project_id,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'discovered_at': datetime.now(timezone.utc).isoformat()
                    })
                
                # Update project compliance score
                compliance_score = self.calculate_compliance_score(vulnerabilities)
                session.run("""
                    MATCH (p:Project {id: $project_id})
                    SET p.compliance_score = $compliance_score,
                        p.last_compliance_update = $update_time
                    RETURN p
                """, {
                    'project_id': project_id,
                    'compliance_score': compliance_score,
                    'update_time': datetime.now(timezone.utc).isoformat()
                })
            
            logger.info(f"Successfully saved {len(vulnerabilities)} vulnerabilities for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving vulnerabilities to Neo4j: {e}")
            return False
    
    def get_compliance_report(self, project_id: str) -> Optional[ComplianceReport]:
        """
        Generate a comprehensive compliance report for a project.
        
        Args:
            project_id: Unique identifier for the project
            
        Returns:
            ComplianceReport object with detailed information
        """
        try:
            with self.neo4j_db.get_session() as session:
                # Get project information
                project_result = session.run("""
                    MATCH (p:Project {id: $project_id})
                    RETURN p.id as id, p.compliance_score as score, 
                           p.vulnerability_count as vuln_count, p.last_audit as last_audit
                """, {'project_id': project_id}).single()
                
                if not project_result:
                    logger.warning(f"Project {project_id} not found")
                    return None
                
                # Get vulnerabilities grouped by severity
                vuln_results = session.run("""
                    MATCH (p:Project {id: $project_id})-[:HAS_VULNERABILITY]->(v:Vulnerability)
                    RETURN v.severity as severity, count(v) as count,
                           collect({id: v.id, package: v.package, title: v.title}) as vulnerabilities
                    ORDER BY v.severity DESC
                """, {'project_id': project_id})
                
                severity_breakdown = {}
                for record in vuln_results:
                    severity_breakdown[record['severity']] = {
                        'count': record['count'],
                        'vulnerabilities': record['vulnerabilities']
                    }
                
                # Calculate risk assessment
                risk_level = self._calculate_risk_level(project_result['score'])
                
                return ComplianceReport(
                    project_id=project_id,
                    compliance_score=project_result['score'],
                    vulnerability_count=project_result['vuln_count'],
                    last_audit=project_result['last_audit'],
                    risk_level=risk_level,
                    severity_breakdown=severity_breakdown,
                    frameworks_compliant=[],
                    audit_duration=None,
                    scan_tools_used=["npm_audit"]
                )
                
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return None
    
    def _calculate_risk_level(self, compliance_score: int) -> str:
        """Calculate risk level based on compliance score."""
        if compliance_score >= 90:
            return "LOW"
        elif compliance_score >= 70:
            return "MEDIUM"
        elif compliance_score >= 50:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def get_vulnerability_trends(self, project_id: str, days: int = 30) -> Dict:
        """
        Get vulnerability trends over time for a project.
        
        Args:
            project_id: Unique identifier for the project
            days: Number of days to look back
            
        Returns:
            Dictionary with trend data
        """
        try:
            with self.neo4j_db.get_session() as session:
                # Get audit history
                audit_results = session.run("""
                    MATCH (p:Project {id: $project_id})-[:HAS_VULNERABILITY]->(v:Vulnerability)
                    WHERE v.created_at >= $start_date
                    RETURN v.severity as severity, v.created_at as created_at
                    ORDER BY v.created_at
                """, {
                    'project_id': project_id,
                    'start_date': (datetime.now(timezone.utc).timestamp() - days * 24 * 3600) * 1000
                })
                
                trends = {
                    'total_vulnerabilities': 0,
                    'severity_trends': {s.value: [] for s in SeverityLevel},
                    'daily_counts': {}
                }
                
                for record in audit_results:
                    severity = record['severity']
                    created_at = record['created_at']
                    
                    trends['total_vulnerabilities'] += 1
                    
                    # Group by day for daily counts
                    day = created_at[:10]  # YYYY-MM-DD format
                    if day not in trends['daily_counts']:
                        trends['daily_counts'][day] = 0
                    trends['daily_counts'][day] += 1
                
                return trends
                
        except Exception as e:
            logger.error(f"Error getting vulnerability trends: {e}")
            return {}
    
    def process_audit_report(self, project_id: str, audit_json: Dict) -> ComplianceReport:
        """
        Complete workflow: parse audit, save to database, and return compliance report.
        
        Args:
            project_id: Unique identifier for the project
            audit_json: Parsed npm audit JSON
            
        Returns:
            ComplianceReport with results
        """
        # Parse vulnerabilities
        vulnerabilities = self.parse_npm_audit_json(audit_json)
        
        # Save to database
        save_success = self.save_vulnerabilities_to_neo4j(project_id, vulnerabilities)
        
        if not save_success:
            raise Exception("Failed to save vulnerabilities to database")
        
        # Generate compliance report
        report = self.get_compliance_report(project_id)
        
        if not report:
            raise Exception("Failed to generate compliance report")
        
        logger.info(f"Successfully processed audit for project {project_id}: "
                   f"score={report.compliance_score}, vulnerabilities={report.vulnerability_count}")
        
        return report


# Example usage and testing
if __name__ == "__main__":
    # Example npm audit JSON structure
    example_audit_json = {
        "vulnerabilities": {
            "axios": {
                "name": "axios",
                "severity": "high",
                "title": "Server-Side Request Forgery in axios",
                "overview": "axios is vulnerable to SSRF.",
                "cwe": ["CWE-918"],
                "cvss": {"score": 7.5}
            },
            "lodash": {
                "name": "lodash",
                "severity": "moderate", 
                "title": "Prototype Pollution in lodash",
                "overview": "lodash is vulnerable to prototype pollution.",
                "cwe": ["CWE-1321"],
                "cvss": {"score": 6.1}
            }
        }
    }
    
    # Example of how to use the service
    # neo4j_db = Neo4jDB()  # Initialize with your connection details
    # service = SecurityComplianceService(neo4j_db)
    # report = service.process_audit_report("my-project", example_audit_json)
    # print(f"Compliance Score: {report.compliance_score}")
