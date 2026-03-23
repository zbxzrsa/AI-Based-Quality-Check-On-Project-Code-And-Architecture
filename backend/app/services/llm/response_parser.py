"""
LLM Response Parser

Parses LLM text responses into structured review comments with
severity levels, line numbers, and suggestions.

Validates Requirements: 1.4
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
# Import consolidated enums from common library
from common.shared.enums import Severity

logger = logging.getLogger(__name__)


def _severity_from_string(value: str) -> Severity:
    """Parse severity from string, case-insensitive. Defaults to MEDIUM."""
    value_lower = value.lower().strip()
    for severity in Severity:
        if severity.value == value_lower:
            return severity
    return Severity.MEDIUM

# Monkey-patch from_string for backward compatibility
Severity.from_string = classmethod(lambda cls, v: _severity_from_string(v))

@dataclass
class ReviewComment:
    """
    Structured review comment from LLM analysis.
    
    Attributes:
        severity: Issue severity (critical, high, medium, low, info)
        file_path: Path to the file
        line_start: Starting line number (optional)
        line_end: Ending line number (optional)
        issue: Description of the issue
        suggestion: Recommended fix or improvement
        rationale: Explanation of why this matters
        category: Optional category (e.g., "security", "performance")
        raw_text: Original text from LLM response
    """
    severity: Severity
    file_path: str
    issue: str
    suggestion: str
    rationale: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    category: Optional[str] = None
    raw_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result["severity"] = self.severity.value
        return result
    
    def __str__(self) -> str:
        """String representation"""
        location = self.file_path
        if self.line_start:
            if self.line_end and self.line_end != self.line_start:
                location += f":{self.line_start}-{self.line_end}"
            else:
                location += f":{self.line_start}"
        
        return (
            f"[{self.severity.value.upper()}] {location}\n"
            f"Issue: {self.issue}\n"
            f"Suggestion: {self.suggestion}\n"
            f"Rationale: {self.rationale}"
        )


@dataclass
class ParseResult:
    """
    Result of parsing LLM response.
    
    Attributes:
        comments: List of successfully parsed review comments
        errors: List of parsing errors encountered
        raw_response: Original LLM response text
        success: Whether parsing was successful
    """
    comments: List[ReviewComment]
    errors: List[str]
    raw_response: str
    success: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "comments": [c.to_dict() for c in self.comments],
            "errors": self.errors,
            "raw_response": self.raw_response,
            "success": self.success,
            "comment_count": len(self.comments),
            "error_count": len(self.errors)
        }


class ResponseParser:
    """
    Parser for LLM code analysis responses.
    
    Parses unstructured text responses from LLMs into structured
    ReviewComment objects. Handles various response formats and
    gracefully handles malformed responses.
    
    Validates Requirements: 1.4
    """
    
    # Patterns for extracting structured information
    SEVERITY_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:\*\*)?(?:severity|level|priority)(?:\*\*)?\s*[:：]\s*\[?([^\]\n]+)\]?',
        re.IGNORECASE | re.MULTILINE
    )
    
    LINE_NUMBER_PATTERN = re.compile(
        r'(?:line|lines?)\s+(\d+)(?:\s*[-–—]\s*(\d+))?',
        re.IGNORECASE
    )
    
    ISSUE_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:\*\*)?(?:issue|problem|concern)(?:\*\*)?\s*[:：]\s*([^\n]+(?:\n(?!\s*(?:\*\*)?(?:suggestion|recommendation|fix|impact|rationale|severity|location))[^\n]+)*)',
        re.IGNORECASE | re.MULTILINE
    )
    
    SUGGESTION_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:\*\*)?(?:suggestion|recommendation|fix|remediation)(?:\*\*)?\s*[:：]\s*([^\n]+(?:\n(?!\s*(?:\*\*)?(?:issue|problem|rationale|severity|location))[^\n]+)*)',
        re.IGNORECASE | re.MULTILINE
    )
    
    RATIONALE_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:\*\*)?(?:rationale|reason|why|explanation|impact)(?:\*\*)?\s*[:：]\s*([^\n]+(?:\n(?!\s*(?:\*\*)?(?:issue|suggestion|severity|location))[^\n]+)*)',
        re.IGNORECASE | re.MULTILINE
    )
    
    CATEGORY_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:\*\*)?(?:category|type|vulnerability\s+type)(?:\*\*)?\s*[:：]\s*([^\n]+)',
        re.IGNORECASE | re.MULTILINE
    )
    
    # Pattern to split response into individual findings
    FINDING_SEPARATOR = re.compile(
        r'\n\s*(?=(?:severity|1\.|2\.|3\.|4\.|5\.|6\.|7\.|8\.|9\.|10\.|\*\*severity|\*\*finding|\#\#\s+finding)\s*[:：])',
        re.IGNORECASE
    )
    
    def __init__(self, default_file_path: Optional[str] = None):
        """
        Initialize response parser.
        
        Args:
            default_file_path: Default file path to use if not found in response
        """
        self.default_file_path = default_file_path or "unknown"
    
    def parse(self, response: str, file_path: Optional[str] = None) -> ParseResult:
        """
        Parse LLM response into structured review comments.
        
        Args:
            response: Raw text response from LLM
            file_path: Optional file path to use as default
            
        Returns:
            ParseResult with comments and any errors encountered
            
        Example:
            >>> parser = ResponseParser()
            >>> result = parser.parse(llm_response, "src/auth.py")
            >>> for comment in result.comments:
            ...     logger.info(comment)
        """
        if not response or not response.strip():
            return ParseResult(
                comments=[],
                errors=["Empty response from LLM"],
                raw_response=response,
                success=False
            )
        
        default_path = file_path or self.default_file_path
        comments = []
        errors = []
        
        try:
            # Split response into individual findings
            findings = self._split_findings(response)
            
            if not findings:
                # Try parsing as a single finding
                findings = [response]
            
            logger.info(f"Found {len(findings)} potential findings in response")
            
            for i, finding in enumerate(findings, 1):
                try:
                    comment = self._parse_finding(finding, default_path)
                    if comment:
                        comments.append(comment)
                    else:
                        logger.debug(f"Finding {i} did not produce a valid comment")
                except Exception as e:
                    error_msg = f"Error parsing finding {i}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            success = len(comments) > 0
            
            if not success and not errors:
                errors.append("No valid review comments found in response")
            
            logger.info(
                f"Parsing complete: {len(comments)} comments, {len(errors)} errors"
            )
            
            return ParseResult(
                comments=comments,
                errors=errors,
                raw_response=response,
                success=success
            )
            
        except Exception as e:
            error_msg = f"Fatal error parsing response: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ParseResult(
                comments=comments,
                errors=errors + [error_msg],
                raw_response=response,
                success=False
            )
    
    def _split_findings(self, response: str) -> List[str]:
        """
        Split response into individual findings.
        
        Args:
            response: Raw response text
            
        Returns:
            List of finding text blocks
        """
        # Try to split by common separators
        findings = []
        
        # Try numbered list format (1., 2., 3., etc.)
        numbered_findings = re.split(r'\n\s*\d+\.\s+', response)
        if len(numbered_findings) > 1:
            # Skip first element if it's just intro text (no severity/issue keywords)
            findings = []
            for f in numbered_findings:
                f_stripped = f.strip()
                if f_stripped and (
                    'severity' in f_stripped.lower() or
                    'issue' in f_stripped.lower() or
                    'location' in f_stripped.lower() or
                    len(f_stripped) > 100  # Substantial content
                ):
                    findings.append(f_stripped)
        
        # Try markdown heading format (## Finding, ### Issue, etc.)
        if not findings:
            markdown_findings = re.split(r'\n\s*#{2,3}\s+', response)
            if len(markdown_findings) > 1:
                findings = []
                for f in markdown_findings:
                    f_stripped = f.strip()
                    if f_stripped and (
                        'severity' in f_stripped.lower() or
                        'issue' in f_stripped.lower() or
                        len(f_stripped) > 100
                    ):
                        findings.append(f_stripped)
        
        # Try markdown bold format (**Finding 1:**, **Finding 2:**, etc.)
        if not findings:
            bold_findings = re.split(r'\n\s*\*\*Finding\s+\d+[:\s]', response, flags=re.IGNORECASE)
            if len(bold_findings) > 1:
                findings = []
                for f in bold_findings:
                    f_stripped = f.strip()
                    if f_stripped and (
                        'severity' in f_stripped.lower() or
                        'issue' in f_stripped.lower() or
                        len(f_stripped) > 100
                    ):
                        findings.append(f_stripped)
        
        # Try severity-based splitting
        if not findings:
            severity_findings = re.split(
                r'\n\s*(?=(?:severity|level)\s*[:：])',
                response,
                flags=re.IGNORECASE
            )
            if len(severity_findings) > 1:
                findings = [f.strip() for f in severity_findings if f.strip()]
        
        # Filter out very short findings (likely noise) and intro text
        findings = [
            f for f in findings 
            if len(f) > 20 and (
                'severity' in f.lower() or
                'issue' in f.lower() or
                'problem' in f.lower()
            )
        ]
        
        return findings
    
    def _parse_finding(
        self,
        finding: str,
        default_file_path: str
    ) -> Optional[ReviewComment]:
        """
        Parse a single finding into a ReviewComment.
        
        Args:
            finding: Text of a single finding
            default_file_path: Default file path if not found
            
        Returns:
            ReviewComment or None if parsing fails
        """
        # Extract fields
        severity = self._extract_severity(finding)
        file_path, line_start, line_end = self._extract_location(
            finding,
            default_file_path
        )
        issue = self._extract_issue(finding)
        suggestion = self._extract_suggestion(finding)
        rationale = self._extract_rationale(finding)
        category = self._extract_category(finding)
        
        # Validate required fields
        if not issue:
            logger.debug("Finding missing issue description")
            return None
        
        # Use defaults for optional fields
        if not suggestion:
            suggestion = "No specific suggestion provided"
        
        if not rationale:
            rationale = "No rationale provided"
        
        return ReviewComment(
            severity=severity,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            issue=issue.strip(),
            suggestion=suggestion.strip(),
            rationale=rationale.strip(),
            category=category,
            raw_text=finding
        )
    
    def _extract_severity(self, text: str) -> Severity:
        """Extract severity from text"""
        match = self.SEVERITY_PATTERN.search(text)
        if match:
            severity_str = match.group(1).strip()
            return Severity.from_string(severity_str)
        
        # Try to infer from keywords
        text_lower = text.lower()
        if any(word in text_lower for word in ['critical', 'severe', 'dangerous']):
            return Severity.CRITICAL
        elif any(word in text_lower for word in ['high', 'important', 'major']):
            return Severity.HIGH
        elif any(word in text_lower for word in ['low', 'minor', 'trivial']):
            return Severity.LOW
        
        # Default to MEDIUM
        return Severity.MEDIUM
    
    def _extract_location(
        self,
        text: str,
        default_file_path: str
    ) -> tuple[str, Optional[int], Optional[int]]:
        """
        Extract file path and line numbers from text.
        
        Returns:
            Tuple of (file_path, line_start, line_end)
        """
        file_path = default_file_path
        line_start = None
        line_end = None
        
        # Try location pattern - look for "Location: <path> line <num>"
        # Use a more specific pattern that captures until "line" keyword or end of line
        location_match = re.search(
            r'(?:location|file|path)\s*[:：]\s*([^\n]+)',
            text,
            re.IGNORECASE
        )
        
        if location_match:
            location_text = location_match.group(1).strip()
            
            # Try to extract line numbers from the location text
            line_match = re.search(r'(?:line|lines?)\s+(\d+)(?:\s*[-–—]\s*(\d+))?', location_text, re.IGNORECASE)
            if line_match:
                line_start = int(line_match.group(1))
                if line_match.group(2):
                    line_end = int(line_match.group(2))
                # Remove the line part to get just the file path
                path_part = location_text[:line_match.start()].strip()
            else:
                path_part = location_text
            
            # Clean up the path
            path_part = path_part.rstrip(',:;')
            path_part = path_part.strip('`"\'')
            path_part = path_part.strip()
            
            # Check if it's a valid path (not N/A, none, unknown, etc.)
            if path_part and not path_part.lower() in ['n/a', 'none', 'unknown', 'n', 'a']:
                # Additional check: path should have at least one character that's not punctuation
                if any(c.isalnum() or c in ['/', '\\', '.', '_', '-'] for c in path_part):
                    file_path = path_part
        
        # Try standalone line number pattern if we didn't find it above
        if not line_start:
            line_match = self.LINE_NUMBER_PATTERN.search(text)
            if line_match:
                line_start = int(line_match.group(1))
                if line_match.group(2):
                    line_end = int(line_match.group(2))
        
        return file_path, line_start, line_end
    
    def _extract_issue(self, text: str) -> Optional[str]:
        """Extract issue description from text"""
        match = self.ISSUE_PATTERN.search(text)
        if match:
            issue = match.group(1).strip()
            # Clean up multi-line issues
            issue = ' '.join(line.strip() for line in issue.split('\n'))
            return issue
        
        # Fallback: try to extract first substantial sentence
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for line in lines:
            # Skip lines that look like headers
            if ':' in line and len(line.split(':')[0]) < 30:
                continue
            if len(line) > 20:
                return line
        
        return None
    
    def _extract_suggestion(self, text: str) -> Optional[str]:
        """Extract suggestion from text"""
        match = self.SUGGESTION_PATTERN.search(text)
        if match:
            suggestion = match.group(1).strip()
            # Clean up multi-line suggestions
            suggestion = ' '.join(line.strip() for line in suggestion.split('\n'))
            return suggestion
        
        return None
    
    def _extract_rationale(self, text: str) -> Optional[str]:
        """Extract rationale from text"""
        match = self.RATIONALE_PATTERN.search(text)
        if match:
            rationale = match.group(1).strip()
            # Clean up multi-line rationale
            rationale = ' '.join(line.strip() for line in rationale.split('\n'))
            return rationale
        
        return None
    
    def _extract_category(self, text: str) -> Optional[str]:
        """Extract category from text"""
        match = self.CATEGORY_PATTERN.search(text)
        if match:
            return match.group(1).strip()
        
        return None


def parse_llm_response(
    response: str,
    file_path: Optional[str] = None
) -> ParseResult:
    """
    Convenience function to parse LLM response.
    
    Args:
        response: Raw text response from LLM
        file_path: Optional file path for context
        
    Returns:
        ParseResult with structured comments
        
    Example:
        >>> result = parse_llm_response(llm_response, "src/auth.py")
        >>> if result.success:
        ...     for comment in result.comments:
        ...         logger.info("{comment.severity}: {comment.issue}")
    """
    parser = ResponseParser(default_file_path=file_path)
    return parser.parse(response, file_path)
