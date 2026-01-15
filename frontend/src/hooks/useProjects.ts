/**
 * Project API hooks using React Query
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export interface Project {
  id: string;
  name: string;
  description: string | null;
  github_repo_url: string;
  owner_id: string;
  language: string | null;
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
}

/**
 * Fetch all projects
 */
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await api.get<Project[]>('/projects');
      return response.data;
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
      const response = await api.get<Project>(`/projects/${projectId}`);
      return response.data;
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
      const response = await api.get(`/github/projects/${projectId}/pulls`, {
        params: { state },
      });
      return response.data;
    },
    enabled: !!projectId,
  });
}

/**
 * Sync project with GitHub
 */
export function useSyncProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await api.post(`/github/projects/${projectId}/sync`);
      return response.data;
    },
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
    },
  });
}

/**
 * Create new project
 */
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Project>) => {
      const response = await api.post<Project>('/projects', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
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
      await api.delete(`/projects/${projectId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
