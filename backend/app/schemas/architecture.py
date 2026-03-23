"""
Architecture Analysis Schemas

Defines data models for architectural analysis and visualization.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


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
    description: Optional[str] = Field(None, description="Description of the component")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional properties of the component"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing the component"
    )
    owner: Optional[str] = Field(None, description="Owner/team responsible for the component")
    is_abstract: bool = Field(False, description="Whether the component is abstract")
    file_path: Optional[str] = Field(None, description="Path to the component's source file")
    line_number: Optional[int] = Field(None, description="Line number where the component is defined")


class ArchitectureDependency(BaseModel):
    """Represents a dependency between two components"""
    source: str = Field(..., description="Name of the source component")
    target: str = Field(..., description="Name of the target component")
    type: DependencyType = Field(..., description="Type of the dependency")
    description: Optional[str] = Field(None, description="Description of the dependency")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional properties of the dependency"
    )
    is_direct: bool = Field(True, description="Whether this is a direct dependency")
    weight: float = Field(1.0, description="Weight/strength of the dependency")


class ArchitectureViolation(BaseModel):
    """Represents an architectural violation"""
    type: ViolationType = Field(..., description="Type of the violation")
    component: str = Field(..., description="Name of the component with the violation")
    related_component: Optional[str] = Field(
        None,
        description="Name of the related component (for dependency violations)"
    )
    message: str = Field(..., description="Description of the violation")
    severity: str = Field("medium", description="Severity of the violation (low, medium, high, critical)")
    file_path: Optional[str] = Field(None, description="Path to the file with the violation")
    line_number: Optional[int] = Field(None, description="Line number of the violation")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix for the violation")
    rule_id: Optional[str] = Field(None, description="ID of the violated rule")
    rule_name: Optional[str] = Field(None, description="Name of the violated rule")
    external_references: List[Dict[str, str]] = Field(
        default_factory=list,
        description="External references (e.g., documentation, principles)"
    )


class ArchitectureMetric(BaseModel):
    """Represents an architectural metric"""
    name: str = Field(..., description="Name of the metric")
    value: float = Field(..., description="Value of the metric")
    description: str = Field(..., description="Description of the metric")
    component: Optional[str] = Field(None, description="Component the metric applies to")
    threshold: Optional[float] = Field(None, description="Threshold value for the metric")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    trend: Optional[float] = Field(None, description="Trend of the metric (positive/negative/neutral)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the metric was calculated"
    )


class ArchitectureReport(BaseModel):
    """Report of architectural analysis"""
    project_id: str = Field(..., description="ID of the analyzed project")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the analysis was performed"
    )
    components: List[ArchitectureComponent] = Field(
        default_factory=list,
        description="List of components in the architecture"
    )
    dependencies: List[ArchitectureDependency] = Field(
        default_factory=list,
        description="List of dependencies between components"
    )
    violations: List[ArchitectureViolation] = Field(
        default_factory=list,
        description="List of architectural violations found"
    )
    metrics: List[ArchitectureMetric] = Field(
        default_factory=list,
        description="Architectural metrics"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="List of recommendations for improving the architecture"
    )
    error: Optional[str] = Field(None, description="Error message if analysis failed")
    analyzer_version: str = Field("1.0.0", description="Version of the analyzer used")
    analysis_duration: float = Field(
        0.0,
        description="Time taken to perform the analysis in seconds"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the report to a dictionary"""
        return self.dict(exclude_none=True)
    
    def get_violations_by_severity(self, severity: str) -> List[ArchitectureViolation]:
        """Get violations with the specified severity"""
        return [v for v in self.violations if v.severity == severity]
    
    def get_metrics_by_component(self, component: str) -> List[ArchitectureMetric]:
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
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing the rule"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the rule to a dictionary"""
        return self.dict(exclude_none=True)


class ArchitectureRuleSet(BaseModel):
    """Collection of architecture rules"""
    name: str = Field(..., description="Name of the rule set")
    description: str = Field(..., description="Description of the rule set")
    rules: List[ArchitectureRule] = Field(
        default_factory=list,
        description="List of rules in the rule set"
    )
    
    def add_rule(self, rule: ArchitectureRule) -> None:
        """Add a rule to the rule set"""
        self.rules.append(rule)
    
    def get_rule(self, rule_id: str) -> Optional[ArchitectureRule]:
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the rule set to a dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "rules": [rule.to_dict() for rule in self.rules]
        }
