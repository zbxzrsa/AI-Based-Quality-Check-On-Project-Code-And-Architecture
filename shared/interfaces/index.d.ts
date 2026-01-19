import { AuthToken, Credentials, Role, HTTPRequest, HTTPResponse, AuthContext, GitHubWebhookPayload, CodeChange, AnalysisResult, ReviewComment, ArchitecturalNode, ArchitecturalEdge, Dependency, Project, ProjectConfiguration, Dashboard, ErrorResponse, Issue, Recommendation, ComponentIdentifier } from '../types';
export interface AuthenticationService {
    authenticate(credentials: Credentials): Promise<AuthToken>;
    authorize(token: AuthToken, resource: string, action: string): Promise<boolean>;
    getUserRoles(userId: string): Promise<Role[]>;
    refreshToken(refreshToken: string): Promise<AuthToken>;
    revokeToken(token: AuthToken): Promise<void>;
}
export interface APIGateway {
    routeRequest(request: HTTPRequest): Promise<HTTPResponse>;
    authenticateRequest(request: HTTPRequest): Promise<AuthContext>;
    applyRateLimit(clientId: string): Promise<boolean>;
    validateRequest(request: HTTPRequest): Promise<boolean>;
}
export interface CodeReviewEngine {
    processWebhook(payload: GitHubWebhookPayload): Promise<void>;
    analyzeCodeChanges(changes: CodeChange[]): Promise<AnalysisResult>;
    generateReviewComments(analysis: AnalysisResult): Promise<ReviewComment[]>;
    postCommentsToGitHub(comments: ReviewComment[], prNumber: number): Promise<void>;
    validateStandardsCompliance(code: string): Promise<Issue[]>;
}
export interface ArchitectureAnalyzer {
    parseSourceCode(files: SourceFile[]): Promise<AST[]>;
    extractDependencies(ast: AST[]): Promise<Dependency[]>;
    updateArchitectureGraph(dependencies: Dependency[]): Promise<void>;
    detectArchitecturalDrift(): Promise<DriftAlert[]>;
    generateArchitectureDiagram(projectId: string): Promise<ArchitectureDiagram>;
    detectCircularDependencies(projectId: string): Promise<CircularDependency[]>;
}
export interface AgenticAIService {
    analyzeCodeWithContext(code: string, context: ProjectContext): Promise<AIAnalysis>;
    recognizePatterns(codeStructure: CodeStructure): Promise<PatternMatch[]>;
    generateRecommendations(analysis: AIAnalysis): Promise<Recommendation[]>;
    simulateArchitecturalChanges(proposedChanges: ArchitecturalChange[]): Promise<SimulationResult>;
    switchModel(modelType: 'gpt-4' | 'claude-3.5'): Promise<void>;
    explainIssue(issue: Issue): Promise<string>;
}
export interface ProjectManager {
    createProject(config: ProjectConfiguration): Promise<Project>;
    queueAnalysisTask(task: AnalysisTask): Promise<TaskId>;
    getTaskStatus(taskId: TaskId): Promise<TaskStatus>;
    generateDashboard(userId: string): Promise<Dashboard>;
    getProjectMetrics(projectId: string): Promise<ProjectMetrics>;
    updateProjectConfiguration(projectId: string, config: ProjectConfiguration): Promise<void>;
}
export interface ErrorHandler {
    handleIntegrationError(error: IntegrationError): Promise<ErrorResponse>;
    handleAnalysisError(error: AnalysisError): Promise<ErrorResponse>;
    handleSystemError(error: SystemError): Promise<ErrorResponse>;
    logError(error: Error, context: Record<string, unknown>): Promise<void>;
}
export interface SourceFile {
    path: string;
    content: string;
    language: string;
    size: number;
}
export interface AST {
    filePath: string;
    nodes: ASTNode[];
    imports: ImportDeclaration[];
    exports: ExportDeclaration[];
}
export interface ASTNode {
    type: string;
    name: string;
    startLine: number;
    endLine: number;
    children: ASTNode[];
    properties: Record<string, unknown>;
}
export interface ImportDeclaration {
    source: string;
    imports: string[];
    isDefault: boolean;
}
export interface ExportDeclaration {
    name: string;
    isDefault: boolean;
    type: string;
}
export interface DriftAlert {
    id: string;
    type: 'circular_dependency' | 'unexpected_coupling' | 'layer_violation';
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
    affectedComponents: ComponentIdentifier[];
    detectedAt: Date;
}
export interface ArchitectureDiagram {
    nodes: ArchitecturalNode[];
    edges: ArchitecturalEdge[];
    metadata: DiagramMetadata;
}
export interface DiagramMetadata {
    projectId: string;
    generatedAt: Date;
    layout: string;
    filters: string[];
}
export interface CircularDependency {
    id: string;
    components: ComponentIdentifier[];
    severity: 'low' | 'medium' | 'high';
    description: string;
}
export interface ProjectContext {
    architecturalGraph: GraphSnapshot;
    codebaseMetrics: CodebaseMetrics;
    historicalPatterns: HistoricalPattern[];
    teamPreferences: TeamPreferences;
}
export interface GraphSnapshot {
    nodes: ArchitecturalNode[];
    edges: ArchitecturalEdge[];
    timestamp: Date;
}
export interface CodebaseMetrics {
    totalLines: number;
    totalFiles: number;
    complexity: number;
    testCoverage: number;
    technicalDebt: number;
}
export interface HistoricalPattern {
    pattern: string;
    frequency: number;
    lastSeen: Date;
    context: string[];
}
export interface TeamPreferences {
    codingStandards: string[];
    architecturalPatterns: string[];
    qualityGates: QualityGate[];
}
export interface QualityGate {
    name: string;
    threshold: number;
    metric: string;
    blocking: boolean;
}
export interface AIAnalysis {
    issues: Issue[];
    patterns: PatternMatch[];
    recommendations: Recommendation[];
    confidence: number;
    reasoning: string;
}
export interface CodeStructure {
    classes: ClassStructure[];
    functions: FunctionStructure[];
    modules: ModuleStructure[];
    dependencies: Dependency[];
}
export interface ClassStructure {
    name: string;
    methods: string[];
    properties: string[];
    inheritance: string[];
    interfaces: string[];
}
export interface FunctionStructure {
    name: string;
    parameters: Parameter[];
    returnType: string;
    complexity: number;
    calls: string[];
}
export interface Parameter {
    name: string;
    type: string;
    optional: boolean;
}
export interface ModuleStructure {
    name: string;
    exports: string[];
    imports: string[];
    dependencies: string[];
}
export interface PatternMatch {
    pattern: string;
    confidence: number;
    location: ComponentIdentifier;
    description: string;
    category: 'design_pattern' | 'anti_pattern' | 'code_smell';
}
export interface ArchitecturalChange {
    type: 'add_dependency' | 'remove_dependency' | 'modify_component';
    source: ComponentIdentifier;
    target?: ComponentIdentifier;
    description: string;
}
export interface SimulationResult {
    feasible: boolean;
    impact: ImpactAnalysis;
    warnings: string[];
    recommendations: string[];
}
export interface ImpactAnalysis {
    affectedComponents: ComponentIdentifier[];
    complexityChange: number;
    couplingChange: number;
    riskScore: number;
}
export interface AnalysisTask {
    id: string;
    projectId: string;
    type: 'full_analysis' | 'incremental_analysis' | 'architecture_analysis';
    priority: 'low' | 'medium' | 'high';
    payload: Record<string, unknown>;
    createdAt: Date;
}
export type TaskId = string;
export interface TaskStatus {
    id: TaskId;
    status: 'queued' | 'processing' | 'completed' | 'failed';
    progress: number;
    estimatedCompletion?: Date;
    result?: AnalysisResult;
    error?: string;
}
export interface ProjectMetrics {
    qualityScore: number;
    architecturalHealth: number;
    technicalDebt: number;
    testCoverage: number;
    issueCount: number;
    trends: MetricTrend[];
}
export interface MetricTrend {
    date: Date;
    metric: string;
    value: number;
}
export interface IntegrationError extends Error {
    service: string;
    operation: string;
    retryable: boolean;
}
export interface AnalysisError extends Error {
    analysisType: string;
    inputData: unknown;
    stage: string;
}
export interface SystemError extends Error {
    component: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    recoverable: boolean;
}
//# sourceMappingURL=index.d.ts.map