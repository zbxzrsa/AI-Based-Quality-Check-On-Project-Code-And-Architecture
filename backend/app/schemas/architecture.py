"""
Architecture Analysis Schemas

Defines data models for architectural analysis and visualization.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    """Types of architectural components"""

    SERVICE = "service"
    CONTROLLER = "controller"
    REPOSITORY = "repository"
    MODEL = "model"
    UTILITY = "utility"
    COMPONENT = "component"
    API = "api"
    UI = "ui"
    DOMAIN = "domain"
    INFRASTRUCTURE = "infrastructure"


class DependencyType(str, Enum):
    """Types of dependencies between components"""

    FUNCTION_CALL = "function_call"
    INHERITANCE = "inheritance"
    IMPLEMENTATION = "implementation"
    IMPORT = "import"
    REFERENCE = "reference"
    DATA_FLOW = "data_flow"
    EVENT = "event"
    MESSAGE = "message"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"


class ViolationType(str, Enum):
    """Types of architectural violations"""

    CIRCULAR_DEPENDENCY = "circular_dependency"
    DEPENDENCY_VIOLATION = "dependency_violation"
    MISSING_ABSTRACTION = "missing_abstraction"
    CYCLIC_DEPENDENCY = "cyclic_dependency"
    VIOLATES_LAYERING = "violates_layering"
    TOO_MANY_DEPENDENCIES = "too_many_dependencies"
    TOO_MANY_DEPENDENTS = "too_many_dependents"
    MISSING_COMPONENT = "missing_component"
    UNAUTHORIZED_COMPONENT = "unauthorized_component"
    INVALID_DEPENDENCY = "invalid_dependency"


class ArchitectureComponent(BaseModel):
    """Represents a component in the software architecture"""

    name: str = Field(..., description="Name of the component")
    type: ComponentType = Field(..., description="Type of the component")
    description: str | None = Field(None, description="Description of the component")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties of the component")
    tags: list[str] = Field(default_factory=list, description="Tags for categorizing the component")
    owner: str | None = Field(None, description="Owner/team responsible for the component")
    is_abstract: bool = Field(False, description="Whether the component is abstract")
    file_path: str | None = Field(None, description="Path to the component's source file")
    line_number: int | None = Field(None, description="Line number where the component is defined")


class ArchitectureDependency(BaseModel):
    """Represents a dependency between two components"""

    source: str = Field(..., description="Name of the source component")
    target: str = Field(..., description="Name of the target component")
    type: DependencyType = Field(..., description="Type of the dependency")
    description: str | None = Field(None, description="Description of the dependency")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties of the dependency")
    is_direct: bool = Field(True, description="Whether this is a direct dependency")
    weight: float = Field(1.0, description="Weight/strength of the dependency")


class ArchitectureViolation(BaseModel):
    """Represents an architectural violation"""

    type: ViolationType = Field(..., description="Type of the violation")
    component: str = Field(..., description="Name of the component with the violation")
    related_component: str | None = Field(None, description="Name of the related component (for dependency violations)")
    message: str = Field(..., description="Description of the violation")
    severity: str = Field("medium", description="Severity of the violation (low, medium, high, critical)")
    file_path: str | None = Field(None, description="Path to the file with the violation")
    line_number: int | None = Field(None, description="Line number of the violation")
    suggested_fix: str | None = Field(None, description="Suggested fix for the violation")
    rule_id: str | None = Field(None, description="ID of the violated rule")
    rule_name: str | None = Field(None, description="Name of the violated rule")
    external_references: list[dict[str, str]] = Field(
        default_factory=list, description="External references (e.g., documentation, principles)"
    )


class ArchitectureMetric(BaseModel):
    """Represents an architectural metric"""

    name: str = Field(..., description="Name of the metric")
    value: float = Field(..., description="Value of the metric")
    description: str = Field(..., description="Description of the metric")
    component: str | None = Field(None, description="Component the metric applies to")
    threshold: float | None = Field(None, description="Threshold value for the metric")
    unit: str | None = Field(None, description="Unit of measurement")
    trend: float | None = Field(None, description="Trend of the metric (positive/negative/neutral)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the metric was calculated")


class ArchitectureReport(BaseModel):
    """Report of architectural analysis"""

    project_id: str = Field(..., description="ID of the analyzed project")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the analysis was performed")
    components: list[ArchitectureComponent] = Field(
        default_factory=list, description="List of components in the architecture"
    )
    dependencies: list[ArchitectureDependency] = Field(
        default_factory=list, description="List of dependencies between components"
    )
    violations: list[ArchitectureViolation] = Field(
        default_factory=list, description="List of architectural violations found"
    )
    metrics: list[ArchitectureMetric] = Field(default_factory=list, description="Architectural metrics")
    recommendations: list[str] = Field(
        default_factory=list, description="List of recommendations for improving the architecture"
    )
    error: str | None = Field(None, description="Error message if analysis failed")
    analyzer_version: str = Field("1.0.0", description="Version of the analyzer used")
    analysis_duration: float = Field(0.0, description="Time taken to perform the analysis in seconds")

    def to_dict(self) -> dict[str, Any]:
        """Convert the report to a dictionary"""
        return self.dict(exclude_none=True)

    def get_violations_by_severity(self, severity: str) -> list[ArchitectureViolation]:
        """Get violations with the specified severity"""
        return [v for v in self.violations if v.severity == severity]

    def get_metrics_by_component(self, component: str) -> list[ArchitectureMetric]:
        """Get metrics for a specific component"""
        return [m for m in self.metrics if m.component == component]


class ArchitectureRule(BaseModel):
    """Rule for validating architecture"""

    id: str = Field(..., description="Unique identifier for the rule")
    name: str = Field(..., description="Name of the rule")
    description: str = Field(..., description="Description of the rule")
    pattern: str = Field(..., description="Pattern to match for the rule")
    type: str = Field(..., description="Type of the rule (dependency, naming, etc.)")
    severity: str = Field("medium", description="Severity of violations")
    enabled: bool = Field(True, description="Whether the rule is enabled")
    tags: list[str] = Field(default_factory=list, description="Tags for categorizing the rule")

    def to_dict(self) -> dict[str, Any]:
        """Convert the rule to a dictionary"""
        return self.dict(exclude_none=True)


class ArchitectureRuleSet(BaseModel):
    """Collection of architecture rules"""

    name: str = Field(..., description="Name of the rule set")
    description: str = Field(..., description="Description of the rule set")
    rules: list[ArchitectureRule] = Field(default_factory=list, description="List of rules in the rule set")

    def add_rule(self, rule: ArchitectureRule) -> None:
        """Add a rule to the rule set"""
        self.rules.append(rule)

    def get_rule(self, rule_id: str) -> ArchitectureRule | None:
        """Get a rule by ID"""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def enable_rule(self, rule_id: str, enabled: bool = True) -> bool:
        """Enable or disable a rule"""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = enabled
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert the rule set to a dictionary"""
        return {"name": self.name, "description": self.description, "rules": [rule.to_dict() for rule in self.rules]}
