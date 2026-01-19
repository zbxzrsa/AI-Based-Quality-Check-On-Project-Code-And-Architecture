// Core domain types shared across all services

export interface User {
  id: string;
  email: string;
  name: string;
  roles: Role[];
  preferences: UserPreferences;
  lastLogin: Date;
}

export interface Role {
  name: 'administrator' | 'programmer' | 'visitor';
  permissions: Permission[];
}

export interface Permission {
  resource: string;
  actions: string[];
}

export interface UserPreferences {
  theme: 'light' | 'dark';
  notifications: NotificationSettings;
  analysisSettings: AnalysisSettings;
}

export interface NotificationSettings {
  email: boolean;
  inApp: boolean;
  webhooks: boolean;
}

export interface AnalysisSettings {
  enabledRules: string[];
  qualityThresholds: QualityThreshold[];
  preferredAIModel: 'gpt-4' | 'claude-3.5';
}

export interface AuthToken {
  userId: string;
  roles: string[];
  permissions: string[];
  expiresAt: Date;
  refreshToken: string;
}

export interface Credentials {
  email: string;
  password: string;
}

export interface Project {
  id: string;
  name: string;
  repositoryUrl: string;
  configuration: ProjectConfiguration;
  createdAt: Date;
  lastAnalyzed: Date;
  status: 'active' | 'paused' | 'archived';
}

export interface ProjectConfiguration {
  analysisRules: AnalysisRule[];
  qualityThresholds: QualityThreshold[];
  architecturalConstraints: ArchitecturalConstraint[];
  integrationSettings: IntegrationSettings;
}

export interface AnalysisRule {
  id: string;
  name: string;
  enabled: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
  configuration: Record<string, unknown>;
}

export interface QualityThreshold {
  metric: string;
  threshold: number;
  operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
}

export interface ArchitecturalConstraint {
  type: 'circular_dependency' | 'coupling_limit' | 'layer_violation';
  configuration: Record<string, unknown>;
}

export interface IntegrationSettings {
  github: GitHubSettings;
  webhooks: WebhookSettings;
}

export interface GitHubSettings {
  accessToken: string;
  webhookSecret: string;
  repositories: string[];
}

export interface WebhookSettings {
  enabled: boolean;
  retryAttempts: number;
  retryDelay: number;
}

export interface AnalysisResult {
  id: string;
  projectId: string;
  pullRequestId: string;
  timestamp: Date;
  codeChanges: CodeChange[];
  qualityScore: number;
  issues: Issue[];
  recommendations: Recommendation[];
}

export interface CodeChange {
  filePath: string;
  changeType: 'added' | 'modified' | 'deleted';
  linesAdded: number;
  linesRemoved: number;
  content: string;
}

export interface Issue {
  type: 'quality' | 'security' | 'architecture' | 'standards';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  location: CodeLocation;
  suggestedFix?: string;
  ruleViolated: string;
}

export interface CodeLocation {
  filePath: string;
  startLine: number;
  endLine: number;
  startColumn?: number;
  endColumn?: number;
}

export interface Recommendation {
  id: string;
  type: 'refactoring' | 'architecture' | 'performance' | 'security';
  priority: 'low' | 'medium' | 'high';
  description: string;
  reasoning: string;
  estimatedEffort: 'small' | 'medium' | 'large';
  references: string[];
}

export interface ArchitecturalNode {
  id: string;
  type: 'class' | 'function' | 'module' | 'package';
  name: string;
  filePath: string;
  metrics: NodeMetrics;
  properties: Record<string, unknown>;
}

export interface NodeMetrics {
  complexity: number;
  linesOfCode: number;
  dependencies: number;
  dependents: number;
}

export interface ArchitecturalEdge {
  id: string;
  sourceId: string;
  targetId: string;
  relationship: RelationshipType;
  weight: number;
  properties: Record<string, unknown>;
}

export type RelationshipType = 'imports' | 'extends' | 'implements' | 'calls' | 'instantiates';

export interface Dependency {
  source: ComponentIdentifier;
  target: ComponentIdentifier;
  type: RelationshipType;
  strength: number;
}

export interface ComponentIdentifier {
  name: string;
  type: string;
  filePath: string;
  namespace?: string;
}

export interface GitHubWebhookPayload {
  action: string;
  number?: number;
  pull_request?: {
    id: number;
    number: number;
    title: string;
    body: string;
    head: {
      sha: string;
      ref: string;
    };
    base: {
      sha: string;
      ref: string;
    };
    user: {
      login: string;
      id: number;
    };
  };
  repository: {
    id: number;
    name: string;
    full_name: string;
    owner: {
      login: string;
      id: number;
    };
  };
}

export interface ReviewComment {
  id: string;
  body: string;
  path: string;
  line: number;
  side: 'LEFT' | 'RIGHT';
  startLine?: number;
  startSide?: 'LEFT' | 'RIGHT';
}

export interface Dashboard {
  activeProjects: ProjectSummary[];
  queueStatus: QueueMetrics;
  recentAnalyses: AnalysisResult[];
  architecturalHealth: HealthMetrics;
}

export interface ProjectSummary {
  id: string;
  name: string;
  status: string;
  lastAnalyzed: Date;
  issueCount: number;
  qualityScore: number;
}

export interface QueueMetrics {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  averageProcessingTime: number;
}

export interface HealthMetrics {
  overallScore: number;
  architecturalDebt: number;
  circularDependencies: number;
  couplingViolations: number;
  trends: HealthTrend[];
}

export interface HealthTrend {
  date: Date;
  score: number;
  metric: string;
}

export interface ErrorResponse {
  code: string;
  message: string;
  retryable: boolean;
  retryAfter?: number;
  context?: Record<string, unknown>;
}

export interface HTTPRequest {
  method: string;
  path: string;
  headers: Record<string, string>;
  body?: unknown;
  query?: Record<string, string>;
}

export interface HTTPResponse {
  statusCode: number;
  headers: Record<string, string>;
  body: unknown;
}

export interface AuthContext {
  userId: string;
  roles: string[];
  permissions: string[];
}