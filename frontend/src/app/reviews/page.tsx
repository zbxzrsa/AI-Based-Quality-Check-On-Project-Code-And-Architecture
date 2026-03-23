'use client';

import { useState, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Search,
  GitPullRequest,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Activity,
  ExternalLink,
  RefreshCw,
  Play,
  Loader2,
} from 'lucide-react';
import { useProjects, useProjectPullRequests } from '@/hooks/useProjects';
import type { Project, PullRequest } from '@/hooks/useProjects';

// Component to render Pull Request list for a project
function ProjectPRList({ project, onSync }: { project: Project; onSync: (msg: string) => void }) {
  const router = useRouter();
  const { data: pullRequestsData, isLoading, refetch } = useProjectPullRequests(project.id, 'all');
  const [analyzingPRId, setAnalyzingPRId] = useState<string | null>(null);
  const [syncLoading, setSyncLoading] = useState(false);

  // Fix: backend returns { pull_requests: [...] }, not a direct array
  const pullRequests: PullRequest[] = useMemo(() => {
    if (!pullRequestsData) return [];
    if (Array.isArray(pullRequestsData)) return pullRequestsData;
    if (pullRequestsData.pull_requests && Array.isArray(pullRequestsData.pull_requests)) {
      return pullRequestsData.pull_requests;
    }
    return [];
  }, [pullRequestsData]);

  const handleSync = useCallback(async () => {
    setSyncLoading(true);
    try {
      const resp = await fetch(`/api/github/projects/${project.id}/sync`, { method: 'POST' });
      const data = await resp.json();
      if (resp.ok) {
        // Show backend's sync result message (includes PR counts)
        onSync(data.message || `${project.name} 同步完成`);
        // Refetch PRs after sync
        setTimeout(() => refetch(), 500);
      } else {
        alert(data.message || data.detail || 'Sync failed');
      }
    } catch (err) {
      alert('Sync failed: network error');
    } finally {
      setSyncLoading(false);
    }
  }, [project.id, refetch, onSync]);

  const handleAnalyze = useCallback(async (prId: string) => {
    setAnalyzingPRId(prId);
    try {
      const resp = await fetch(`/api/github/analyze/${prId}`, { method: 'POST' });
      const data = await resp.json();
      if (resp.ok) {
        // Force invalidate the cache and refetch immediately
        // The apiClient has a 5-min cache, so we clear the query cache via React Query
        refetch();
        // Poll for status change (analyzing → reviewed) every 2 seconds
        let pollCount = 0;
        const pollInterval = setInterval(() => {
          pollCount++;
          refetch();
          // Stop polling after 30 attempts (60 seconds)
          if (pollCount >= 30) clearInterval(pollInterval);
        }, 2000);
        // Also stop polling after 60 seconds as safety measure
        setTimeout(() => clearInterval(pollInterval), 62000);
      } else {
        alert(data.message || data.detail || '分析启动失败');
      }
    } catch (err) {
      alert('分析启动失败：网络错误');
    } finally {
      setAnalyzingPRId(null);
    }
  }, [refetch]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved': case 'merged': return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'rejected': case 'closed': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'analyzing': return <Activity className="h-4 w-4 text-blue-500" />;
      case 'reviewed': return <CheckCircle2 className="h-4 w-4 text-blue-500" />;
      default: return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'approved': case 'merged': case 'reviewed': return 'success' as const;
      case 'rejected': case 'closed': return 'destructive' as const;
      case 'analyzing': return 'default' as const;
      default: return 'outline' as const;
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: '待审查', analyzing: '分析中', reviewed: '已审查',
      approved: '已通过', rejected: '已拒绝', merged: '已合并', closed: '已关闭',
    };
    return labels[status] || status;
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Sync button */}
      {project.github_repo_url && (
        <div className="flex items-center justify-between border-b pb-3">
          <span className="text-sm text-muted-foreground">
            {pullRequests.length > 0 ? `${pullRequests.length} 个 Pull Request` : '暂无 Pull Request'}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={syncLoading}
          >
            {syncLoading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            {syncLoading ? '同步中...' : '从 GitHub 同步'}
          </Button>
        </div>
      )}

      {/* No GitHub repo linked */}
      {!project.github_repo_url && (
        <div className="text-center py-6">
          <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">此项目未关联 GitHub 仓库</p>
          <p className="text-xs text-muted-foreground mt-1">请先在项目设置中关联 GitHub 仓库</p>
        </div>
      )}

      {/* PR list */}
      {pullRequests.length === 0 && project.github_repo_url ? (
        <div className="text-center py-6">
          <GitPullRequest className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">暂无 Pull Request</p>
          <p className="text-xs text-muted-foreground mt-1">
            点击上方"从 GitHub 同步"按钮获取 Pull Request
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {pullRequests.map((pr) => (
            <div
              key={pr.id}
              className="flex items-start justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-start gap-3 flex-1">
                {getStatusIcon(pr.status)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-sm font-semibold truncate">
                      PR #{pr.github_pr_number || pr.number}: {pr.title}
                    </h4>
                    <Badge variant={getStatusBadgeVariant(pr.status)}>
                      {getStatusLabel(pr.status)}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    {pr.files_changed > 0 && <span>{pr.files_changed} 文件</span>}
                    {pr.lines_added > 0 && <span className="text-green-600">+{pr.lines_added}</span>}
                    {pr.lines_deleted > 0 && <span className="text-red-600">-{pr.lines_deleted}</span>}
                    {pr.branch_name && <span>{pr.branch_name}</span>}
                    <span>
                      <Clock className="inline h-3 w-3 mr-1" />
                      {new Date(pr.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {pr.risk_score !== null && pr.risk_score !== undefined && (
                  <Badge
                    variant={pr.risk_score > 70 ? 'destructive' : pr.risk_score > 40 ? 'warning' : 'success'}
                  >
                    风险: {pr.risk_score}
                  </Badge>
                )}
                {(pr.status === 'pending' || pr.status === 'analyzing') && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => { e.stopPropagation(); handleAnalyze(pr.id); }}
                    disabled={analyzingPRId === pr.id || pr.status === 'analyzing'}
                  >
                    {(analyzingPRId === pr.id || pr.status === 'analyzing') ? (
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    ) : (
                      <Play className="h-3 w-3 mr-1" />
                    )}
                    {(analyzingPRId === pr.id || pr.status === 'analyzing') ? '分析中' : '开始审查'}
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
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [syncMessage, setSyncMessage] = useState('');

  const filteredProjects = useMemo(() => {
    const list = Array.isArray(projects) ? projects : [];
    return list.filter((project: Project) => {
      if (searchTerm) {
        return project.name.toLowerCase().includes(searchTerm.toLowerCase());
      }
      return true;
    });
  }, [projects, searchTerm]);

  // Sort projects: those with GitHub repos first
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
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <GitPullRequest className="h-8 w-8" />
            Pull Requests
          </h1>
          <p className="text-muted-foreground mt-1">
            查看和管理所有项目的 Pull Request 代码审查
          </p>
        </div>

        {syncMessage && (
          <div className="p-3 rounded-lg bg-green-50 text-green-700 text-sm border border-green-200">
            {syncMessage}
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索项目..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="状态筛选" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="pending">待审查</SelectItem>
              <SelectItem value="approved">已通过</SelectItem>
              <SelectItem value="rejected">已拒绝</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-40 w-full" />
            ))}
          </div>
        ) : sortedProjects.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <GitPullRequest className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">暂无项目</h3>
              <p className="text-sm text-muted-foreground">
                请先在项目页面中添加项目
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {sortedProjects.map((project: Project) => (
              <Card key={project.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg flex items-center gap-2">
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
                          '未关联仓库'
                        )}
                      </CardDescription>
                    </div>
                    <Badge variant={project.language ? 'outline' : 'secondary'}>
                      {project.language || 'Unknown'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <ProjectPRList
                    project={project}
                    onSync={(msg) => setSyncMessage(msg)}
                  />
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
