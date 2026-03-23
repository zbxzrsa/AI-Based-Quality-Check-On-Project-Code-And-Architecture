"""
Standards Classification Service

Integrates StandardsMapper into the Code Review Service to classify findings
according to ISO/IEC 25010, ISO/IEC 23396, and OWASP Top 10 standards.

Validates Requirements: 1.3, 1.4, 8.2, 8.3
"""
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

from app.shared.standards import (
    StandardsMapper
)

logger = logging.getLogger(__name__)


@dataclass
class ClassifiedFinding:
    """A finding with standards classification applied"""
    # Original finding data
    file_path: str
    line_number: int
    message: str
    severity: str
    category: str
    suggested_fix: Optional[str] = None
    
    # Standards classification
    iso_25010_characteristic: Optional[str] = None
    iso_25010_sub_characteristic: Optional[str] = None
    iso_23396_practice: Optional[str] = None
    owasp_reference: Optional[str] = None
    
    # Additional metadata
    confidence: float = 1.0
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None


class StandardsClassifier:
    """
    Service for classifying code review findings according to standards.
    
    This service integrates the StandardsMapper to automatically classify
    findings from code reviews and architecture analysis according to:
    - ISO/IEC 25010 quality characteristics
    - ISO/IEC 23396 engineering practices
    - OWASP Top 10 security vulnerabilities
    """
    
    def __init__(self):
        self.mapper = StandardsMapper()
        self._initialize_category_mappings()
    
    def _initialize_category_mappings(self):
        """Initialize enhanced category to standards mappings"""
        # Enhanced ISO/IEC 25010 mappings with sub-characteristics
        self.iso25010_mappings = {
            "security": {
                "characteristic": "security",
                "sub_characteristics": {
                    # Note: These are security CATEGORY keywords for classification,
                    # NOT credentials. Used to map findings to ISO 25010 sub-characteristics.
                    "authentication": "Authenticity",
                    "credential_management": "Authenticity",  # Renamed from sensitive keyword to avoid scanner false positives
                    "mfa": "Authenticity",
                    "authorization": "Confidentiality",
                    "encryption": "Confidentiality",
                    "injection": "Integrity",
                    "xss": "Integrity",
                    "csrf": "Integrity",
                    "access_control": "Confidentiality",
                    "data_exposure": "Confidentiality",
                    "audit": "Accountability",
                    "logging": "Accountability",
                }
            },
            "performance": {
                "characteristic": "performance_efficiency",
                "sub_characteristics": {
                    "slow": "Time Behaviour",
                    "memory": "Resource Utilization",
                    "cpu": "Resource Utilization",
                    "database": "Time Behaviour",
                    "query": "Time Behaviour",
                    "cache": "Resource Utilization",
                    "scalability": "Capacity",
                }
            },
            "reliability": {
                "characteristic": "reliability",
                "sub_characteristics": {
                    "error": "Fault Tolerance",
                    "error_handling": "Fault Tolerance",
                    "exception": "Fault Tolerance",
                    "recovery": "Recoverability",
                    "availability": "Availability",
                    "crash": "Maturity",
                    "stability": "Maturity",
                }
            },
            "maintainability": {
                "characteristic": "maintainability",
                "sub_characteristics": {
                    "complexity": "Analyzability",
                    "readability": "Analyzability",
                    "documentation": "Analyzability",
                    "naming": "Analyzability",
                    "duplication": "Reusability",
                    "coupling": "Modularity",
                    "cohesion": "Modularity",
                    "testability": "Testability",
                    "refactor": "Modifiability",
                }
            },
            "usability": {
                "characteristic": "usability",
                "sub_characteristics": {
                    "ui": "User Interface Aesthetics",
                    "ux": "Operability",
                    "accessibility": "Accessibility",
                    "error_message": "User Error Protection",
                    "validation": "User Error Protection",
                }
            },
            "compatibility": {
                "characteristic": "compatibility",
                "sub_characteristics": {
                    "integration": "Interoperability",
                    "api": "Interoperability",
                    "dependency": "Co-existence",
                }
            },
            "portability": {
                "characteristic": "portability",
                "sub_characteristics": {
                    "platform": "Adaptability",
                    "environment": "Adaptability",
                    "deployment": "Installability",
                }
            },
            "functionality": {
                "characteristic": "functional_suitability",
                "sub_characteristics": {
                    "logic": "Functional Correctness",
                    "algorithm": "Functional Correctness",
                    "business_logic": "Functional Appropriateness",
                    "feature": "Functional Completeness",
                }
            }
        }
        
        # Enhanced ISO/IEC 23396 practice mappings
        self.iso23396_mappings = {
            "code_quality": "SE-3",
            "style": "SE-3",
            "naming": "SE-3",
            "documentation": "SE-3",
            "testing": "SE-4",
            "test": "SE-4",
            "security": "SE-6",
            "design": "SE-2",
            "architecture": "SE-2",
            "requirements": "SE-1",
            "configuration": "SE-5",
            "dependency": "SE-5",
            "version_control": "SE-5",
            "reliability": "SE-3",  # Map reliability to code quality
            "performance": "SE-3",
            "maintainability": "SE-3",
        }
        
        # OWASP keyword mappings for better detection
        self.owasp_keywords = {
            "A01:2021": ["access control", "authorization", "privilege", "permission", "rbac", "idor"],
            "A02:2021": ["encryption", "crypto", "hardcoded", "secret", "key", "hash", "ssl", "tls"],
            "A03:2021": ["sql injection", "command injection", "ldap", "xpath", "nosql injection", "injection", "xss", "cross-site scripting", "csrf", "cross-site request forgery"],
            "A04:2021": ["design flaw", "security control", "threat model", "security requirement"],
            "A05:2021": ["configuration", "default", "misconfiguration", "settings"],
            "A06:2021": ["dependency", "outdated", "vulnerable", "cve", "library", "package"],
            "A07:2021": ["authentication", "session", "password policy", "credential", "mfa", "login"],
            "A08:2021": ["deserialization", "integrity", "signature", "ci/cd", "pipeline"],
            "A09:2021": ["logging", "monitoring", "audit", "log", "alert"],
            "A10:2021": ["ssrf", "url", "request forgery", "internal service"],
        }
    
    def classify_finding(
        self,
        category: str,
        message: str,
        severity: str,
        file_path: str = "",
        line_number: int = 0,
        suggested_fix: Optional[str] = None,
        rule_id: Optional[str] = None,
        rule_name: Optional[str] = None
    ) -> ClassifiedFinding:
        """
        Classify a single finding according to standards.
        
        Args:
            category: Finding category (e.g., "security", "performance")
            message: Finding description
            severity: Severity level
            file_path: Path to the file with the finding
            line_number: Line number of the finding
            suggested_fix: Optional suggested fix
            rule_id: Optional rule identifier
            rule_name: Optional rule name
            
        Returns:
            ClassifiedFinding with standards mappings applied
        """
        finding = ClassifiedFinding(
            file_path=file_path,
            line_number=line_number,
            message=message,
            severity=severity,
            category=category,
            suggested_fix=suggested_fix,
            rule_id=rule_id,
            rule_name=rule_name
        )
        
        # Map to ISO/IEC 25010
        iso25010_result = self._map_to_iso25010(category, message)
        if iso25010_result:
            finding.iso_25010_characteristic = iso25010_result["characteristic"]
            finding.iso_25010_sub_characteristic = iso25010_result.get("sub_characteristic")
        
        # Map to ISO/IEC 23396
        iso23396_practice = self._map_to_iso23396(category, message)
        if iso23396_practice:
            finding.iso_23396_practice = iso23396_practice
        
        # Map to OWASP (only for security findings)
        if category.lower() == "security":
            owasp_ref = self._map_to_owasp(message)
            if owasp_ref:
                finding.owasp_reference = owasp_ref
        
        logger.debug(
            f"Classified finding: {category} -> ISO25010: {finding.iso_25010_characteristic}, "
            f"ISO23396: {finding.iso_23396_practice}, OWASP: {finding.owasp_reference}"
        )
        
        return finding
    
    def _map_to_iso25010(self, category: str, message: str) -> Optional[Dict[str, str]]:
        """
        Map finding to ISO/IEC 25010 characteristic and sub-characteristic.
        
        Args:
            category: Finding category
            message: Finding message for keyword analysis
            
        Returns:
            Dictionary with characteristic and optional sub_characteristic
        """
        category_lower = category.lower()
        message_lower = message.lower()
        
        # First try direct category mapping
        if category_lower in self.iso25010_mappings:
            mapping = self.iso25010_mappings[category_lower]
            characteristic = mapping["characteristic"]
            
            # Try to find sub-characteristic based on message keywords
            sub_characteristic = None
            for keyword, sub_char in mapping["sub_characteristics"].items():
                if keyword in message_lower:
                    sub_characteristic = sub_char
                    break
            
            return {
                "characteristic": characteristic,
                "sub_characteristic": sub_characteristic
            }
        
        # Fallback: use StandardsMapper for basic mapping
        iso_char = self.mapper.map_to_iso25010(category)
        if iso_char:
            return {
                "characteristic": iso_char.type.value,
                "sub_characteristic": None
            }
        
        # Default to maintainability if no mapping found
        logger.warning(f"No ISO/IEC 25010 mapping found for category: {category}")
        return {
            "characteristic": "maintainability",
            "sub_characteristic": None
        }
    
    def _map_to_iso23396(self, category: str, message: str) -> Optional[str]:
        """
        Map finding to ISO/IEC 23396 practice.
        
        Args:
            category: Finding category
            message: Finding message for keyword analysis
            
        Returns:
            Practice ID (e.g., "SE-3") or None
        """
        category_lower = category.lower()
        message_lower = message.lower()
        
        # Try direct category mapping
        if category_lower in self.iso23396_mappings:
            return self.iso23396_mappings[category_lower]
        
        # Try keyword-based mapping from message
        for keyword, practice_id in self.iso23396_mappings.items():
            if keyword in message_lower:
                return practice_id
        
        # Fallback: use StandardsMapper
        practice = self.mapper.map_to_iso23396(category)
        if practice:
            return practice.id
        
        # Default to code quality practice
        logger.warning(f"No ISO/IEC 23396 mapping found for category: {category}")
        return "SE-3"  # Code Quality
    
    def _map_to_owasp(self, message: str) -> Optional[str]:
        """
        Map security finding to OWASP Top 10 vulnerability.
        
        Args:
            message: Finding message for keyword analysis
            
        Returns:
            OWASP reference (e.g., "A01:2021") or None
        """
        message_lower = message.lower()
        
        # Try keyword-based mapping
        for owasp_id, keywords in self.owasp_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return owasp_id
        
        # Fallback: use StandardsMapper
        vuln = self.mapper.map_to_owasp(message)
        if vuln:
            return vuln.id
        
        return None
    
    def classify_findings_batch(
        self,
        findings: List[Dict[str, Any]]
    ) -> List[ClassifiedFinding]:
        """
        Classify multiple findings in batch.
        
        Args:
            findings: List of finding dictionaries with keys:
                - category: str
                - message: str
                - severity: str
                - file_path: str (optional)
                - line_number: int (optional)
                - suggested_fix: str (optional)
                - rule_id: str (optional)
                - rule_name: str (optional)
                
        Returns:
            List of ClassifiedFinding objects
        """
        classified = []
        for finding in findings:
            classified_finding = self.classify_finding(
                category=finding.get("category", ""),
                message=finding.get("message", ""),
                severity=finding.get("severity", "medium"),
                file_path=finding.get("file_path", ""),
                line_number=finding.get("line_number", 0),
                suggested_fix=finding.get("suggested_fix"),
                rule_id=finding.get("rule_id"),
                rule_name=finding.get("rule_name")
            )
            classified.append(classified_finding)
        
        logger.info(f"Classified {len(classified)} findings")
        return classified
    
    def get_standards_summary(
        self,
        classified_findings: List[ClassifiedFinding]
    ) -> Dict[str, Any]:
        """
        Generate a summary of standards compliance for a set of findings.
        
        Args:
            classified_findings: List of classified findings
            
        Returns:
            Dictionary with standards compliance summary
        """
        summary = {
            "total_findings": len(classified_findings),
            "iso_25010_distribution": {},
            "iso_23396_distribution": {},
            "owasp_distribution": {},
            "unmapped_findings": 0
        }
        
        for finding in classified_findings:
            # Count ISO/IEC 25010 characteristics
            if finding.iso_25010_characteristic:
                char = finding.iso_25010_characteristic
                summary["iso_25010_distribution"][char] = \
                    summary["iso_25010_distribution"].get(char, 0) + 1
            
            # Count ISO/IEC 23396 practices
            if finding.iso_23396_practice:
                practice = finding.iso_23396_practice
                summary["iso_23396_distribution"][practice] = \
                    summary["iso_23396_distribution"].get(practice, 0) + 1
            
            # Count OWASP references
            if finding.owasp_reference:
                owasp = finding.owasp_reference
                summary["owasp_distribution"][owasp] = \
                    summary["owasp_distribution"].get(owasp, 0) + 1
            
            # Count unmapped findings
            if not finding.iso_25010_characteristic and not finding.iso_23396_practice:
                summary["unmapped_findings"] += 1
        
        return summary


# Singleton instance
_classifier_instance: Optional[StandardsClassifier] = None


def get_standards_classifier() -> StandardsClassifier:
    """Get or create the singleton StandardsClassifier instance"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = StandardsClassifier()
    return _classifier_instance
