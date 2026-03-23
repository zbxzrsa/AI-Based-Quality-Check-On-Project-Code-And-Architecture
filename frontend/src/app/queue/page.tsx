'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import {
  Clock,
  Activity,
  CheckCircle2,
  XCircle,
  AlertCircle,
  PlayCircle,
  RotateCw,
  Eye,
  GitPullRequest,
} from 'lucide-react';
import { useProjects, useProjectPullRequests } from '@/hooks/useProjects';
import type { Project, PullRequest } from '@/hooks/useProjects';

// Component for showing analysis tasks for one project
function ProjectQueueSection({ project }: { project: Project }) {
  const router = useRouter();
  const { data: pullRequestsData = [], isLoading } = useProjectPullRequests(project.id, 'all');
  const pullRequests: PullRequest[] = Array.isArray(pullRequestsData) ? pullRequestsData : [];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
      case 'merged':
      case 'reviewed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'rejected':
      case 'closed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'analyzing':
        return <PlayCircle className="h-4 w-4 text-blue-500 animate-pulse" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'approved':
      case 'merged':
      case 'reviewed':
        return <Badge variant="success">已完成</Badge>;
      case 'rejected':
      case 'closed':
        return <Badge variant="destructive">已关闭</Badge>;
      case 'analyzing':
        return <Badge variant="default">分析中</Badge>;
      case 'pending':
        return <Badge variant="outline">排队中</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (isLoading) {
    return (
      <>
        {[1, 2].map((i) => (
          <TableRow key={`skeleton-${project.id}-${i}`}>
            <TableCell><div className="h-4 w-24 animate-pulse rounded bg-muted" /></TableCell>
            <TableCell><div className="h-4 w-16 animate-pulse rounded bg-muted" /></TableCell>
            <TableCell><div className="h-4 w-32 animate-pulse rounded bg-muted" /></TableCell>
            <TableCell><div className="h-4 w-16 animate-pulse rounded bg-muted" /></TableCell>
            <TableCell><div className="h-4 w-20 animate-pulse rounded bg-muted" /></TableCell>
            <TableCell><div className="h-4 w-28 animate-pulse rounded bg-muted" /></TableCell>
            <TableCell><div className="h-4 w-8 animate-pulse rounded bg-muted" /></TableCell>
          </TableRow>
        ))}
      </>
    );
  }

  if (pullRequests.length === 0) return null;

  return (
    <>
      {pullRequests.map((pr) => (
        <TableRow
          key={pr.id}
          className="cursor-pointer hover:bg-accent/50"
          onClick={() => router.push(`/projects/${project.id}`)}
        >
          <TableCell>
            <div className="flex items-center gap-2">
              {getStatusIcon(pr.status)}
              <span className="font-medium">{project.name}</span>
            </div>
          </TableCell>
          <TableCell>
            <div className="flex items-center gap-1">
              <GitPullRequest className="h-3 w-3" />
              PR #{pr.github_pr_number}
            </div>
          </TableCell>
          <TableCell className="max-w-[200px] truncate">
            {pr.title}
          </TableCell>
          <TableCell>{getStatusBadge(pr.status)}</TableCell>
          <TableCell>
            {pr.risk_score !== null && pr.risk_score !== undefined ? (
              <div className="flex items-center gap-2">
                <Progress
                  value={pr.risk_score}
                  className="w-16 h-2"
                />
                <span className="text-xs">{pr.risk_score}%</span>
              </div>
            ) : (
              <span className="text-xs text-muted-foreground">-</span>
            )}
          </TableCell>
          <TableCell className="text-xs text-muted-foreground">
            {new Date(pr.created_at).toLocaleString()}
          </TableCell>
          <TableCell>
            <Button variant="ghost" size="sm">
              <Eye className="h-4 w-4" />
            </Button>
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}

export default function QueuePage() {
  const { data: projects = [], isLoading } = useProjects();
  const projectList: Project[] = Array.isArray(projects) ? projects : [];

  // Simple counts
  const totalProjects = projectList.length;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Activity className="h-8 w-8" />
              Analysis Queue
            </h1>
            <p className="text-muted-foreground mt-1">
              Monitor code review and architecture analysis tasks
            </p>
          </div>
          <Button variant="outline" onClick={() => window.location.reload()}>
            <RotateCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">总项目数</p>
                <p className="text-2xl font-bold">{totalProjects}</p>
              </div>
              <Activity className="h-8 w-8 text-blue-500" />
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">已关联仓库</p>
                <p className="text-2xl font-bold">
                  {projectList.filter(p => p.github_repo_url).length}
                </p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">活跃项目</p>
                <p className="text-2xl font-bold">
                  {projectList.filter(p => p.is_active).length}
                </p>
              </div>
              <PlayCircle className="h-8 w-8 text-blue-500" />
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">无仓库项目</p>
                <p className="text-2xl font-bold">
                  {projectList.filter(p => !p.github_repo_url).length}
                </p>
              </div>
              <AlertCircle className="h-8 w-8 text-yellow-500" />
            </div>
          </Card>
        </div>

        {/* Task Queue Table */}
        <Card>
          <CardHeader>
            <CardTitle>Analysis Tasks</CardTitle>
            <CardDescription>所有项目的 Pull Request 分析任务</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : projectList.length === 0 ? (
              <div className="text-center py-12">
                <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">暂无分析任务</h3>
                <p className="text-sm text-muted-foreground">
                  当项目有新的 Pull Request 时，分析任务会自动添加到队列
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>项目</TableHead>
                    <TableHead>PR</TableHead>
                    <TableHead>标题</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>风险分数</TableHead>
                    <TableHead>提交时间</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {projectList.map((project) => (
                    <ProjectQueueSection key={project.id} project={project} />
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
