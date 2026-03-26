'use client';

import Link from 'next/link';
import { useCallback, useMemo, useState } from 'react';
import MainLayout from '@/components/layout/main-layout';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Search, GitPullRequest, Clock, CheckCircle2, XCircle, AlertCircle, Activity, ExternalLink, RefreshCw, Play, Loader2 } from 'lucide-react';
import { useProjects, useProjectPullRequests } from '@/hooks/useProjects';
import type { Project, PullRequest } from '@/hooks/useProjects';
import { apiPost } from '@/lib/api-client';

function ProjectPRList({ project, onSync }: { project: Project; onSync: (message: string) => void }) {
  const { data: pullRequestsData, isLoading, refetch } = useProjectPullRequests(project.id, 'all');
  const [analyzingPRId, setAnalyzingPRId] = useState<string | null>(null);
  const [syncLoading, setSyncLoading] = useState(false);

  const pullRequests: PullRequest[] = useMemo(() => pullRequestsData || [], [pullRequestsData]);

  const handleSync = useCallback(async () => {
    setSyncLoading(true);
    try {
      const data = await apiPost<{ message?: string }>(`/api/github/projects/${project.id}/sync`);

      onSync(data.message || `${project.name} synced successfully`);
      setTimeout(() => {
        void refetch();
      }, 500);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Sync failed: network error');
    } finally {
      setSyncLoading(false);
    }
  }, [onSync, project.id, project.name, refetch]);

  const handleAnalyze = useCallback(async (prId: string) => {
    setAnalyzingPRId(prId);
    try {
      await apiPost(`/api/github/analyze/${prId}`);

      void refetch();
      let pollCount = 0;
      const pollInterval = setInterval(() => {
        pollCount += 1;
        void refetch();
        if (pollCount >= 30) {
          clearInterval(pollInterval);
        }
      }, 2000);
      setTimeout(() => clearInterval(pollInterval), 62000);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to start analysis: network error');
    } finally {
      setAnalyzingPRId(null);
    }
  }, [refetch]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
      case 'merged':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'rejected':
      case 'closed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'analyzing':
        return <Activity className="h-4 w-4 text-blue-500" />;
      case 'reviewed':
        return <CheckCircle2 className="h-4 w-4 text-blue-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'approved':
      case 'merged':
      case 'reviewed':
        return 'success' as const;
      case 'rejected':
      case 'closed':
        return 'destructive' as const;
      case 'analyzing':
        return 'default' as const;
      default:
        return 'outline' as const;
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: 'Pending',
      analyzing: 'Analyzing',
      reviewed: 'Reviewed',
      approved: 'Approved',
      rejected: 'Rejected',
      merged: 'Merged',
      closed: 'Closed',
    };
    return labels[status] || status;
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((item) => (
          <Skeleton key={item} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {project.github_repo_url && (
        <div className="flex items-center justify-between border-b pb-3">
          <span className="text-sm text-muted-foreground">
            {pullRequests.length > 0 ? `${pullRequests.length} pull requests` : 'No pull requests yet'}
          </span>
          <Button variant="outline" size="sm" onClick={handleSync} disabled={syncLoading}>
            {syncLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            {syncLoading ? 'Syncing...' : 'Sync from GitHub'}
          </Button>
        </div>
      )}

      {!project.github_repo_url && (
        <div className="py-6 text-center">
          <AlertCircle className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">This project is not connected to a GitHub repository.</p>
          <p className="mt-1 text-xs text-muted-foreground">Connect a repository in project settings to review pull requests.</p>
        </div>
      )}

      {pullRequests.length === 0 && project.github_repo_url ? (
        <div className="py-6 text-center">
          <GitPullRequest className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">No pull requests found.</p>
          <p className="mt-1 text-xs text-muted-foreground">Use "Sync from GitHub" above to fetch the latest pull requests.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {pullRequests.map((pr) => (
            <div key={pr.id} className="flex items-start justify-between rounded-lg border p-4 transition-colors hover:bg-accent/50">
              <div className="flex flex-1 items-start gap-3">
                {getStatusIcon(pr.status)}
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <h4 className="truncate text-sm font-semibold">
                      PR #{pr.github_pr_number}: {pr.title}
                    </h4>
                    <Badge variant={getStatusBadgeVariant(pr.status)}>{getStatusLabel(pr.status)}</Badge>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    {pr.files_changed > 0 && <span>{pr.files_changed} files</span>}
                    {pr.lines_added > 0 && <span className="text-green-600">+{pr.lines_added}</span>}
                    {pr.lines_deleted > 0 && <span className="text-red-600">-{pr.lines_deleted}</span>}
                    {pr.branch_name && <span>{pr.branch_name}</span>}
                    <span>
                      <Clock className="mr-1 inline h-3 w-3" />
                      {new Date(pr.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {pr.risk_score !== null && pr.risk_score !== undefined && (
                  <Badge variant={pr.risk_score > 70 ? 'destructive' : pr.risk_score > 40 ? 'warning' : 'success'}>
                    Risk: {pr.risk_score}
                  </Badge>
                )}
                <Button asChild variant="secondary" size="sm">
                  <Link href={`/reviews/${pr.id}`}>View details</Link>
                </Button>
                {(pr.status === 'pending' || pr.status === 'analyzing') && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(event) => {
                      event.stopPropagation();
                      void handleAnalyze(pr.id);
                    }}
                    disabled={analyzingPRId === pr.id || pr.status === 'analyzing'}
                  >
                    {analyzingPRId === pr.id || pr.status === 'analyzing' ? (
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    ) : (
                      <Play className="mr-1 h-3 w-3" />
                    )}
                    {analyzingPRId === pr.id || pr.status === 'analyzing' ? 'Analyzing' : 'Start review'}
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ReviewsPage() {
  const { data: projects = [], isLoading } = useProjects();
  const [searchTerm, setSearchTerm] = useState('');
  const [syncMessage, setSyncMessage] = useState('');

  const filteredProjects = useMemo(() => {
    const list = Array.isArray(projects) ? projects : [];
    return list.filter((project: Project) => {
      if (!searchTerm) {
        return true;
      }
      return project.name.toLowerCase().includes(searchTerm.toLowerCase());
    });
  }, [projects, searchTerm]);

  const sortedProjects = useMemo(() => {
    return [...filteredProjects].sort((a, b) => {
      if (a.github_repo_url && !b.github_repo_url) return -1;
      if (!a.github_repo_url && b.github_repo_url) return 1;
      return 0;
    });
  }, [filteredProjects]);

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Pull Requests"
          description="Review and manage pull request analysis across all projects from the same dashboard-style workspace used throughout the application."
        />

        {syncMessage && (
          <div className="rounded-2xl border border-green-200 bg-green-50/90 p-3 text-sm text-green-700 dark:border-green-500/20 dark:bg-green-500/10 dark:text-green-200">
            {syncMessage}
          </div>
        )}

        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search projects..."
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            className="pl-10"
          />
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((item) => (
              <Skeleton key={item} className="h-40 w-full" />
            ))}
          </div>
        ) : sortedProjects.length === 0 ? (
          <Card className="border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <GitPullRequest className="mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="mb-2 text-lg font-semibold">No projects found</h3>
              <p className="text-sm text-muted-foreground">
                Add a project from the Projects page to start reviewing pull requests.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {sortedProjects.map((project: Project) => (
              <Card key={project.id} className="border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2 text-lg">
                        <GitPullRequest className="h-5 w-5" />
                        {project.name}
                      </CardTitle>
                      <CardDescription>
                        {project.github_repo_url ? (
                          <a
                            href={project.github_repo_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 hover:underline"
                          >
                            {project.github_repo_url.replace('https://github.com/', '')}
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        ) : (
                          'Repository not connected'
                        )}
                      </CardDescription>
                    </div>
                    <Badge variant={project.language ? 'outline' : 'secondary'}>
                      {project.language || 'Unknown'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <ProjectPRList project={project} onSync={setSyncMessage} />
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
