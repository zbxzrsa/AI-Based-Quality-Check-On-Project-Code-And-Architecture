"""
AI PR Review specific data models for the PR review service.
"""

from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    """Compliance status enum."""
    COMPLIANT = "COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"


class SafetyScore(BaseModel):
    """Safety score model for code changes."""
    overall_score: int = Field(..., ge=0, le=100, description="Overall safety score (0-100)")
    maintainability_score: int = Field(..., ge=0, le=100, description="Maintainability score (0-100)")
    testability_score: int = Field(..., ge=0, le=100, description="Testability score (0-100)")
    risk_factors: List[str] = Field(default_factory=list, description="List of identified risk factors")
    performance_impact: str = Field(default="Unknown", description="Performance impact assessment")


class RefactoringSuggestion(BaseModel):
    """Refactoring suggestion model."""
    title: str = Field(..., description="Title of the suggestion")
    description: str = Field(..., description="Detailed description of the suggestion")
    priority: str = Field(..., description="Priority level (LOW, MEDIUM, HIGH)")
    estimated_effort: float = Field(..., gt=0, description="Estimated effort in hours")
    benefits: List[str] = Field(default_factory=list, description="List of expected benefits")


class ArchitecturalViolation(BaseModel):
    """Architectural violation model."""
    type: str = Field(..., description="Type of violation")
    description: str = Field(..., description="Detailed description of the violation")
    location: str = Field(..., description="Location where violation was detected")
    severity: str = Field(..., description="Severity level (LOW, MEDIUM, HIGH, CRITICAL)")


class PRReviewReport(BaseModel):
    """Complete PR review report model."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")
    compliance_status: ComplianceStatus = Field(..., description="Overall compliance status")
    safety_score: SafetyScore = Field(..., description="Safety and quality scores")
    architectural_violations: List[Dict] = Field(default_factory=list, description="List of architectural violations")
    refactoring_suggestions: List[Dict] = Field(default_factory=list, description="List of refactoring suggestions")
    markdown_report: str = Field(..., description="Markdown formatted report")


class DesignStandard(BaseModel):
    """Design standard model for architectural validation."""
    name: str = Field(..., description="Name of the design standard")
    description: str = Field(..., description="Description of the design standard")
    patterns: List[str] = Field(default_factory=list, description="List of approved patterns")
    anti_patterns: List[str] = Field(default_factory=list, description="List of anti-patterns to avoid")
    layers: Dict[str, List[str]] = Field(default_factory=dict, description="Layer definitions and responsibilities")


class PRReviewRequest(BaseModel):
    """Request model for PR review."""
    diff: str = Field(..., description="Git diff string to analyze")
    design_standard: str = Field(..., description="Design standard text for comparison")


class PRReviewResponse(BaseModel):
    """Response model for PR review."""
    report: PRReviewReport = Field(..., description="Complete review report")
    success: bool = Field(default=True, description="Whether the review was successful")
    message: Optional[str] = Field(None, description="Additional message or error details")
