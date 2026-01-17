"""
Pydantic schemas for security scan results and audit logging
Structures results from Bandit, TruffleHog, Safety, and other security tools
"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
from uuid import UUID


class Severity(str, Enum):
    """Security issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScanTool(str, Enum):
    """Security scanning tools"""
    BANDIT = "bandit"
    TRUFFLEHOG = "trufflehog"
    SAFETY = "safety"
    PIP_AUDIT = "pip_audit"
    NPM_AUDIT = "npm_audit"
    ESLINT = "eslint"
    CODEQL = "codeql"
    TRIVY = "trivy"
    CHECKOV = "checkov"


class Confidence(str, Enum):
    """Confidence levels for security findings"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BanditIssue(BaseModel):
    """Bandit SAST issue model"""
    filename: str = Field(..., description="File where issue was found")
    test_name: str = Field(..., description="Name of the test that triggered")
    test_id: str = Field(..., description="Unique test identifier")
    issue_severity: Severity = Field(..., description="Severity level")
    issue_confidence: Confidence = Field(..., description="Confidence level")
    issue_text: str = Field(..., description="Description of the issue")
    line_number: int = Field(..., description="Line number where issue occurs")
    line_range: List[int] = Field(default_factory=list, description="Line range affected")
    code: str = Field("", description="Code snippet where issue occurs")
    more_info: str = Field("", description="Additional information URL")

    @validator('issue_severity', pre=True)
    def normalize_severity(cls, v):
        return v.upper() if isinstance(v, str) else v


class TruffleHogFinding(BaseModel):
    """TruffleHog secret detection finding"""
    file: str = Field(..., description="File containing the secret")
    line: int = Field(..., description="Line number")
    secret_type: str = Field(..., description="Type of secret detected")
    hash: str = Field(..., description="Hash of the secret")
    verified: bool = Field(True, description="Whether secret was verified")
    reason: str = Field("", description="Detection reason")


class SafetyVulnerability(BaseModel):
    """Safety dependency vulnerability"""
    package: str = Field(..., description="Package name")
    version: str = Field(..., description="Installed version")
    vulnerability_id: str = Field(..., description="CVE or vulnerability ID")
    advisory: str = Field(..., description="Security advisory text")
    severity: Severity = Field(..., description="Vulnerability severity")
    cve: Optional[str] = Field(None, description="CVE identifier")
    cvss_score: Optional[float] = Field(None, description="CVSS score")
    more_info_url: Optional[str] = Field(None, description="More information URL")


class PipAuditVulnerability(BaseModel):
    """pip-audit vulnerability finding"""
    name: str = Field(..., description="Package name")
    version: str = Field(..., description="Installed version")
    description: str = Field(..., description="Vulnerability description")
    severity: Severity = Field(..., description="Vulnerability severity")
    cve_id: Optional[str] = Field(None, description="CVE identifier")
    urls: List[str] = Field(default_factory=list, description="Related URLs")


class NpmAuditVulnerability(BaseModel):
    """npm audit vulnerability finding"""
    name: str = Field(..., description="Package name")
    severity: Severity = Field(..., description="Vulnerability severity")
    via: List[Union[str, Dict[str, Any]]] = Field(default_factory=list, description="Vulnerability path")
    effects: List[str] = Field(default_factory=list, description="Affected packages")
    range: str = Field("", description="Version range affected")
    nodes: List[str] = Field(default_factory=list, description="Affected package nodes")
    fix_available: bool = Field(False, description="Whether fix is available")


class ESLintIssue(BaseModel):
    """ESLint security/code quality issue"""
    file_path: str = Field(..., description="File with the issue")
    line: int = Field(..., description="Line number")
    column: int = Field(..., description="Column number")
    rule_id: str = Field(..., description="ESLint rule identifier")
    message: str = Field(..., description="Issue description")
    severity: int = Field(..., description="ESLint severity (1=warning, 2=error)")

    @property
    def mapped_severity(self) -> Severity:
        """Map ESLint severity to our Severity enum"""
        return Severity.HIGH if self.severity == 2 else Severity.MEDIUM


class CodeQLAlert(BaseModel):
    """CodeQL security alert"""
    tool: str = Field(..., description="CodeQL tool name")
    rule_id: str = Field(..., description="Rule identifier")
    rule_name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Alert description")
    severity: Severity = Field(..., description="Alert severity")
    precision: str = Field(..., description="Alert precision")
    locations: List[Dict[str, Any]] = Field(default_factory=list, description="Alert locations")


class TrivyVulnerability(BaseModel):
    """Trivy container/infrastructure vulnerability"""
    vulnerability_id: str = Field(..., description="Vulnerability ID")
    pkg_name: str = Field(..., description="Package name")
    installed_version: str = Field(..., description="Installed version")
    fixed_version: str = Field("", description="Fixed version")
    severity: Severity = Field(..., description="Vulnerability severity")
    description: str = Field(..., description="Vulnerability description")
    references: List[str] = Field(default_factory=list, description="Reference URLs")


class SecurityScanResult(BaseModel):
    """Comprehensive security scan result"""
    scan_id: str = Field(..., description="Unique scan identifier")
    tool: ScanTool = Field(..., description="Security scanning tool used")
    target: str = Field(..., description="Scan target (e.g., 'backend/app', 'frontend/src')")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When scan was performed")
    duration_seconds: float = Field(..., description="Scan duration in seconds")

    # Tool-specific results
    bandit_issues: List[BanditIssue] = Field(default_factory=list, description="Bandit SAST issues")
    trufflehog_findings: List[TruffleHogFinding] = Field(default_factory=list, description="TruffleHog secrets")
    safety_vulnerabilities: List[SafetyVulnerability] = Field(default_factory=list, description="Safety vulnerabilities")
    pip_audit_vulnerabilities: List[PipAuditVulnerability] = Field(default_factory=list, description="pip-audit vulnerabilities")
    npm_audit_vulnerabilities: List[NpmAuditVulnerability] = Field(default_factory=list, description="npm audit vulnerabilities")
    eslint_issues: List[ESLintIssue] = Field(default_factory=list, description="ESLint issues")
    codeql_alerts: List[CodeQLAlert] = Field(default_factory=list, description="CodeQL alerts")
    trivy_vulnerabilities: List[TrivyVulnerability] = Field(default_factory=list, description="Trivy vulnerabilities")

    # Summary statistics
    total_issues: int = Field(default=0, description="Total number of issues found")
    critical_issues: int = Field(default=0, description="Number of critical severity issues")
    high_issues: int = Field(default=0, description="Number of high severity issues")
    medium_issues: int = Field(default=0, description="Number of medium severity issues")
    low_issues: int = Field(default=0, description="Number of low severity issues")
    info_issues: int = Field(default=0, description="Number of info severity issues")

    # Scan metadata
    scan_version: str = Field("", description="Tool version used")
    scan_config: Dict[str, Any] = Field(default_factory=dict, description="Scan configuration used")
    raw_output: Optional[str] = Field(None, description="Raw scan output for debugging")

    def calculate_summary_stats(self):
        """Calculate summary statistics from all findings"""
        all_issues = []

        # Collect all issues with severity
        for issue in self.bandit_issues:
            all_issues.append((issue.issue_severity, issue))
        for issue in self.trufflehog_findings:
            all_issues.append((Severity.CRITICAL, issue))  # Secrets are always critical
        for issue in self.safety_vulnerabilities:
            all_issues.append((issue.severity, issue))
        for issue in self.pip_audit_vulnerabilities:
            all_issues.append((issue.severity, issue))
        for issue in self.npm_audit_vulnerabilities:
            all_issues.append((issue.severity, issue))
        for issue in self.eslint_issues:
            all_issues.append((issue.mapped_severity, issue))
        for issue in self.codeql_alerts:
            all_issues.append((issue.severity, issue))
        for issue in self.trivy_vulnerabilities:
            all_issues.append((issue.severity, issue))

        # Count by severity
        severity_counts = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 0,
            Severity.MEDIUM: 0,
            Severity.LOW: 0,
            Severity.INFO: 0
        }

        for severity, _ in all_issues:
            severity_counts[severity] += 1

        self.total_issues = len(all_issues)
        self.critical_issues = severity_counts[Severity.CRITICAL]
        self.high_issues = severity_counts[Severity.HIGH]
        self.medium_issues = severity_counts[Severity.MEDIUM]
        self.low_issues = severity_counts[Severity.LOW]
        self.info_issues = severity_counts[Severity.INFO]


class AuditLogEntry(BaseModel):
    """Audit log entry for security and compliance events"""
    audit_id: str = Field(..., description="Unique audit log identifier")
    project_id: str = Field(..., description="Project identifier")
    commit_sha: str = Field(..., description="Git commit SHA")
    developer_id: Optional[str] = Field(None, description="Developer/user identifier")
    developer_email: Optional[str] = Field(None, description="Developer email")
    action: str = Field(..., description="Action performed (scan, review, etc.)")
    entity_type: str = Field(..., description="Entity type (security_scan, pr_review, etc.)")
    entity_id: str = Field(..., description="Entity identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When action occurred")

    # Security scan specific fields
    scan_result: Optional[SecurityScanResult] = Field(None, description="Security scan results")
    previous_scan_id: Optional[str] = Field(None, description="Previous scan for comparison")

    # Change details
    changes: Dict[str, Any] = Field(default_factory=dict, description="What changed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    # Compliance information
    compliance_framework: Optional[str] = Field(None, description="Compliance framework (GDPR, HIPAA, etc.)")
    regulatory_requirements: List[str] = Field(default_factory=list, description="Regulatory requirements addressed")


class QualityGrade(str, Enum):
    """Quality grade based on security scan results"""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class ComplianceReport(BaseModel):
    """Compliance report for security audit results"""
    project_id: str = Field(..., description="Project identifier")
    compliance_score: int = Field(..., description="Overall compliance score (0-100)")
    vulnerability_count: int = Field(..., description="Total number of vulnerabilities")
    last_audit: Optional[str] = Field(None, description="Last audit timestamp")
    risk_level: str = Field(..., description="Risk level (LOW, MEDIUM, HIGH, CRITICAL)")
    severity_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Vulnerabilities by severity")
    
    # Additional compliance metrics
    frameworks_compliant: List[str] = Field(default_factory=list, description="Compliant frameworks")
    audit_duration: Optional[float] = Field(None, description="Audit duration in seconds")
    scan_tools_used: List[str] = Field(default_factory=list, description="Security tools used in audit")


class ProjectQualityMetrics(BaseModel):
    """Project quality metrics for dashboard display"""
    project_id: str = Field(..., description="Project identifier")
    last_scan_date: Optional[datetime] = Field(None, description="Last security scan date")
    quality_grade: QualityGrade = Field(..., description="Current quality grade")
    grade_score: int = Field(..., description="Numerical score (0-100)")

    # Security metrics
    total_vulnerabilities: int = Field(default=0, description="Total vulnerabilities found")
    critical_vulnerabilities: int = Field(default=0, description="Critical vulnerabilities")
    high_vulnerabilities: int = Field(default=0, description="High severity vulnerabilities")
    unresolved_vulnerabilities: int = Field(default=0, description="Unresolved vulnerabilities")

    # Compliance metrics
    compliance_score: int = Field(default=0, description="Compliance score (0-100)")
    frameworks_compliant: List[str] = Field(default_factory=list, description="Compliant frameworks")

    # Trend data
    vulnerability_trend: List[Dict[str, Any]] = Field(default_factory=list, description="Vulnerability trend over time")
    grade_history: List[Dict[str, Any]] = Field(default_factory=list, description="Grade history")

    def calculate_quality_grade(self) -> QualityGrade:
        """
        Calculate quality grade based on vulnerability counts and other metrics

        Grading criteria:
        A+: 0 critical, 0-2 high, compliance_score >= 95
        A:  0 critical, 0-5 high, compliance_score >= 90
        B:  0-1 critical, 0-10 high, compliance_score >= 80
        C:  0-3 critical, 0-20 high, compliance_score >= 70
        D:  0-5 critical, 0-30 high, compliance_score >= 60
        F:  >5 critical or >30 high or compliance_score < 60
        """
        critical = self.critical_vulnerabilities
        high = self.high_vulnerabilities
        compliance = self.compliance_score

        if critical == 0 and high <= 2 and compliance >= 95:
            return QualityGrade.A_PLUS
        elif critical == 0 and high <= 5 and compliance >= 90:
            return QualityGrade.A
        elif critical <= 1 and high <= 10 and compliance >= 80:
            return QualityGrade.B
        elif critical <= 3 and high <= 20 and compliance >= 70:
            return QualityGrade.C
        elif critical <= 5 and high <= 30 and compliance >= 60:
            return QualityGrade.D
        else:
            return QualityGrade.F

    def update_grade(self):
        """Update quality grade based on current metrics"""
        self.quality_grade = self.calculate_quality_grade()
        self.grade_score = self._calculate_grade_score()

    def _calculate_grade_score(self) -> int:
        """Calculate numerical score from 0-100"""
        # Base score from compliance
        score = self.compliance_score

        # Deduct points for vulnerabilities
        score -= self.critical_vulnerabilities * 10  # -10 per critical
        score -= self.high_vulnerabilities * 5       # -5 per high
        score -= self.total_vulnerabilities          # -1 per total

        # Ensure score stays within bounds
        return max(0, min(100, score))
