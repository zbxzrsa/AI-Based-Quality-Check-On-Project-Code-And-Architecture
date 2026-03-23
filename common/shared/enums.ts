/**
 * Consolidated Enums for TypeScript/Frontend
 * 
 * This module contains all shared enum definitions to eliminate duplicates
 * and ensure consistency across the frontend codebase.
 */

// ============================================================================
// RBAC & Authentication Enums
// ============================================================================

export enum Role {
  ADMIN = 'ADMIN',                    // Full system control
  MANAGER = 'MANAGER',                // Project oversight & ROI
  REVIEWER = 'REVIEWER',              // Read/Write analysis
  PROGRAMMER = 'PROGRAMMER',          // CRUD own branch
  DEVELOPER = 'DEVELOPER',            // Developer role (alias for PROGRAMMER)
  COMPLIANCE_OFFICER = 'COMPLIANCE_OFFICER',  // Compliance officer
  VISITOR = 'VISITOR',                // Read-only grants
}

export enum Permission {
  // User Management
  CREATE_USER = 'CREATE_USER',
  DELETE_USER = 'DELETE_USER',
  UPDATE_USER = 'UPDATE_USER',
  VIEW_USER = 'VIEW_USER',
  MODIFY_USER = 'MODIFY_USER',
  VIEW_USERS = 'VIEW_USERS',
  
  // Project Management
  CREATE_PROJECT = 'CREATE_PROJECT',
  DELETE_PROJECT = 'DELETE_PROJECT',
  UPDATE_PROJECT = 'UPDATE_PROJECT',
  VIEW_PROJECT = 'VIEW_PROJECT',
  VIEW_PROJECTS = 'VIEW_PROJECTS',
  MODIFY_PROJECT = 'MODIFY_PROJECT',
  
  // Reviews
  VIEW_REVIEWS = 'VIEW_REVIEWS',
  CREATE_REVIEW = 'CREATE_REVIEW',
  MODIFY_REVIEW = 'MODIFY_REVIEW',
  
  // Configuration
  MODIFY_CONFIG = 'MODIFY_CONFIG',
  VIEW_CONFIG = 'VIEW_CONFIG',
  
  // Reports
  EXPORT_REPORT = 'EXPORT_REPORT',
}

// ============================================================================
// Severity & Priority Enums
// ============================================================================

export enum Severity {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  INFO = 'info',
}

export enum TaskPriority {
  CRITICAL = 0,    // Security issues, critical errors
  HIGH = 1,        // Important features, major bugs
  MEDIUM = 2,      // Standard features, minor bugs
  LOW = 3,         // Nice-to-have features, cosmetic issues
}

// ============================================================================
// Status Enums
// ============================================================================

export enum RepositoryStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  ARCHIVED = 'archived',
}

export enum TaskStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  SUCCESS = 'SUCCESS',
  FAILURE = 'FAILURE',
  RETRY = 'RETRY',
  CANCELLED = 'CANCELLED',
}

export enum HealthStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNHEALTHY = 'unhealthy',
  UNKNOWN = 'unknown',
}

export enum PRStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

// ============================================================================
// Error Handling Enums
// ============================================================================

export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  AUTH_ERROR = 'AUTH_ERROR',
  PERMISSION_ERROR = 'PERMISSION_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  RATE_LIMIT_ERROR = 'RATE_LIMIT_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}

// ============================================================================
// Circuit Breaker & System Enums
// ============================================================================

export enum CircuitBreakerState {
  CLOSED = 'closed',      // Normal operation
  OPEN = 'open',          // Circuit is open, requests fail fast
  HALF_OPEN = 'half_open',  // Testing if service is back
}

export enum ServiceState {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNHEALTHY = 'unhealthy',
  MAINTENANCE = 'maintenance',
}

// ============================================================================
// Analysis & Review Enums
// ============================================================================

export enum ReviewSeverity {
  INFO = 'info',
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum ReviewCategory {
  SECURITY = 'security',
  PERFORMANCE = 'performance',
  MAINTAINABILITY = 'maintainability',
  RELIABILITY = 'reliability',
  STYLE = 'style',
  DOCUMENTATION = 'documentation',
  TESTING = 'testing',
}

export enum AnalysisType {
  CODE_QUALITY = 'code_quality',
  SECURITY = 'security',
  PERFORMANCE = 'performance',
  ARCHITECTURE = 'architecture',
  COMPLIANCE = 'compliance',
}

export enum ComplianceStatus {
  COMPLIANT = 'compliant',           // Score >= 80
  PARTIALLY_COMPLIANT = 'partially_compliant',  // Score 60-79
  NON_COMPLIANT = 'non_compliant',   // Score < 60
}

// ============================================================================
// Repository & Git Enums
// ============================================================================

export enum RepositoryURLFormat {
  HTTPS = 'https',
  SSH = 'ssh',
  GIT = 'git',
}

export enum GitHubConnectionType {
  HTTPS = 'https',
  SSH = 'ssh',
  TOKEN = 'token',
}

// ============================================================================
// Node & Graph Enums
// ============================================================================

export enum NodeType {
  CLASS = 'class',
  FUNCTION = 'function',
  METHOD = 'method',
  MODULE = 'module',
  FILE = 'file',
  PACKAGE = 'package',
  INTERFACE = 'interface',
  ENUM = 'enum',
  VARIABLE = 'variable',
}

export enum RelationshipType {
  DEFINES = 'DEFINES',
  CALLS = 'CALLS',
  INHERITS = 'INHERITS',
  IMPLEMENTS = 'IMPLEMENTS',
  IMPORTS = 'IMPORTS',
  DEPENDS_ON = 'DEPENDS_ON',
  CONTAINS = 'CONTAINS',
  USES = 'USES',
}

// ============================================================================
// Architectural Enums
// ============================================================================

export enum ComponentType {
  SERVICE = 'service',
  MODULE = 'module',
  LIBRARY = 'library',
  DATABASE = 'database',
  API = 'api',
  UI_COMPONENT = 'ui_component',
}

export enum DependencyType {
  FUNCTION_CALL = 'function_call',
  DATA_FLOW = 'data_flow',
  INHERITANCE = 'inheritance',
  COMPOSITION = 'composition',
  AGGREGATION = 'aggregation',
  IMPORT = 'import',
}

export enum ViolationType {
  CIRCULAR_DEPENDENCY = 'circular_dependency',
  LAYER_VIOLATION = 'layer_violation',
  DEPENDENCY_RULE_VIOLATION = 'dependency_rule_violation',
  NAMING_CONVENTION = 'naming_convention',
  COMPLEXITY_VIOLATION = 'complexity_violation',
}

// ============================================================================
// LLM & AI Enums
// ============================================================================

export enum LLMProvider {
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  OLLAMA = 'ollama',
  HUGGINGFACE = 'huggingface',
}

export enum ModelType {
  CODE_REVIEW = 'code_review',
  GENERAL = 'general',
  VISION = 'vision',
  CHAT = 'chat',
}

// ============================================================================
// Cache & Performance Enums
// ============================================================================

export enum CacheKeyPrefix {
  SESSION = 'session',
  USER = 'user',
  PROJECT = 'project',
  ANALYSIS = 'analysis',
  REPOSITORY = 'repository',
}

// ============================================================================
// Audit & Logging Enums
// ============================================================================

export enum AuditAction {
  CREATE = 'create',
  READ = 'read',
  UPDATE = 'update',
  DELETE = 'delete',
  LOGIN = 'login',
  LOGOUT = 'logout',
  EXPORT = 'export',
  IMPORT = 'import',
}

// ============================================================================
// Invitation & Project Enums
// ============================================================================

export enum InvitationStatus {
  PENDING = 'pending',
  ACCEPTED = 'accepted',
  DECLINED = 'declined',
  EXPIRED = 'expired',
  CANCELLED = 'cancelled',
}

export enum ProjectRole {
  OWNER = 'owner',
  ADMIN = 'admin',
  MEMBER = 'member',
  VIEWER = 'viewer',
}

// ============================================================================
// Quality & Compliance Enums
// ============================================================================

export enum QualityGrade {
  A_PLUS = 'A+',
  A = 'A',
  B = 'B',
  C = 'C',
  D = 'D',
  F = 'F',
}

export enum ComplianceFramework {
  PCI_DSS = 'pci_dss',
  SOX = 'sox',
  HIPAA = 'hipaa',
  GDPR = 'gdpr',
  ISO_27001 = 'iso_27001',
}

export enum ScanTool {
  BANDIT = 'bandit',
  SAFETY = 'safety',
  SEMGREP = 'semgrep',
  ESLINT = 'eslint',
  SONARQUBE = 'sonarqube',
}

export enum Confidence {
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
}