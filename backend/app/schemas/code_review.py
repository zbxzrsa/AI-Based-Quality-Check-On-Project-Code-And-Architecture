"""
Code Review Schemas

Defines the data models for code review results and related entities.
"""
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ReviewSeverity(str, Enum):
    """Severity levels for code review findings"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    ERROR = "error"


class ReviewCategory(str, Enum):
    """Categories for code review findings"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class ReviewComment(BaseModel):
    """A single code review comment"""
    file_path: str = Field(..., description="Path to the file containing the issue")
    line: int = Field(..., description="Line number where the issue was found (0 for file-level issues)")
    message: str = Field(..., description="Description of the issue")
    severity: ReviewSeverity = Field(..., description="Severity of the issue")
    category: ReviewCategory = Field(ReviewCategory.OTHER, description="Category of the issue")
    snippet: Optional[str] = Field(None, description="Code snippet where the issue was found")
    rule_id: Optional[str] = Field(None, description="ID of the rule that was violated")
    rule_name: Optional[str] = Field(None, description="Name of the rule that was violated")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix for the issue")
    confidence: float = Field(1.0, description="Confidence score (0.0 to 1.0)")
    external_references: List[Dict[str, str]] = Field(
        default_factory=list,
        description="External references (e.g., CVE, OWASP, etc.)"
    )


class CodeReviewResult(BaseModel):
    """Result of a code review for a single file or PR"""
    pr_id: Optional[str] = Field(None, description="ID of the pull request")
    project_id: str = Field(..., description="ID of the project being reviewed")
    file_path: Optional[str] = Field(None, description="Path to the file being reviewed (if applicable)")
    commit_sha: Optional[str] = Field(None, description="Commit SHA being reviewed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the review was performed")
    
    # Review results
    comments: List[ReviewComment] = Field(
        default_factory=list,
        description="List of review comments"
    )
    
    # Metrics
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key metrics about the review"
    )
    
    # Metadata
    analyzer_version: str = Field("1.0.0", description="Version of the analyzer used")
    analysis_duration: Optional[float] = Field(None, description="Time taken for analysis in seconds")
    
    def add_comment(self, comment: ReviewComment) -> None:
        """Add a comment to the review"""
        self.comments.append(comment)
    
    def get_issues_by_severity(self, severity: ReviewSeverity) -> List[ReviewComment]:
        """Get all issues with the specified severity"""
        return [c for c in self.comments if c.severity == severity]
    
    def get_issues_by_category(self, category: ReviewCategory) -> List[ReviewComment]:
        """Get all issues in the specified category"""
        return [c for c in self.comments if c.category == category]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the review result to a dictionary"""
        return self.dict(exclude_none=True)


class CodeReviewSummary(BaseModel):
    """Summary of code review results"""
    pr_id: str = Field(..., description="ID of the pull request")
    project_id: str = Field(..., description="ID of the project")
    commit_sha: str = Field(..., description="Commit SHA that was reviewed")
    timestamp: datetime = Field(..., description="When the review was performed")
    
    # Summary metrics
    total_issues: int = Field(0, description="Total number of issues found")
    issues_by_severity: Dict[ReviewSeverity, int] = Field(
        default_factory=lambda: {s: 0 for s in ReviewSeverity},
        description="Number of issues by severity"
    )
    issues_by_category: Dict[ReviewCategory, int] = Field(
        default_factory=lambda: {c: 0 for c in ReviewCategory},
        description="Number of issues by category"
    )
    
    # Analysis metadata
    files_analyzed: int = Field(0, description="Number of files analyzed")
    analysis_duration: float = Field(0.0, description="Time taken for analysis in seconds")
    
    @classmethod
    def from_review_result(cls, result: CodeReviewResult) -> 'CodeReviewSummary':
        """Create a summary from a CodeReviewResult"""
        summary = cls(
            pr_id=result.pr_id or "",
            project_id=result.project_id,
            commit_sha=result.commit_sha or "",
            timestamp=result.timestamp,
            analysis_duration=result.analysis_duration or 0.0,
            files_analyzed=1 if result.file_path else 0
        )
        
        # Count issues by severity and category
        for comment in result.comments:
            summary.total_issues += 1
            summary.issues_by_severity[comment.severity] += 1
            summary.issues_by_category[comment.category] += 1
        
        return summary
    
    def merge(self, other: 'CodeReviewSummary') -> 'CodeReviewSummary':
        """Merge another summary into this one"""
        if self.pr_id != other.pr_id or self.project_id != other.project_id:
            raise ValueError("Cannot merge summaries from different PRs or projects")
        
        merged = self.copy(deep=True)
        merged.total_issues += other.total_issues
        merged.files_analyzed += other.files_analyzed
        
        # Update severity counts
        for severity in ReviewSeverity:
            merged.issues_by_severity[severity] += other.issues_by_severity.get(severity, 0)
        
        # Update category counts
        for category in ReviewCategory:
            merged.issues_by_category[category] += other.issues_by_category.get(category, 0)
        
        # Update timestamp to the most recent
        if other.timestamp > merged.timestamp:
            merged.timestamp = other.timestamp
        
        # Update analysis duration
        merged.analysis_duration += other.analysis_duration
        
        return merged
