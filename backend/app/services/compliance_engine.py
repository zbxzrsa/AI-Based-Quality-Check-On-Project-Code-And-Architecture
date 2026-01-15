"""
Compliance Rules Engine for regulated industries
"""
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
import re


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks"""
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    NIST = "nist"


class RuleSeverity(str, Enum):
    """Rule violation severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceRule(BaseModel):
    """Individual compliance rule"""
    id: str
    framework: ComplianceFramework
    name: str
    description: str
    severity: RuleSeverity
    category: str
    pattern: Optional[str] = None  # Regex pattern for code matching
    file_patterns: List[str] = []  # File patterns to check
    enabled: bool = True


class ComplianceViolation(BaseModel):
    """Detected compliance violation"""
    rule_id: str
    framework: ComplianceFramework
    severity: RuleSeverity
    file_path: str
    line_number: int
    message: str
    evidence: str
    remediation: str


class ComplianceRulesEngine:
    """Engine for evaluating compliance rules"""
    
    # PCI-DSS Rules
    PCI_DSS_RULES = [
        ComplianceRule(
            id="PCI-DSS-6.5.1",
            framework=ComplianceFramework.PCI_DSS,
            name="SQL Injection Prevention",
            description="Prevent SQL injection vulnerabilities",
            severity=RuleSeverity.CRITICAL,
            category="injection",
            pattern=r"execute\(['\"].*\+.*['\"]|cursor\.execute\(.*%.*\)",
            file_patterns=["*.py", "*.js", "*.java"],
        ),
        ComplianceRule(
            id="PCI-DSS-3.4",
            framework=ComplianceFramework.PCI_DSS,
            name="Encryption of Cardholder Data",
            description="Cardholder data must be encrypted in storage",
            severity=RuleSeverity.CRITICAL,
            category="encryption",
            pattern=r"(card|credit|cvv|pan)[_\s]*(?:number|data).*=.*(?!encrypt|hash)",
            file_patterns=["*.py", "*.js", "*.java"],
        ),
        ComplianceRule(
            id="PCI-DSS-8.2.3",
            framework=ComplianceFramework.PCI_DSS,
            name="Strong Password Requirements",
            description="Passwords must meet complexity requirements",
            severity=RuleSeverity.HIGH,
            category="authentication",
            pattern=r"password.*=.*['\"][^A-Z0-9!@#$%^&*]{1,7}['\"]",
            file_patterns=["*.py", "*.js", "*.ts"],
        ),
        ComplianceRule(
            id="PCI-DSS-6.2",
            framework=ComplianceFramework.PCI_DSS,
            name="Security Patches",
            description="All system components must have latest security patches",
            severity=RuleSeverity.HIGH,
            category="patching",
            file_patterns=["requirements.txt", "package.json"],
        ),
    ]
    
    # HIPAA Rules
    HIPAA_RULES = [
        ComplianceRule(
            id="HIPAA-164.312(a)(1)",
            framework=ComplianceFramework.HIPAA,
            name="Access Control",
            description="Implement technical policies for PHI access control",
            severity=RuleSeverity.CRITICAL,
            category="access_control",
            pattern=r"def\s+get_patient|def\s+access_phi.*(?!@require_auth|@login_required)",
            file_patterns=["*.py", "*.js"],
        ),
        ComplianceRule(
            id="HIPAA-164.312(e)(1)",
            framework=ComplianceFramework.HIPAA,
            name="Transmission Security",
            description="PHI transmission must be encrypted",
            severity=RuleSeverity.CRITICAL,
            category="encryption",
            pattern=r"http://.*(?:patient|phi|health)",
            file_patterns=["*.py", "*.js", "*.ts"],
        ),
        ComplianceRule(
            id="HIPAA-164.308(a)(5)",
            framework=ComplianceFramework.HIPAA,
            name="Security Awareness Training",
            description="Implement security awareness procedures",
            severity=RuleSeverity.MEDIUM,
            category="training",
        ),
        ComplianceRule(
            id="HIPAA-164.312(b)",
            framework=ComplianceFramework.HIPAA,
            name="Audit Controls",
            description="Implement audit trail for PHI access",
            severity=RuleSeverity.HIGH,
            category="audit",
            pattern=r"get_patient|access_phi.*(?!log|audit)",
            file_patterns=["*.py", "*.js"],
        ),
    ]
    
    # GDPR Rules
    GDPR_RULES = [
        ComplianceRule(
            id="GDPR-Article-25",
            framework=ComplianceFramework.GDPR,
            name="Data Protection by Design",
            description="Implement data protection from the design phase",
            severity=RuleSeverity.HIGH,
            category="privacy",
        ),
        ComplianceRule(
            id="GDPR-Article-17",
            framework=ComplianceFramework.GDPR,
            name="Right to Erasure",
            description="Users must be able to request data deletion",
            severity=RuleSeverity.CRITICAL,
            category="privacy",
            pattern=r"def\s+delete_user.*(?!cascade|related_data)",
            file_patterns=["*.py", "*.js"],
        ),
        ComplianceRule(
            id="GDPR-Article-32",
            framework=ComplianceFramework.GDPR,
            name="Security of Processing",
            description="Implement appropriate security measures",
            severity=RuleSeverity.CRITICAL,
            category="security",
            pattern=r"password.*(?!hash|encrypt|bcrypt)",
            file_patterns=["*.py", "*.js", "*.ts"],
        ),
        ComplianceRule(
            id="GDPR-Article-15",
            framework=ComplianceFramework.GDPR,
            name="Right of Access",
            description="Users must be able to access their data",
            severity=RuleSeverity.HIGH,
            category="privacy",
        ),
    ]
    
    def __init__(self, frameworks: List[ComplianceFramework] = None):
        """
        Initialize compliance rules engine
        
        Args:
            frameworks: List of frameworks to check (default: all)
        """
        self.frameworks = frameworks or list(ComplianceFramework)
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[ComplianceRule]:
        """Load rules for selected frameworks"""
        all_rules = []
        
        if ComplianceFramework.PCI_DSS in self.frameworks:
            all_rules.extend(self.PCI_DSS_RULES)
        if ComplianceFramework.HIPAA in self.frameworks:
            all_rules.extend(self.HIPAA_RULES)
        if ComplianceFramework.GDPR in self.frameworks:
            all_rules.extend(self.GDPR_RULES)
        
        return [rule for rule in all_rules if rule.enabled]
    
    def check_code(self, file_path: str, code: str) -> List[ComplianceViolation]:
        """
        Check code against compliance rules
        
        Args:
            file_path: Path to the file being checked
            code: Source code content
            
        Returns:
            List of compliance violations
        """
        violations = []
        
        for rule in self.rules:
            # Check if file matches rule patterns
            if not self._matches_file_pattern(file_path, rule.file_patterns):
                continue
            
            # Check pattern if defined
            if rule.pattern:
                matches = re.finditer(rule.pattern, code, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    # Calculate line number
                    line_number = code[:match.start()].count('\n') + 1
                    
                    violation = ComplianceViolation(
                        rule_id=rule.id,
                        framework=rule.framework,
                        severity=rule.severity,
                        file_path=file_path,
                        line_number=line_number,
                        message=rule.description,
                        evidence=match.group(0),
                        remediation=self._get_remediation(rule.id),
                    )
                    violations.append(violation)
        
        return violations
    
    def _matches_file_pattern(self, file_path: str, patterns: List[str]) -> bool:
        """Check if file path matches any pattern"""
        if not patterns:
            return True
        
        import fnmatch
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in patterns)
    
    def _get_remediation(self, rule_id: str) -> str:
        """Get remediation advice for a rule"""
        remediations = {
            "PCI-DSS-6.5.1": "Use parameterized queries or prepared statements instead of string concatenation",
            "PCI-DSS-3.4": "Encrypt cardholder data using AES-256 or stronger algorithm",
            "PCI-DSS-8.2.3": "Implement strong password policy: min 8 chars, uppercase, lowercase, digit, special char",
            "HIPAA-164.312(a)(1)": "Add authentication decorator to all PHI access methods",
            "HIPAA-164.312(e)(1)": "Use HTTPS for all PHI transmission",
            "HIPAA-164.312(b)": "Add audit logging to all PHI access methods",
            "GDPR-Article-17": "Implement cascade deletion for all user-related data",
            "GDPR-Article-32": "Hash passwords using bcrypt or Argon2",
        }
        return remediations.get(rule_id, "See compliance framework documentation for remediation")
    
    def generate_report(self, violations: List[ComplianceViolation]) -> Dict[str, Any]:
        """
        Generate compliance report
        
        Args:
            violations: List of detected violations
            
        Returns:
            Compliance report dictionary
        """
        # Group by framework
        by_framework = {}
        for violation in violations:
            framework = violation.framework.value
            if framework not in by_framework:
                by_framework[framework] = []
            by_framework[framework].append(violation)
        
        # Group by severity
        by_severity = {}
        for violation in violations:
            severity = violation.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(violation)
        
        return {
            "total_violations": len(violations),
            "by_framework": {
                framework: len(viols) 
                for framework, viols in by_framework.items()
            },
            "by_severity": {
                severity: len(viols)
                for severity, viols in by_severity.items()
            },
            "critical_count": len(by_severity.get("critical", [])),
            "high_count": len(by_severity.get("high", [])),
            "compliance_score": self._calculate_compliance_score(violations),
            "violations": [v.dict() for v in violations],
        }
    
    def _calculate_compliance_score(self, violations: List[ComplianceViolation]) -> float:
        """
        Calculate compliance score (0-100)
        
        Higher violations = lower score
        """
        if not violations:
            return 100.0
        
        # Weight violations by severity
        weights = {
            RuleSeverity.CRITICAL: 10,
            RuleSeverity.HIGH: 5,
            RuleSeverity.MEDIUM: 2,
            RuleSeverity.LOW: 1,
            RuleSeverity.INFO: 0.5,
        }
        
        total_weight = sum(weights.get(v.severity, 1) for v in violations)
        
        # Score decreases with violations
        score = max(0, 100 - (total_weight * 2))
        
        return round(score, 2)
