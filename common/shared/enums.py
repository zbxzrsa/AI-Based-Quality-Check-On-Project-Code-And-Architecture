"""
Consolidated Enums for the Project

This module contains all shared enum definitions to eliminate duplicates
and ensure consistency across the codebase.
"""

from enum import Enum


# ============================================================================
# RBAC & Authentication Enums
# ============================================================================

class Role(str, Enum):
    """User roles in the system - consolidated from multiple sources"""
    ADMIN = "ADMIN"                    # Full system control
    MANAGER = "MANAGER"                # Project oversight & ROI
    REVIEWER = "REVIEWER"              # Read/Write analysis
    PROGRAMMER = "PROGRAMMER"          # CRUD own branch
    DEVELOPER = "DEVELOPER"            # Developer role (alias for PROGRAMMER)
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"  # Compliance officer
    VISITOR = "VISITOR"                # Read-only grants


class Permission(str, Enum):
    """Permissions that can be granted to roles - consolidated"""
    # User Management
    CREATE_USER = "CREATE_USER"
    DELETE_USER = "DELETE_USER"
    UPDATE_USER = "UPDATE_USER"
    VIEW_USER = "VIEW_USER"
    MODIFY_USER = "MODIFY_USER"
    VIEW_USERS = "VIEW_USERS"
    
    # Project Management
    CREATE_PROJECT = "CREATE_PROJECT"
    DELETE_PROJECT = "DELETE_PROJECT"
    UPDATE_PROJECT = "UPDATE_PROJECT"
    VIEW_PROJECT = "VIEW_PROJECT"
    VIEW_PROJECTS = "VIEW_PROJECTS"
    MODIFY_PROJECT = "MODIFY_PROJECT"
    
    # Reviews
    VIEW_REVIEWS = "VIEW_REVIEWS"
    CREATE_REVIEW = "CREATE_REVIEW"
    MODIFY_REVIEW = "MODIFY_REVIEW"
    
    # Configuration
    MODIFY_CONFIG = "MODIFY_CONFIG"
    VIEW_CONFIG = "VIEW_CONFIG"
    
    # Reports
    EXPORT_REPORT = "EXPORT_REPORT"


# ============================================================================
# Severity & Priority Enums
# ============================================================================

class Severity(str, Enum):
    """Universal severity levels - consolidated from multiple sources"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TaskPriority(int, Enum):
    """Task priority levels"""
    CRITICAL = 0    # Security issues, critical errors
    HIGH = 1        # Important features, major bugs
    MEDIUM = 2      # Standard features, minor bugs
    LOW = 3         # Nice-to-have features, cosmetic issues


# ============================================================================
# Status Enums
# ============================================================================

class RepositoryStatus(str, Enum):
    """Repository processing status - consolidated"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    CANCELLED = "CANCELLED"


class HealthStatus(str, Enum):
    """Health status values"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PRStatus(str, Enum):
    """Pull request status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Circuit Breaker & System Enums
# ============================================================================

class CircuitBreakerState(str, Enum):
    """Circuit breaker states - consolidated"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back


class ServiceState(str, Enum):
    """Service state enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


# ============================================================================
# Analysis & Review Enums
# ============================================================================

class ReviewSeverity(str, Enum):
    """Severity levels for code review findings"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewCategory(str, Enum):
    """Categories for code review findings"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    RELIABILITY = "reliability"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


class AnalysisType(str, Enum):
    """Types of code analysis"""
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    COMPLIANCE = "compliance"


class ComplianceStatus(str, Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"           # Score >= 80
    PARTIALLY_COMPLIANT = "partially_compliant"  # Score 60-79
    NON_COMPLIANT = "non_compliant"   # Score < 60


# ============================================================================
# Repository & Git Enums
# ============================================================================

class RepositoryURLFormat(str, Enum):
    """Supported repository URL formats"""
    HTTPS = "https"
    SSH = "ssh"
    GIT = "git"


class GitHubConnectionType(str, Enum):
    """GitHub connection type"""
    HTTPS = "https"
    SSH = "ssh"
    TOKEN = "token"


# ============================================================================
# Node & Graph Enums
# ============================================================================

class NodeType(str, Enum):
    """Node type enumeration - consolidated"""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    MODULE = "module"
    FILE = "file"
    PACKAGE = "package"
    INTERFACE = "interface"
    ENUM = "enum"
    VARIABLE = "variable"


class RelationshipType(str, Enum):
    """Types of relationships in the code graph"""
    DEFINES = "DEFINES"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    IMPORTS = "IMPORTS"
    DEPENDS_ON = "DEPENDS_ON"
    CONTAINS = "CONTAINS"
    USES = "USES"


# ============================================================================
# Architectural Enums
# ============================================================================

class ComponentType(str, Enum):
    """Types of architectural components"""
    SERVICE = "service"
    MODULE = "module"
    LIBRARY = "library"
    DATABASE = "database"
    API = "api"
    UI_COMPONENT = "ui_component"


class DependencyType(str, Enum):
    """Types of dependencies between components"""
    FUNCTION_CALL = "function_call"
    DATA_FLOW = "data_flow"
    INHERITANCE = "inheritance"
    COMPOSITION = "composition"
    AGGREGATION = "aggregation"
    IMPORT = "import"


class ViolationType(str, Enum):
    """Types of architectural violations"""
    CIRCULAR_DEPENDENCY = "circular_dependency"
    LAYER_VIOLATION = "layer_violation"
    DEPENDENCY_RULE_VIOLATION = "dependency_rule_violation"
    NAMING_CONVENTION = "naming_convention"
    COMPLEXITY_VIOLATION = "complexity_violation"


# ============================================================================
# LLM & AI Enums
# ============================================================================

class LLMProvider(str, Enum):
    """LLM provider enum"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"


class ModelType(str, Enum):
    """Model types for different use cases"""
    CODE_REVIEW = "code_review"
    GENERAL = "general"
    VISION = "vision"
    CHAT = "chat"


# ============================================================================
# Cache & Performance Enums
# ============================================================================

class CacheKeyPrefix(str, Enum):
    """Standard cache key prefixes"""
    SESSION = "session"
    USER = "user"
    PROJECT = "project"
    ANALYSIS = "analysis"
    REPOSITORY = "repository"


# ============================================================================
# Audit & Logging Enums
# ============================================================================

class AuditAction(str, Enum):
    """Audit action enum"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"


# ============================================================================
# Invitation & Project Enums
# ============================================================================

class InvitationStatus(str, Enum):
    """Invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ProjectRole(str, Enum):
    """Project role for invitation-based system"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# ============================================================================
# Quality & Compliance Enums
# ============================================================================

class QualityGrade(str, Enum):
    """Quality grade based on analysis results"""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks"""
    PCI_DSS = "pci_dss"
    SOX = "sox"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    ISO_27001 = "iso_27001"


class ScanTool(str, Enum):
    """Security scanning tools"""
    BANDIT = "bandit"
    SAFETY = "safety"
    SEMGREP = "semgrep"
    ESLINT = "eslint"
    SONARQUBE = "sonarqube"


class Confidence(str, Enum):
    """Confidence levels for findings"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"