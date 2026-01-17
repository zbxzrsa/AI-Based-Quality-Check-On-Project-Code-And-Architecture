#!/usr/bin/env python3
"""
Security Compliance Report Generator

This script processes Bandit SAST output and generates a comprehensive
Security Compliance Report aligned with ISO/IEC 25010 quality standards.

Usage:
    python security_compliance_report.py bandit-report.json --output report.md
    python security_compliance_report.py bandit-report.json --format json --output report.json
"""

import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path
import re


class SecurityComplianceReport:
    """
    Generates security compliance reports from Bandit SAST output
    aligned with ISO/IEC 25010 quality standards.
    """

    # ISO/IEC 25010 Security Characteristics Mapping
    ISO_25010_MAPPING = {
        # Confidentiality (Protection from unauthorized access)
        'B101': {'characteristic': 'Confidentiality', 'severity': 'HIGH',
                'description': 'Use of assert statements'},
        'B102': {'characteristic': 'Confidentiality', 'severity': 'MEDIUM',
                'description': 'Use of exec() function'},
        'B103': {'characteristic': 'Confidentiality', 'severity': 'HIGH',
                'description': 'Use of setattr() with dynamic attribute names'},
        'B104': {'characteristic': 'Confidentiality', 'severity': 'MEDIUM',
                'description': 'Use of hardcoded password strings'},
        'B105': {'characteristic': 'Confidentiality', 'severity': 'HIGH',
                'description': 'Use of hardcoded password function parameters'},
        'B106': {'characteristic': 'Confidentiality', 'severity': 'HIGH',
                'description': 'Use of hardcoded password variable names'},
        'B107': {'characteristic': 'Confidentiality', 'severity': 'HIGH',
                'description': 'Use of hardcoded password default arguments'},

        # Integrity (Protection from unauthorized modification)
        'B201': {'characteristic': 'Integrity', 'severity': 'HIGH',
                'description': 'Use of flask.debug with True'},
        'B301': {'characteristic': 'Integrity', 'severity': 'MEDIUM',
                'description': 'Use of pickle module'},
        'B302': {'characteristic': 'Integrity', 'severity': 'MEDIUM',
                'description': 'Use of marshal module'},
        'B303': {'characteristic': 'Integrity', 'severity': 'HIGH',
                'description': 'Use of insecure deserialization'},
        'B304': {'characteristic': 'Integrity', 'severity': 'HIGH',
                'description': 'Use of insecure deserialization with yaml'},
        'B305': {'characteristic': 'Integrity', 'severity': 'HIGH',
                'description': 'Use of insecure deserialization with jsonpickle'},

        # Availability (Reliability and accessibility)
        'B401': {'characteristic': 'Availability', 'severity': 'MEDIUM',
                'description': 'Use of subprocess with shell=True'},
        'B402': {'characteristic': 'Availability', 'severity': 'LOW',
                'description': 'Use of subprocess with shell=False'},
        'B403': {'characteristic': 'Availability', 'severity': 'HIGH',
                'description': 'Use of pickle and modules that wrap it'},
        'B404': {'characteristic': 'Availability', 'severity': 'MEDIUM',
                'description': 'Use of subprocess module without timeout'},

        # Accountability (Auditability and traceability)
        'B501': {'characteristic': 'Accountability', 'severity': 'LOW',
                'description': 'Use of request without timeout'},
        'B502': {'characteristic': 'Accountability', 'severity': 'LOW',
                'description': 'Use of ssl.wrap_socket without server_hostname'},
        'B503': {'characteristic': 'Accountability', 'severity': 'HIGH',
                'description': 'Use of ssl.wrap_socket with insecure SSL/TLS versions'},

        # Authenticity (Verification of identity and origin)
        'B601': {'characteristic': 'Authenticity', 'severity': 'HIGH',
                'description': 'Use of shell=True in subprocess calls'},
        'B602': {'characteristic': 'Authenticity', 'severity': 'MEDIUM',
                'description': 'Use of subprocess.call with shell=True'},
        'B603': {'characteristic': 'Authenticity', 'severity': 'MEDIUM',
                'description': 'Use of subprocess.Popen with shell=True'},
        'B604': {'characteristic': 'Authenticity', 'severity': 'MEDIUM',
                'description': 'Use of subprocess.run with shell=True'},
        'B605': {'characteristic': 'Authenticity', 'severity': 'HIGH',
                'description': 'Use of os.system, os.popen, os.spawn*'},
        'B606': {'characteristic': 'Authenticity', 'severity': 'HIGH',
                'description': 'Use of os.startfile with shell=True'},
        'B607': {'characteristic': 'Authenticity', 'severity': 'MEDIUM',
                'description': 'Use of os.forkpty, os.popen2, os.popen3, os.popen4'},
    }

    def __init__(self, bandit_report_path: str):
        self.bandit_report_path = Path(bandit_report_path)
        self.report_data = self._load_bandit_report()
        self.compliance_score = self._calculate_compliance_score()

    def _load_bandit_report(self) -> Dict[str, Any]:
        """Load and parse Bandit JSON report."""
        try:
            with open(self.bandit_report_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Bandit report not found: {self.bandit_report_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Bandit report: {e}")

    def _calculate_compliance_score(self) -> float:
        """Calculate overall security compliance score (0-100)."""
        if not self.report_data.get('results'):
            return 100.0  # No issues found

        total_issues = len(self.report_data['results'])
        high_severity = sum(1 for issue in self.report_data['results']
                          if issue.get('issue_severity', '').upper() == 'HIGH')
        medium_severity = sum(1 for issue in self.report_data['results']
                            if issue.get('issue_severity', '').upper() == 'MEDIUM')
        low_severity = sum(1 for issue in self.report_data['results']
                         if issue.get('issue_severity', '').upper() == 'LOW')

        # Scoring: HIGH = -10 points, MEDIUM = -5 points, LOW = -2 points
        penalty = (high_severity * 10) + (medium_severity * 5) + (low_severity * 2)
        score = max(0, 100 - penalty)

        return round(score, 1)

    def categorize_by_iso_25010(self) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize vulnerabilities by ISO/IEC 25010 security characteristics."""
        categories = {
            'Confidentiality': [],
            'Integrity': [],
            'Availability': [],
            'Accountability': [],
            'Authenticity': [],
            'Other': []
        }

        for issue in self.report_data.get('results', []):
            test_id = issue.get('test_id', '')
            iso_info = self.ISO_25010_MAPPING.get(test_id, {})

            category = iso_info.get('characteristic', 'Other')
            categories[category].append({
                'test_id': test_id,
                'filename': issue.get('filename', ''),
                'line_number': issue.get('line_number', 0),
                'issue_severity': issue.get('issue_severity', ''),
                'issue_confidence': issue.get('issue_confidence', ''),
                'issue_text': issue.get('issue_text', ''),
                'description': iso_info.get('description', 'Unknown security issue'),
                'iso_characteristic': category
            })

        return categories

    def get_critical_vulnerabilities(self) -> List[Dict[str, Any]]:
        """Get only critical/high-severity vulnerabilities."""
        return [issue for issue in self.report_data.get('results', [])
                if issue.get('issue_severity', '').upper() == 'HIGH']

    def generate_markdown_report(self) -> str:
        """Generate comprehensive Markdown security compliance report."""
        timestamp = datetime.now().isoformat()
        categories = self.categorize_by_iso_25010()
        critical_issues = self.get_critical_vulnerabilities()

        report = f"""# 🔒 Security Compliance Report

**Generated:** {timestamp}
**Compliance Score:** {self.compliance_score}/100
**Bandit Report:** `{self.bandit_report_path.name}`

## 📊 Executive Summary

### Overall Assessment
- **Compliance Score:** {self.compliance_score}/100 ({self._get_score_rating()})
- **Total Issues:** {len(self.report_data.get('results', []))}
- **Critical Issues:** {len(critical_issues)}
- **Files Scanned:** {len(set(issue.get('filename') for issue in self.report_data.get('results', [])))}

### Risk Assessment
{self._generate_risk_assessment(critical_issues)}

## 🚨 Critical Security Issues

{self._format_critical_issues(critical_issues)}

## 🔍 ISO/IEC 25010 Security Analysis

{self._format_iso_categories(categories)}

## 📋 Recommendations

### Immediate Actions Required
{self._generate_recommendations(critical_issues)}

### Long-term Security Improvements
{self._generate_long_term_recommendations()}

## 📈 Compliance Trends

### Historical Comparison
*This section would show trends if multiple reports are compared*

### Target Compliance Levels
- **Critical Issues:** 0 (Zero tolerance)
- **High Severity:** < 5 per 1000 lines of code
- **Overall Score:** > 85/100

---

*Report generated by Security Compliance Analyzer*
*Aligned with ISO/IEC 25010 quality standards*
"""

        return report

    def generate_json_report(self) -> Dict[str, Any]:
        """Generate structured JSON report."""
        return {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'bandit_report': str(self.bandit_report_path),
                'compliance_score': self.compliance_score,
                'score_rating': self._get_score_rating()
            },
            'summary': {
                'total_issues': len(self.report_data.get('results', [])),
                'critical_issues': len(self.get_critical_vulnerabilities()),
                'files_scanned': len(set(issue.get('filename') for issue in self.report_data.get('results', []))),
                'high_severity': sum(1 for issue in self.report_data.get('results', []) if issue.get('issue_severity', '').upper() == 'HIGH'),
                'medium_severity': sum(1 for issue in self.report_data.get('results', []) if issue.get('issue_severity', '').upper() == 'MEDIUM'),
                'low_severity': sum(1 for issue in self.report_data.get('results', []) if issue.get('issue_severity', '').upper() == 'LOW')
            },
            'iso_25010_analysis': self.categorize_by_iso_25010(),
            'critical_issues': self.get_critical_vulnerabilities(),
            'recommendations': {
                'immediate': self._generate_recommendations(self.get_critical_vulnerabilities()),
                'long_term': self._generate_long_term_recommendations()
            }
        }

    def _get_score_rating(self) -> str:
        """Get compliance score rating."""
        if self.compliance_score >= 90:
            return "Excellent"
        elif self.compliance_score >= 80:
            return "Good"
        elif self.compliance_score >= 70:
            return "Fair"
        elif self.compliance_score >= 60:
            return "Poor"
        else:
            return "Critical"

    def _generate_risk_assessment(self, critical_issues: List[Dict]) -> str:
        """Generate risk assessment section."""
        if not critical_issues:
            return "✅ **No critical security vulnerabilities detected.** The codebase demonstrates strong security practices."
        else:
            risk_level = "HIGH" if len(critical_issues) > 5 else "MEDIUM" if len(critical_issues) > 2 else "LOW"
            return f"""⚠️ **{risk_level} RISK:** {len(critical_issues)} critical security vulnerabilities require immediate attention.

**Impact Assessment:**
- Potential data breaches or unauthorized access
- System compromise through injection attacks
- Loss of confidentiality, integrity, or availability
- Compliance violations and regulatory penalties"""

    def _format_critical_issues(self, critical_issues: List[Dict]) -> str:
        """Format critical issues for Markdown."""
        if not critical_issues:
            return "✅ No critical security issues found."

        issues_md = ""
        for i, issue in enumerate(critical_issues, 1):
            issues_md += f"""### {i}. {issue.get('test_name', 'Unknown Issue')}
- **File:** `{issue.get('filename', 'Unknown')}`
- **Line:** {issue.get('line_number', 'Unknown')}
- **Severity:** {issue.get('issue_severity', 'Unknown')}
- **Confidence:** {issue.get('issue_confidence', 'Unknown')}
- **Description:** {issue.get('issue_text', '')}
- **ISO/IEC 25010:** {self.ISO_25010_MAPPING.get(issue.get('test_id', ''), {}).get('characteristic', 'Other')}

"""

        return issues_md

    def _format_iso_categories(self, categories: Dict[str, List]) -> str:
        """Format ISO 25010 categories for Markdown."""
        md = ""

        for characteristic, issues in categories.items():
            if not issues:
                continue

            md += f"### {characteristic}\n\n"
            md += f"**Issues Found:** {len(issues)}\n\n"

            for issue in issues:
                md += f"""- **{issue['test_id']}**: {issue['description']}
  - File: `{issue['filename']}:{issue['line_number']}`
  - Severity: {issue['issue_severity']} | Confidence: {issue['issue_confidence']}

"""

        return md

    def _generate_recommendations(self, critical_issues: List[Dict]) -> str:
        """Generate immediate action recommendations."""
        recommendations = []

        if critical_issues:
            recommendations.extend([
                "🔴 **CRITICAL:** Address all high-severity vulnerabilities immediately",
                "🔴 **CRITICAL:** Implement proper input validation and sanitization",
                "🔴 **CRITICAL:** Review and update dependency versions",
                "🟡 **HIGH:** Implement security code reviews for all changes",
                "🟡 **HIGH:** Add security testing to CI/CD pipeline"
            ])

        # Check for specific issue types
        issue_types = set(issue.get('test_id', '') for issue in critical_issues)

        if any('B10' in tid for tid in issue_types):  # Password issues
            recommendations.append("🔴 **CRITICAL:** Remove all hardcoded credentials and use environment variables")

        if any('B30' in tid for tid in issue_types):  # Serialization issues
            recommendations.append("🟡 **HIGH:** Replace pickle usage with safer serialization methods (JSON, msgpack)")

        if any('B60' in tid for tid in issue_types):  # Subprocess issues
            recommendations.append("🟡 **HIGH:** Use subprocess with shell=False and proper argument lists")

        return "\n".join(f"- {rec}" for rec in recommendations)

    def _generate_long_term_recommendations(self) -> str:
        """Generate long-term security improvement recommendations."""
        return """
- 🔵 Implement automated security testing in CI/CD
- 🔵 Establish security code review checklists
- 🔵 Regular dependency vulnerability scanning
- 🔵 Security awareness training for development team
- 🔵 Implement threat modeling for new features
- 🔵 Regular security audits and penetration testing
- 🔵 Adopt secure coding standards and guidelines
- 🔵 Implement security monitoring and alerting"""


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Security Compliance Report from Bandit SAST output"
    )
    parser.add_argument('bandit_report', help='Path to Bandit JSON report file')
    parser.add_argument('--output', '-o', required=True, help='Output file path')
    parser.add_argument('--format', '-f', choices=['markdown', 'json'],
                       default='markdown', help='Output format (default: markdown)')

    args = parser.parse_args()

    try:
        report = SecurityComplianceReport(args.bandit_report)

        if args.format == 'json':
            output_data = report.generate_json_report()
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
        else:
            output_content = report.generate_markdown_report()
            with open(args.output, 'w') as f:
                f.write(output_content)

        print(f"✅ Security Compliance Report generated: {args.output}")
        print(f"📊 Compliance Score: {report.compliance_score}/100")

        critical_count = len(report.get_critical_vulnerabilities())
        if critical_count > 0:
            print(f"🚨 Critical Issues: {critical_count} - IMMEDIATE ACTION REQUIRED")

    except Exception as e:
        print(f"❌ Error generating report: {e}")
        exit(1)


if __name__ == "__main__":
    main()
