/**
 * Project API hooks using React Query
 * Uses optimized API client with caching and retry logic
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, apiPost } from '@/lib/api-client';

const LIVE_REVIEW_POLL_INTERVAL = 5000;

export interface Project {
  id: string;
  name: string;
  description: string | null;
  github_repo_url: string | null;
  github_connection_type: 'https' | 'ssh' | 'cli';
  github_ssh_key_id: string | null;
  language: string | null;
  is_active: boolean;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface PullRequest {
  id: string;
  project_id: string;
  github_pr_number: number;
  title: string;
  description: string | null;
  branch_name: string;
  commit_sha: string;
  status: string;
  risk_score: number | null;
  files_changed: number;
  lines_added: number;
  lines_deleted: number;
  created_at: string;
  analyzed_at: string | null;
  updated_at?: string | null;
}

export interface ProjectMetrics {
  code_quality: number;
  security_rating: number;
  architecture_health: number;
  test_coverage: number;
  overall_health: number;
}

export interface DependencyStats {
  total: number;
  circular: number;
  outdated: number;
  dependency_issues: number;
}

export interface PerformanceMetrics {
  avg_build_time: string;
  avg_test_time: string;
  avg_analysis_time: string;
  pr_review_time_avg: string;
}

export interface IssueStats {
  critical: number;
  high: number;
  medium: number;
  low: number;
  security: number;
  performance: number;
  code_style: number;
  best_practices: number;
  total: number;
}

export interface TrendAnalysis {
  code_quality_change: number;
  test_coverage_change: number;
  issues_change: number;
}

export interface RecentReview {
  pr_id: string;
  pr_number: number;
  title: string;
  status: string;
  risk_score: number | null;
  files_changed: number;
  lines_added: number;
  lines_deleted: number;
  analyzed_at: string | null;
}

export interface ProjectAnalytics {
  project_id: string;
  metrics: ProjectMetrics;
  dependency_stats: DependencyStats;
  performance_metrics: PerformanceMetrics;
  issue_stats: IssueStats;
  trends: TrendAnalysis;
  recent_reviews: RecentReview[];
  total_prs: number;
  reviewed_prs: number;
  analysis_timestamp: string;
}

export interface ProjectIssue {
  id: string;
  file_path: string;
  line_number: number | null;
  message: string;
  severity: string;
  category: string | null;
  rule_id: string | null;
  rule_name: string | null;
  suggested_fix: string | null;
  created_at: string;
}

export interface ProjectIssuesResponse {
  issues: ProjectIssue[];
  total: number;
}

/**
 * Fetch all projects
 */
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      return apiClient.get<Project[]>('/rbac/projects');
    },
  });
}

/**
 * Fetch single project
 */
export function useProject(projectId: string) {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: async () => {
      return apiClient.get<Project>(`/rbac/projects/${projectId}`);
    },
    enabled: !!projectId,
  });
}

/**
 * Fetch project pull requests
 */
export function useProjectPullRequests(projectId: string, state: string = 'all') {
  return useQuery({
    queryKey: ['projects', projectId, 'pulls', state],
    queryFn: async () => {
      const response = await apiClient.get<
        | { pull_requests?: Array<Record<string, unknown>> }
        | Array<Record<string, unknown>>
      >(`/github/projects/${projectId}/pulls`, {
        params: { state },
        skipCache: true,
      });

      const pullRequests = Array.isArray(response)
        ? response
        : Array.isArray(response?.pull_requests)
          ? response.pull_requests
          : [];

      return pullRequests.map((pr) => ({
        id: String(pr.id ?? ''),
        project_id: projectId,
        github_pr_number: Number(pr.github_pr_number ?? pr.number ?? 0),
        title: String(pr.title ?? 'Untitled pull request'),
        description: typeof pr.description === 'string' ? pr.description : null,
        branch_name: typeof pr.branch_name === 'string' ? pr.branch_name : '',
        commit_sha: typeof pr.commit_sha === 'string' ? pr.commit_sha : '',
        status: String(pr.status ?? 'pending'),
        risk_score: typeof pr.risk_score === 'number' ? pr.risk_score : null,
        files_changed: Number(pr.files_changed ?? 0),
        lines_added: Number(pr.lines_added ?? 0),
        lines_deleted: Number(pr.lines_deleted ?? 0),
        created_at: typeof pr.created_at === 'string' ? pr.created_at : new Date().toISOString(),
        analyzed_at: typeof pr.analyzed_at === 'string' ? pr.analyzed_at : null,
        updated_at: typeof pr.updated_at === 'string' ? pr.updated_at : null,
      })) as PullRequest[];
    },
    enabled: !!projectId,
    staleTime: 0,
    refetchInterval: projectId ? LIVE_REVIEW_POLL_INTERVAL : false,
    refetchOnWindowFocus: true,
  });
}

/**
 * Fetch project analytics (AI reviewData)
 */
export function useProjectAnalytics(projectId: string) {
  return useQuery({
    queryKey: ['projects', projectId, 'analytics'],
    queryFn: async () => {
      return apiClient.get<ProjectAnalytics>(`/projects/${projectId}/analytics`);
    },
    enabled: !!projectId,
    staleTime: 0,
    refetchInterval: projectId ? LIVE_REVIEW_POLL_INTERVAL : false,
    refetchOnWindowFocus: true,
  });
}

/**
 * Sync project with GitHub
 */
export function useSyncProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await apiClient.post<{ message?: string }>(`/github/projects/${projectId}/sync`);
      const message = response?.message || '';

      if (message.toLowerCase().startsWith('sync failed')) {
        throw new Error(message);
      }

      return response;
    },
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'pulls'] });
      queryClient.invalidateQueries({ queryKey: ['architecture', projectId, 'branches'] });
      queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'issues'] });
    },
  });
}

/**
 * Create new project with GitHub connection options
 * Uses the /api/projects/create route to ensure github_repo_url is properly forwarded
 */
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      name: string;
      description?: string;
      github_repo_url?: string;
      github_connection_type?: 'https' | 'ssh' | 'cli';
      github_ssh_key_id?: string;
      github_cli_token?: string;
      language?: string;
    }) => {
      return apiPost<Project>('/api/projects/create', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

/**
 * Update project
 */
export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ projectId, updates }: { projectId: string; updates: Partial<Project> }) => {
      return apiClient.put<Project>(`/rbac/projects/${projectId}`, updates);
    },
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
    },
  });
}

/**
 * Delete project
 */
export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      await apiClient.delete(`/rbac/projects/${projectId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export interface SSHKey {
  id: string;
  name: string;
  public_key: string;
  key_fingerprint: string;
  github_username: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
}

export function useSSHKeys() {
  return useQuery({
    queryKey: ['ssh-keys'],
    queryFn: async () => {
      return apiClient.get<SSHKey[]>('/rbac/ssh-keys');
    },
  });
}

export function useCreateSSHKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      name: string;
      public_key: string;
      private_key: string;
      github_username?: string;
    }) => {
      return apiClient.post<SSHKey>('/rbac/ssh-keys', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ssh-keys'] });
    },
  });
}

export function useDeleteSSHKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (keyId: string) => {
      await apiClient.delete(`/rbac/ssh-keys/${keyId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ssh-keys'] });
    },
  });
}

/**
 * Fetch project branches for architecture visualization
 */
export function useProjectBranches(projectId: string) {
  return useQuery({
    queryKey: ['architecture', projectId, 'branches'],
    queryFn: async () => {
      return apiClient.get<BranchInfo[]>(`/architecture/${projectId}/branches`);
    },
    enabled: !!projectId,
    staleTime: 0,
    refetchInterval: projectId ? LIVE_REVIEW_POLL_INTERVAL : false,
    refetchOnWindowFocus: true,
  });
}

/**
 * Fetch branch architecture data
 */
export function useBranchArchitecture(projectId: string, branchId: string) {
  return useQuery({
    queryKey: ['architecture', projectId, 'branches', branchId],
    queryFn: async () => {
      return apiClient.get<BranchArchitecture>(
        `/architecture/${projectId}/branches/${branchId}/architecture`
      );
    },
    enabled: !!(projectId && branchId),
    staleTime: 0,
    refetchInterval: projectId && branchId ? LIVE_REVIEW_POLL_INTERVAL : false,
    refetchOnWindowFocus: true,
  });
}

/**
 * Fetch project architecture analysis (AI-generated)
 */
export function useProjectArchitectureAnalysis(projectId: string) {
  return useQuery({
    queryKey: ['projects', projectId, 'architecture-analysis'],
    queryFn: async () => {
      return apiClient.get<{
        strengths: string[];
        recommendations: string[];
        analysis_timestamp: string;
      }>(`/projects/${projectId}/architecture-analysis`);
    },
    enabled: !!projectId,
    staleTime: 0,
    refetchInterval: projectId ? LIVE_REVIEW_POLL_INTERVAL : false,
    refetchOnWindowFocus: true,
  });
}

export function useProjectIssues(projectId: string) {
  return useQuery({
    queryKey: ['projects', projectId, 'issues'],
    queryFn: async () => {
      return apiClient.get<ProjectIssuesResponse>(`/projects/${projectId}/issues`, {
        skipCache: true,
      });
    },
    enabled: !!projectId,
    staleTime: 0,
    refetchInterval: projectId ? LIVE_REVIEW_POLL_INTERVAL : false,
    refetchOnWindowFocus: true,
  });
}

export interface BranchInfo {
  id: string;
  name: string;
  last_commit: string;
  last_commit_date: string;
  author: string;
  components_count: number;
  complexity: number;
  health_status: 'healthy' | 'warning' | 'critical';
  circular_dependencies: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  health: 'healthy' | 'warning' | 'critical';
  complexity: number;
  position: { x: number; y: number };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  is_circular?: boolean;
}

export interface BranchArchitecture {
  branch_info: BranchInfo;
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics: {
    total_components: number;
    total_dependencies: number;
    circular_dependencies: number;
    avg_complexity: number;
    violations_count: number;
    critical_violations: number;
    high_violations: number;
  };
}

export interface ArchOverviewNode {
  id: string;
  label: string;
  type: string;
  group: string;
  health: string;
  description: string;
  position: { x: number; y: number };
  style?: { background: string; borderColor: string };
}

export interface ArchOverviewEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
}

export interface ArchOverviewGroup {
  id: string;
  label: string;
  color: string;
  borderColor: string;
}

export interface ArchitectureOverview {
  project_id: string;
  project_name: string;
  nodes: ArchOverviewNode[];
  edges: ArchOverviewEdge[];
  groups: ArchOverviewGroup[];
  health_summary: {
    overall: string;
    total_components: number;
    healthy_components: number;
    warning_components: number;
    critical_components: number;
    total_violations: number;
    has_analysis: boolean;
  };
}

/**
 * Fetch system-level architecture overview for a project
 */
export function useArchitectureOverview(projectId: string) {
  return useQuery({
    queryKey: ['architecture', projectId, 'overview'],
    queryFn: async () => {
      return apiClient.get<ArchitectureOverview>(
        `/architecture/overview/${projectId}`
      );
    },
    enabled: !!projectId,
    staleTime: 0,
    refetchInterval: projectId ? LIVE_REVIEW_POLL_INTERVAL : false,
    refetchOnWindowFocus: true,
  });
}

