"""
Standards data models for ISO/IEC 25010, ISO/IEC 23396, and OWASP Top 10

Provides structured representations of software quality standards for
classification and compliance reporting.

Validates Requirements: 1.3, 1.4, 1.6, 8.1, 8.2, 8.3
"""

from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field


class ISO25010CharacteristicType(str, Enum):
    """ISO/IEC 25010 Quality Characteristics"""
    FUNCTIONAL_SUITABILITY = "functional_suitability"
    PERFORMANCE_EFFICIENCY = "performance_efficiency"
    COMPATIBILITY = "compatibility"
    USABILITY = "usability"
    RELIABILITY = "reliability"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    PORTABILITY = "portability"


@dataclass
class ISO25010SubCharacteristic:
    """ISO/IEC 25010 Sub-characteristic"""
    name: str
    description: str
    metrics: List[str] = field(default_factory=list)


@dataclass
class ISO25010Characteristic:
    """ISO/IEC 25010 Quality Characteristic with sub-characteristics"""
    type: ISO25010CharacteristicType
    name: str
    description: str
    sub_characteristics: List[ISO25010SubCharacteristic] = field(default_factory=list)
    
    @classmethod
    def get_all_characteristics(cls) -> List["ISO25010Characteristic"]:
        """Get all ISO/IEC 25010 quality characteristics"""
        return [
            cls(
                type=ISO25010CharacteristicType.FUNCTIONAL_SUITABILITY,
                name="Functional Suitability",
                description="Degree to which a product provides functions that meet stated and implied needs",
                sub_characteristics=[
                    ISO25010SubCharacteristic("Functional Completeness", "Degree to which functions cover all specified tasks"),
                    ISO25010SubCharacteristic("Functional Correctness", "Degree to which product provides correct results"),
                    ISO25010SubCharacteristic("Functional Appropriateness", "Degree to which functions facilitate specified tasks"),
                ]
            ),
            cls(
                type=ISO25010CharacteristicType.PERFORMANCE_EFFICIENCY,
                name="Performance Efficiency",
                description="Performance relative to the amount of resources used",
                sub_characteristics=[
                    ISO25010SubCharacteristic("Time Behaviour", "Response and processing times"),
                    ISO25010SubCharacteristic("Resource Utilization", "Amounts and types of resources used"),
                    ISO25010SubCharacteristic("Capacity", "Maximum limits of product parameters"),
                ]
            ),
            cls(
                type=ISO25010CharacteristicType.COMPATIBILITY,
                name="Compatibility",
                description="Degree to which a product can exchange information with other products",
                sub_characteristics=[
                    ISO25010SubCharacteristic("Co-existence", "Can perform required functions while sharing environment"),
                    ISO25010SubCharacteristic("Interoperability", "Can exchange and use information"),
                ]
            ),
            cls(
                type=ISO25010CharacteristicType.USABILITY,
                name="Usability",
                description="Degree to which a product can be used by specified users",
                sub_characteristics=[
                    ISO25010SubCharacteristic("Appropriateness Recognizability", "Users can recognize if suitable"),
                    ISO25010SubCharacteristic("Learnability", "Can be learned to use"),
                    ISO25010SubCharacteristic("Operability", "Easy to operate and control"),
                    ISO25010SubCharacteristic("User Error Protection", "Protects users against making errors"),
                    ISO25010SubCharacteristic("User Interface Aesthetics", "Pleasing and satisfying interaction"),
                    ISO25010SubCharacteristic("Accessibility", "Can be used by people with widest range of characteristics"),
                ]
            ),
            cls(
                type=ISO25010CharacteristicType.RELIABILITY,
                name="Reliability",
                description="Degree to which a system performs specified functions under specified conditions",
                sub_characteristics=[
                    ISO25010SubCharacteristic("Maturity", "Meets needs for reliability under normal operation"),
                    ISO25010SubCharacteristic("Availability", "Operational and accessible when required"),
                    ISO25010SubCharacteristic("Fault Tolerance", "Operates despite hardware or software faults"),
                    ISO25010SubCharacteristic("Recoverability", "Can recover data and re-establish desired state"),
                ]
            ),
            cls(
                type=ISO25010CharacteristicType.SECURITY,
                name="Security",
                description="Degree to which a product protects information and data",
                sub_characteristics=[
                    ISO25010SubCharacteristic("Confidentiality", "Ensures data accessible only to authorized"),
                    ISO25010SubCharacteristic("Integrity", "Prevents unauthorized access or modification"),
                    ISO25010SubCharacteristic("Non-repudiation", "Actions or events can be proven"),
                    ISO25010SubCharacteristic("Accountability", "Actions can be traced uniquely"),
                    ISO25010SubCharacteristic("Authenticity", "Identity of subject can be proved"),
                ]
            ),
            cls(
                type=ISO25010CharacteristicType.MAINTAINABILITY,
                name="Maintainability",
                description="Degree of effectiveness and efficiency with which a product can be modified",
                sub_characteristics=[
                    ISO25010SubCharacteristic("Modularity", "Composed of discrete components"),
                    ISO25010SubCharacteristic("Reusability", "Asset can be used in more than one system"),
                    ISO25010SubCharacteristic("Analyzability", "Impact of change can be assessed"),
                    ISO25010SubCharacteristic("Modifiability", "Can be modified without introducing defects"),
                    ISO25010SubCharacteristic("Testability", "Test criteria can be established and tests performed"),
                ]
            ),
            cls(
                type=ISO25010CharacteristicType.PORTABILITY,
                name="Portability",
                description="Degree of effectiveness and efficiency with which a system can be transferred",
                sub_characteristics=[
                    ISO25010SubCharacteristic("Adaptability", "Can be adapted for different environments"),
                    ISO25010SubCharacteristic("Installability", "Can be successfully installed/uninstalled"),
                    ISO25010SubCharacteristic("Replaceability", "Can replace another specified software product"),
                ]
            ),
        ]


@dataclass
class ISO23396Practice:
    """ISO/IEC 23396 Software Engineering Practice"""
    id: str
    name: str
    description: str
    category: str
    guidelines: List[str] = field(default_factory=list)
    
    @classmethod
    def get_common_practices(cls) -> List["ISO23396Practice"]:
        """Get common ISO/IEC 23396 practices"""
        return [
            cls(
                id="SE-1",
                name="Requirements Engineering",
                description="Systematic approach to eliciting, documenting, and managing requirements",
                category="Requirements",
                guidelines=["Define clear requirements", "Validate with stakeholders", "Maintain traceability"]
            ),
            cls(
                id="SE-2",
                name="Software Design",
                description="Architectural and detailed design of software systems",
                category="Design",
                guidelines=["Follow design principles", "Document architecture", "Review designs"]
            ),
            cls(
                id="SE-3",
                name="Code Quality",
                description="Practices for writing maintainable, readable code",
                category="Implementation",
                guidelines=["Follow coding standards", "Write self-documenting code", "Perform code reviews"]
            ),
            cls(
                id="SE-4",
                name="Testing Practices",
                description="Comprehensive testing strategies and methodologies",
                category="Testing",
                guidelines=["Write unit tests", "Perform integration testing", "Automate testing"]
            ),
            cls(
                id="SE-5",
                name="Configuration Management",
                description="Managing changes to software artifacts",
                category="Management",
                guidelines=["Use version control", "Manage dependencies", "Track changes"]
            ),
            cls(
                id="SE-6",
                name="Security Practices",
                description="Secure software development practices",
                category="Security",
                guidelines=["Follow secure coding guidelines", "Perform security reviews", "Handle sensitive data properly"]
            ),
        ]


@dataclass
class OWASPVulnerability:
    """OWASP Top 10 Vulnerability"""
    rank: int
    id: str
    name: str
    description: str
    examples: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)
    
    @classmethod
    def get_owasp_top_10_2021(cls) -> List["OWASPVulnerability"]:
        """Get OWASP Top 10 2021 vulnerabilities"""
        return [
            cls(
                rank=1,
                id="A01:2021",
                name="Broken Access Control",
                description="Failures related to access control allowing unauthorized access",
                examples=["Missing access control checks", "Insecure direct object references", "Privilege escalation"],
                mitigations=["Implement proper authorization", "Deny by default", "Log access control failures"]
            ),
            cls(
                rank=2,
                id="A02:2021",
                name="Cryptographic Failures",
                description="Failures related to cryptography leading to sensitive data exposure",
                examples=["Weak encryption", "Hardcoded secrets", "Insecure key management"],
                mitigations=["Use strong encryption", "Protect data in transit and at rest", "Proper key management"]
            ),
            cls(
                rank=3,
                id="A03:2021",
                name="Injection",
                description="Injection flaws such as SQL, NoSQL, OS command injection",
                examples=["SQL injection", "Command injection", "LDAP injection"],
                mitigations=["Use parameterized queries", "Input validation", "Escape special characters"]
            ),
            cls(
                rank=4,
                id="A04:2021",
                name="Insecure Design",
                description="Missing or ineffective control design",
                examples=["Missing security controls", "Insecure design patterns", "Threat modeling gaps"],
                mitigations=["Secure design patterns", "Threat modeling", "Security requirements"]
            ),
            cls(
                rank=5,
                id="A05:2021",
                name="Security Misconfiguration",
                description="Missing or incorrect security configuration",
                examples=["Default credentials", "Unnecessary features enabled", "Verbose error messages"],
                mitigations=["Secure configuration", "Remove unnecessary features", "Regular security updates"]
            ),
            cls(
                rank=6,
                id="A06:2021",
                name="Vulnerable and Outdated Components",
                description="Using components with known vulnerabilities",
                examples=["Outdated libraries", "Unpatched dependencies", "Unsupported components"],
                mitigations=["Keep dependencies updated", "Monitor for vulnerabilities", "Remove unused dependencies"]
            ),
            cls(
                rank=7,
                id="A07:2021",
                name="Identification and Authentication Failures",
                description="Failures in authentication and session management",
                examples=["Weak passwords", "Session fixation", "Missing MFA"],
                mitigations=["Strong authentication", "Secure session management", "Implement MFA"]
            ),
            cls(
                rank=8,
                id="A08:2021",
                name="Software and Data Integrity Failures",
                description="Code and infrastructure that doesn't protect against integrity violations",
                examples=["Unsigned updates", "Insecure deserialization", "CI/CD pipeline vulnerabilities"],
                mitigations=["Digital signatures", "Verify integrity", "Secure CI/CD pipelines"]
            ),
            cls(
                rank=9,
                id="A09:2021",
                name="Security Logging and Monitoring Failures",
                description="Insufficient logging and monitoring",
                examples=["Missing logs", "Inadequate monitoring", "No alerting"],
                mitigations=["Comprehensive logging", "Real-time monitoring", "Incident response"]
            ),
            cls(
                rank=10,
                id="A10:2021",
                name="Server-Side Request Forgery (SSRF)",
                description="Fetching remote resources without validating user-supplied URL",
                examples=["Unvalidated URL input", "Internal service access", "Cloud metadata access"],
                mitigations=["Validate and sanitize URLs", "Network segmentation", "Deny by default"]
            ),
        ]


class StandardsMapper:
    """Maps code findings to standards (ISO/IEC 25010, ISO/IEC 23396, OWASP)"""
    
    def __init__(self):
        self.iso25010_characteristics = {char.type: char for char in ISO25010Characteristic.get_all_characteristics()}
        self.iso23396_practices = {practice.id: practice for practice in ISO23396Practice.get_common_practices()}
        self.owasp_vulnerabilities = {vuln.id: vuln for vuln in OWASPVulnerability.get_owasp_top_10_2021()}
    
    def map_to_iso25010(self, finding_category: str) -> Optional[ISO25010Characteristic]:
        """Map a finding category to ISO/IEC 25010 characteristic"""
        category_mapping = {
            "security": ISO25010CharacteristicType.SECURITY,
            "performance": ISO25010CharacteristicType.PERFORMANCE_EFFICIENCY,
            "reliability": ISO25010CharacteristicType.RELIABILITY,
            "maintainability": ISO25010CharacteristicType.MAINTAINABILITY,
            "usability": ISO25010CharacteristicType.USABILITY,
            "compatibility": ISO25010CharacteristicType.COMPATIBILITY,
            "portability": ISO25010CharacteristicType.PORTABILITY,
            "functionality": ISO25010CharacteristicType.FUNCTIONAL_SUITABILITY,
        }
        
        char_type = category_mapping.get(finding_category.lower())
        return self.iso25010_characteristics.get(char_type) if char_type else None
    
    def map_to_iso23396(self, finding_category: str) -> Optional[ISO23396Practice]:
        """Map a finding category to ISO/IEC 23396 practice"""
        category_mapping = {
            "code_quality": "SE-3",
            "testing": "SE-4",
            "security": "SE-6",
            "design": "SE-2",
            "requirements": "SE-1",
            "configuration": "SE-5",
        }
        
        practice_id = category_mapping.get(finding_category.lower())
        return self.iso23396_practices.get(practice_id) if practice_id else None
    
    def map_to_owasp(self, security_issue: str) -> Optional[OWASPVulnerability]:
        """Map a security issue to OWASP Top 10 vulnerability"""
        issue_lower = security_issue.lower()
        
        # Simple keyword-based mapping
        for vuln in self.owasp_vulnerabilities.values():
            if any(keyword in issue_lower for keyword in vuln.name.lower().split()):
                return vuln
            if any(example.lower() in issue_lower for example in vuln.examples):
                return vuln
        
        return None
    
    def get_all_iso25010_characteristics(self) -> List[ISO25010Characteristic]:
        """Get all ISO/IEC 25010 characteristics"""
        return list(self.iso25010_characteristics.values())
    
    def get_all_iso23396_practices(self) -> List[ISO23396Practice]:
        """Get all ISO/IEC 23396 practices"""
        return list(self.iso23396_practices.values())
    
    def get_all_owasp_vulnerabilities(self) -> List[OWASPVulnerability]:
        """Get all OWASP Top 10 vulnerabilities"""
        return list(self.owasp_vulnerabilities.values())
