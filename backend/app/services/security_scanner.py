"""
Security Scanner Service with OWASP References

Integrates SecureCodeAnalyzer with StandardsClassifier to provide
comprehensive security scanning with OWASP Top 10 references.

Validates Requirements: 1.6
"""
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from app.services.secure_code_analyzer import (
    SecureCodeAnalyzer,
    SecurityIssue,
    AnalysisRisk
)
from app.services.standards_classifier import (
    get_standards_classifier
)

logger = logging.getLogger(__name__)


@dataclass
class SecurityFinding:
    """Security finding with OWASP reference"""
    # Original issue data
    issue_type: str
    severity: str
    location: str
    description: str
    code_snippet: str
    suggestion: str
    
    # Standards classification
    iso_25010_characteristic: Optional[str] = None
    iso_25010_sub_characteristic: Optional[str] = None
    iso_23396_practice: Optional[str] = None
    owasp_reference: Optional[str] = None
    owasp_name: Optional[str] = None
    owasp_description: Optional[str] = None
    owasp_mitigations: Optional[List[str]] = None
    
    # Metadata
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class SecurityScanResult:
    """Result of security scan with OWASP references"""
    findings: List[SecurityFinding]
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    owasp_coverage: Dict[str, int]  # OWASP ID -> count
    complexity_score: int
    analysis_time: float
    files_scanned: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'findings': [f.to_dict() for f in self.findings],
            'total_issues': self.total_issues,
            'critical_issues': self.critical_issues,
            'high_issues': self.high_issues,
            'medium_issues': self.medium_issues,
            'low_issues': self.low_issues,
            'owasp_coverage': self.owasp_coverage,
            'complexity_score': self.complexity_score,
            'analysis_time': self.analysis_time,
            'files_scanned': self.files_scanned
        }


class SecurityScanner:
    """
    Security scanner that combines code analysis with OWASP classification.
    
    This service:
    1. Uses SecureCodeAnalyzer to detect security issues
    2. Uses StandardsClassifier to map issues to OWASP Top 10
    3. Enriches findings with OWASP references and mitigations
    """
    
    def __init__(self):
        self.code_analyzer = SecureCodeAnalyzer()
        self.standards_classifier = get_standards_classifier()
        self._initialize_owasp_mappings()
    
    def _initialize_owasp_mappings(self):
        """Initialize enhanced OWASP mappings for security issues"""
        # Map issue types to OWASP categories
        self.issue_to_owasp = {
            'dangerous_function_call': {
                'eval': 'A03:2021',  # Injection
                'exec': 'A03:2021',  # Injection
                'pickle': 'A08:2021',  # Software and Data Integrity Failures
                'subprocess': 'A03:2021',  # Injection (command injection)
                'os.system': 'A03:2021',  # Injection
            },
            'sql_injection_risk': 'A03:2021',  # Injection
            'hardcoded_secret': 'A02:2021',  # Cryptographic Failures
            'dangerous_import': 'A05:2021',  # Security Misconfiguration
            'missing_authentication': 'A07:2021',  # Identification and Authentication Failures
            'missing_authorization': 'A01:2021',  # Broken Access Control
            'insecure_deserialization': 'A08:2021',  # Software and Data Integrity Failures
            'missing_logging': 'A09:2021',  # Security Logging and Monitoring Failures
            'ssrf_risk': 'A10:2021',  # Server-Side Request Forgery
            'xss_risk': 'A03:2021',  # Injection
            'csrf_risk': 'A01:2021',  # Broken Access Control
            'weak_crypto': 'A02:2021',  # Cryptographic Failures
            'path_traversal': 'A01:2021',  # Broken Access Control
            'insecure_config': 'A05:2021',  # Security Misconfiguration
            'outdated_dependency': 'A06:2021',  # Vulnerable and Outdated Components
        }
        
        # Get OWASP vulnerabilities for reference
        self.owasp_vulnerabilities = {
            vuln.id: vuln 
            for vuln in self.standards_classifier.mapper.get_all_owasp_vulnerabilities()
        }
    
    def scan_code(
        self,
        source_code: str,
        filename: str = "<string>"
    ) -> SecurityScanResult:
        """
        Scan source code for security issues with OWASP references.
        
        Args:
            source_code: Source code to scan
            filename: Name of the file being scanned
            
        Returns:
            SecurityScanResult with OWASP-enriched findings
        """
        # Perform code analysis
        analysis_result = self.code_analyzer.analyze_code(source_code, filename)
        
        # Convert and enrich findings
        findings = self._enrich_findings(analysis_result.issues, filename)
        
        # Calculate statistics
        severity_counts = self._calculate_severity_counts(findings)
        owasp_coverage = self._calculate_owasp_coverage(findings)
        
        result = SecurityScanResult(
            findings=findings,
            total_issues=len(findings),
            critical_issues=severity_counts['critical'],
            high_issues=severity_counts['high'],
            medium_issues=severity_counts['medium'],
            low_issues=severity_counts['low'],
            owasp_coverage=owasp_coverage,
            complexity_score=analysis_result.complexity_score,
            analysis_time=analysis_result.analysis_time,
            files_scanned=1
        )
        
        logger.info(
            f"Security scan completed for {filename}: "
            f"{result.total_issues} issues found, "
            f"{len(owasp_coverage)} OWASP categories affected"
        )
        
        return result
    
    def scan_multiple_files(
        self,
        files: Dict[str, str]
    ) -> SecurityScanResult:
        """
        Scan multiple files for security issues.
        
        Args:
            files: Dictionary mapping filenames to source code
            
        Returns:
            Aggregated SecurityScanResult
        """
        all_findings = []
        total_complexity = 0
        total_time = 0.0
        
        for filename, source_code in files.items():
            try:
                result = self.scan_code(source_code, filename)
                all_findings.extend(result.findings)
                total_complexity += result.complexity_score
                total_time += result.analysis_time
            except Exception as e:
                logger.error(f"Failed to scan {filename}: {str(e)}")
                # Add error finding
                error_finding = SecurityFinding(
                    issue_type='scan_error',
                    severity='low',
                    location=filename,
                    description=f"Failed to scan file: {str(e)}",
                    code_snippet='',
                    suggestion='Check file format and try again'
                )
                all_findings.append(error_finding)
        
        # Calculate aggregated statistics
        severity_counts = self._calculate_severity_counts(all_findings)
        owasp_coverage = self._calculate_owasp_coverage(all_findings)
        
        result = SecurityScanResult(
            findings=all_findings,
            total_issues=len(all_findings),
            critical_issues=severity_counts['critical'],
            high_issues=severity_counts['high'],
            medium_issues=severity_counts['medium'],
            low_issues=severity_counts['low'],
            owasp_coverage=owasp_coverage,
            complexity_score=total_complexity,
            analysis_time=total_time,
            files_scanned=len(files)
        )
        
        logger.info(
            f"Security scan completed for {len(files)} files: "
            f"{result.total_issues} total issues, "
            f"{len(owasp_coverage)} OWASP categories affected"
        )
        
        return result
    
    def _enrich_findings(
        self,
        issues: List[SecurityIssue],
        filename: str
    ) -> List[SecurityFinding]:
        """
        Enrich security issues with OWASP references and standards classification.
        
        Args:
            issues: List of security issues from code analyzer
            filename: Name of the file being analyzed
            
        Returns:
            List of enriched SecurityFinding objects
        """
        enriched_findings = []
        
        for issue in issues:
            # Classify with standards
            classified = self.standards_classifier.classify_finding(
                category='security',
                message=issue.description,
                severity=issue.severity.value,
                file_path=filename,
                line_number=self._extract_line_number(issue.location)
            )
            
            # Determine OWASP reference
            owasp_id = self._determine_owasp_reference(issue)
            owasp_vuln = self.owasp_vulnerabilities.get(owasp_id) if owasp_id else None
            
            # Create enriched finding
            finding = SecurityFinding(
                issue_type=issue.issue_type,
                severity=issue.severity.value,
                location=issue.location,
                description=issue.description,
                code_snippet=issue.code_snippet,
                suggestion=issue.suggestion,
                iso_25010_characteristic=classified.iso_25010_characteristic,
                iso_25010_sub_characteristic=classified.iso_25010_sub_characteristic,
                iso_23396_practice=classified.iso_23396_practice,
                owasp_reference=owasp_id,
                owasp_name=owasp_vuln.name if owasp_vuln else None,
                owasp_description=owasp_vuln.description if owasp_vuln else None,
                owasp_mitigations=owasp_vuln.mitigations if owasp_vuln else None,
                confidence=classified.confidence
            )
            
            enriched_findings.append(finding)
        
        return enriched_findings
    
    def _determine_owasp_reference(self, issue: SecurityIssue) -> Optional[str]:
        """
        Determine OWASP Top 10 reference for a security issue.
        
        Args:
            issue: Security issue to classify
            
        Returns:
            OWASP ID (e.g., "A01:2021") or None
        """
        issue_type = issue.issue_type
        description_lower = issue.description.lower()
        
        # Check direct issue type mapping
        if issue_type in self.issue_to_owasp:
            mapping = self.issue_to_owasp[issue_type]
            
            # If mapping is a dict, check for specific function names
            if isinstance(mapping, dict):
                for keyword, owasp_id in mapping.items():
                    if keyword in description_lower:
                        return owasp_id
                # Return first value as default
                return next(iter(mapping.values()))
            else:
                return mapping
        
        # Use standards classifier for keyword-based mapping
        owasp_ref = self.standards_classifier._map_to_owasp(issue.description)
        if owasp_ref:
            return owasp_ref
        
        # Default mapping based on severity for security issues
        if issue.severity == AnalysisRisk.CRITICAL:
            return 'A03:2021'  # Injection (most critical)
        elif issue.severity == AnalysisRisk.HIGH:
            return 'A01:2021'  # Broken Access Control
        
        return None
    
    def _extract_line_number(self, location: str) -> int:
        """Extract line number from location string"""
        try:
            # Location format: "filename:line"
            if ':' in location:
                return int(location.split(':')[-1])
        except (ValueError, IndexError):
            pass
        return 0
    
    def _calculate_severity_counts(
        self,
        findings: List[SecurityFinding]
    ) -> Dict[str, int]:
        """Calculate counts by severity level"""
        counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'safe': 0
        }
        
        for finding in findings:
            severity = finding.severity.lower()
            if severity in counts:
                counts[severity] += 1
        
        return counts
    
    def _calculate_owasp_coverage(
        self,
        findings: List[SecurityFinding]
    ) -> Dict[str, int]:
        """Calculate OWASP Top 10 coverage (which categories are affected)"""
        coverage = {}
        
        for finding in findings:
            if finding.owasp_reference:
                owasp_id = finding.owasp_reference
                coverage[owasp_id] = coverage.get(owasp_id, 0) + 1
        
        return coverage
    
    def get_owasp_summary(
        self,
        result: SecurityScanResult
    ) -> Dict[str, Any]:
        """
        Generate OWASP-focused summary of scan results.
        
        Args:
            result: Security scan result
            
        Returns:
            Dictionary with OWASP summary information
        """
        owasp_details = {}
        
        for owasp_id, count in result.owasp_coverage.items():
            vuln = self.owasp_vulnerabilities.get(owasp_id)
            if vuln:
                owasp_details[owasp_id] = {
                    'rank': vuln.rank,
                    'name': vuln.name,
                    'description': vuln.description,
                    'finding_count': count,
                    'mitigations': vuln.mitigations
                }
        
        return {
            'total_owasp_categories_affected': len(result.owasp_coverage),
            'owasp_details': owasp_details,
            'most_common_vulnerability': max(
                result.owasp_coverage.items(),
                key=lambda x: x[1]
            )[0] if result.owasp_coverage else None,
            'security_score': self._calculate_security_score(result)
        }
    
    def _calculate_security_score(self, result: SecurityScanResult) -> float:
        """
        Calculate overall security score (0-100).
        
        Higher score = better security
        Score is reduced by:
        - Critical issues: -20 points each
        - High issues: -10 points each
        - Medium issues: -5 points each
        - Low issues: -2 points each
        """
        score = 100.0
        
        score -= result.critical_issues * 20
        score -= result.high_issues * 10
        score -= result.medium_issues * 5
        score -= result.low_issues * 2
        
        # Ensure score doesn't go below 0
        return max(0.0, score)


# Singleton instance
_scanner_instance: Optional[SecurityScanner] = None


def get_security_scanner() -> SecurityScanner:
    """Get or create the singleton SecurityScanner instance"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = SecurityScanner()
    return _scanner_instance
