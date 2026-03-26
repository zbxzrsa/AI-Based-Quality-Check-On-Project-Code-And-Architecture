/**
 * Zod Schemas for API Response Validation
 * 
 * Defines validation schemas for all API responses to ensure type safety
 * and data integrity in the frontend application.
 * 
 * Requirements: 3.1, 3.2, 3.4, 3.5, 3.7
 */

import { z } from 'zod';

// ============================================================================
// Architecture Analysis Schemas
// ============================================================================

/**
 * Architecture Node Schema
 * Represents a node in the architecture graph (component, module, class, function)
 */
export const ArchitectureNodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  type: z.string(),
  health: z.string().optional().default('healthy'),
  complexity: z.number().int().nonnegative().optional().default(5),
  position: z.record(z.string(), z.number()).optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
  metrics: z.record(z.string(), z.number()).optional(),
});

export type ArchitectureNode = z.output<typeof ArchitectureNodeSchema>;

/**
 * Architecture Edge Schema
 * Represents a dependency relationship between nodes
 */
export const ArchitectureEdgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  type: z.string(),
  is_circular: z.boolean().optional().default(false),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export type ArchitectureEdge = z.output<typeof ArchitectureEdgeSchema>;

/**
 * Architecture Metrics Schema
 * Aggregated metrics for the architecture analysis
 */
export const ArchitectureMetricsSchema = z.object({
  total_nodes: z.number().int().nonnegative(),
  total_edges: z.number().int().nonnegative(),
  circular_dependencies: z.number().int().nonnegative(),
  max_depth: z.number().int().nonnegative().optional(),
  avg_complexity: z.number().nonnegative().optional(),
});

export type ArchitectureMetrics = z.output<typeof ArchitectureMetricsSchema>;

/**
 * Architecture Analysis Response Schema
 * Complete architecture analysis data including nodes, edges, and metrics
 */
export const ArchitectureAnalysisSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  branch_id: z.string(),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  nodes: z.array(ArchitectureNodeSchema),
  edges: z.array(ArchitectureEdgeSchema),
  metrics: ArchitectureMetricsSchema,
  circular_dependency_chains: z.array(z.array(z.string())).optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  api_version: z.string().optional().default('1.0.0'),
});

export type ArchitectureAnalysis = z.output<typeof ArchitectureAnalysisSchema>;

// ============================================================================
// Dependency Graph Schemas
// ============================================================================

/**
 * Dependency Graph Node Schema
 */
export const DependencyGraphNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.enum(['module', 'class', 'function', 'package']),
  file_path: z.string().optional(),
  lines_of_code: z.number().int().nonnegative().optional(),
  complexity: z.number().int().nonnegative().optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export type DependencyGraphNode = z.output<typeof DependencyGraphNodeSchema>;

/**
 * Dependency Graph Edge Schema
 */
export const DependencyGraphEdgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  type: z.enum(['import', 'call', 'inheritance']),
  weight: z.number().nonnegative().optional().default(1.0),
  is_circular: z.boolean().optional().default(false),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export type DependencyGraphEdge = z.output<typeof DependencyGraphEdgeSchema>;

/**
 * Dependency Graph Metrics Schema
 */
export const DependencyGraphMetricsSchema = z.object({
  total_nodes: z.number().int().nonnegative(),
  total_edges: z.number().int().nonnegative(),
  circular_dependencies: z.number().int().nonnegative(),
  max_depth: z.number().int().nonnegative().optional(),
  avg_dependencies_per_node: z.number().nonnegative().optional(),
});

export type DependencyGraphMetrics = z.output<typeof DependencyGraphMetricsSchema>;

/**
 * Dependency Graph Response Schema
 */
export const DependencyGraphSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  branch_id: z.string().optional(),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  nodes: z.array(DependencyGraphNodeSchema),
  edges: z.array(DependencyGraphEdgeSchema),
  metrics: DependencyGraphMetricsSchema,
  circular_dependency_chains: z.array(z.array(z.string())).optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  api_version: z.string().optional().default('1.0.0'),
});

export type DependencyGraph = z.output<typeof DependencyGraphSchema>;

// ============================================================================
// Performance Metrics Schemas
// ============================================================================

/**
 * Performance Metric Schema
 * Individual metric data point with timestamp
 */
export const PerformanceMetricSchema = z.object({
  timestamp: z.string().datetime(),
  metric_name: z.string(),
  value: z.number().nonnegative(),
  unit: z.string(),
  tags: z.record(z.string(), z.string()).optional(),
});

export type PerformanceMetric = z.output<typeof PerformanceMetricSchema>;

/**
 * Time Range Schema
 */
export const TimeRangeSchema = z.object({
  start: z.string().datetime(),
  end: z.string().datetime(),
});

export type TimeRange = z.output<typeof TimeRangeSchema>;

/**
 * Metrics Collection Schema
 */
export const MetricsCollectionSchema = z.object({
  response_time: z.array(PerformanceMetricSchema),
  throughput: z.array(PerformanceMetricSchema),
  error_rate: z.array(PerformanceMetricSchema),
  cpu_usage: z.array(PerformanceMetricSchema),
  memory_usage: z.array(PerformanceMetricSchema),
});

export type MetricsCollection = z.output<typeof MetricsCollectionSchema>;

/**
 * Metrics Aggregations Schema
 */
export const MetricsAggregationsSchema = z.object({
  avg_response_time: z.number().nonnegative().max(10000),
  p95_response_time: z.number().nonnegative().max(10000),
  p99_response_time: z.number().nonnegative().max(10000),
  total_requests: z.number().int().nonnegative(),
  total_errors: z.number().int().nonnegative(),
});

export type MetricsAggregations = z.output<typeof MetricsAggregationsSchema>;

/**
 * Performance Dashboard Data Schema
 */
export const PerformanceDashboardDataSchema = z.object({
  api_version: z.string().optional().default('1.0.0'),
  project_id: z.string().uuid(),
  time_range: TimeRangeSchema,
  metrics: MetricsCollectionSchema,
  aggregations: MetricsAggregationsSchema,
});

export type PerformanceDashboardData = z.output<typeof PerformanceDashboardDataSchema>;

// ============================================================================
// Code Review Schemas
// ============================================================================

/**
 * Code Review Comment Schema
 */
export const CodeReviewCommentSchema = z.object({
  id: z.string().uuid(),
  file_path: z.string(),
  line_number: z.number().int().positive(),
  severity: z.enum(['info', 'warning', 'error', 'critical']),
  category: z.string(),
  message: z.string(),
  suggestion: z.string().optional(),
  code_snippet: z.string().optional(),
});

export type CodeReviewComment = z.output<typeof CodeReviewCommentSchema>;

/**
 * Code Review Summary Schema
 */
export const CodeReviewSummarySchema = z.object({
  total_files: z.number().int().nonnegative(),
  total_comments: z.number().int().nonnegative(),
  severity_counts: z.record(z.string(), z.number().int().nonnegative()),
  categories: z.array(z.string()),
});

export type CodeReviewSummary = z.output<typeof CodeReviewSummarySchema>;

/**
 * Code Review Response Schema
 */
export const CodeReviewSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  pr_number: z.number().int().nonnegative(),
  status: z.enum(['pending', 'in_progress', 'completed', 'failed']),
  comments: z.array(CodeReviewCommentSchema),
  summary: CodeReviewSummarySchema,
  created_at: z.string().datetime(),
  completed_at: z.string().datetime().optional(),
  api_version: z.string().optional().default('1.0.0'),
});

export type CodeReview = z.output<typeof CodeReviewSchema>;

// ============================================================================
// Validation Helper Functions
// ============================================================================

/**
 * Custom validation error class
 */
export class ValidationError extends Error {
  public readonly zodError: z.ZodError;
  
  constructor(
    message: string,
    zodError: z.ZodError
  ) {
    super(message);
    this.name = 'ValidationError';
    this.zodError = zodError;
  }
}

/**
 * Validate data against a schema (throws on error)
 */
export function validate<T>(schema: z.ZodType<T>, data: unknown): T {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('[Validation Error]', {
        issues: error.issues,
        data,
      });
      throw new ValidationError('Data validation failed', error);
    }
    throw error;
  }
}

/**
 * Safely validate data against a schema (returns result object)
 */
export function safeValidate<T>(
  schema: z.ZodType<T>,
  data: unknown
): { success: true; data: T } | { success: false; error: z.ZodError } {
  const result = schema.safeParse(data);
  
  if (!result.success) {
    console.error('[Validation Error]', {
      issues: result.error.issues,
      data,
    });
  }
  
  return result;
}

/**
 * Validate architecture analysis response
 */
export function validateArchitectureAnalysis(data: unknown): ArchitectureAnalysis {
  return ArchitectureAnalysisSchema.parse(data) as ArchitectureAnalysis;
}

/**
 * Validate dependency graph response
 */
export function validateDependencyGraph(data: unknown): DependencyGraph {
  return DependencyGraphSchema.parse(data) as DependencyGraph;
}

/**
 * Validate performance dashboard data
 */
export function validatePerformanceDashboardData(data: unknown): PerformanceDashboardData {
  return PerformanceDashboardDataSchema.parse(data) as PerformanceDashboardData;
}

/**
 * Validate code review response
 */
export function validateCodeReview(data: unknown): CodeReview {
  return CodeReviewSchema.parse(data) as CodeReview;
}

