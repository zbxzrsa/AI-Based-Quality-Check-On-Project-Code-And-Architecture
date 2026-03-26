'use client';

import { useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { PageHeader } from '@/components/layout/page-header';
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
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  Eye,
  GitPullRequest,
  PlayCircle,
  RotateCw,
  XCircle,
} from 'lucide-react';
import { useProjects, useProjectPullRequests } from '@/hooks/useProjects';
import type { Project, PullRequest } from '@/hooks/useProjects';

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
        return <PlayCircle className="h-4 w-4 animate-pulse text-blue-500" />;
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
        return <Badge variant="success">Completed</Badge>;
      case 'rejected':
      case 'closed':
        return <Badge variant="destructive">Closed</Badge>;
      case 'analyzing':
        return <Badge variant="default">Analyzing</Badge>;
      case 'pending':
        return <Badge variant="outline">Queued</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (isLoading) {
    return (
      <>
        {[1, 2].map((index) => (
          <TableRow key={`skeleton-${project.id}-${index}`}>
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

  if (pullRequests.length === 0) {
    return null;
  }

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
          <TableCell className="max-w-[200px] truncate">{pr.title}</TableCell>
          <TableCell>{getStatusBadge(pr.status)}</TableCell>
          <TableCell>
            {pr.risk_score !== null && pr.risk_score !== undefined ? (
              <div className="flex items-center gap-2">
                <Progress value={pr.risk_score} className="h-2 w-16" />
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
            <Button variant="ghost" size="sm" aria-label={`View ${pr.title}`}>
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

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Analysis Queue"
          description="Monitor pull request reviews and architecture analysis activity in one place with the same dashboard rhythm used across the rest of the product."
          actions={
            <Button variant="outline" onClick={() => window.location.reload()}>
              <RotateCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          }
        />

        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <Card className="border-white/70 bg-white/80 p-4 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total projects</p>
                <p className="text-2xl font-bold">{projectList.length}</p>
              </div>
              <Activity className="h-8 w-8 text-blue-500" />
            </div>
          </Card>
          <Card className="border-white/70 bg-white/80 p-4 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Connected repositories</p>
                <p className="text-2xl font-bold">
                  {projectList.filter((project) => project.github_repo_url).length}
                </p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
          </Card>
          <Card className="border-white/70 bg-white/80 p-4 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active projects</p>
                <p className="text-2xl font-bold">
                  {projectList.filter((project) => project.is_active).length}
                </p>
              </div>
              <PlayCircle className="h-8 w-8 text-blue-500" />
            </div>
          </Card>
          <Card className="border-white/70 bg-white/80 p-4 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Projects awaiting setup</p>
                <p className="text-2xl font-bold">
                  {projectList.filter((project) => !project.github_repo_url).length}
                </p>
              </div>
              <AlertCircle className="h-8 w-8 text-yellow-500" />
            </div>
          </Card>
        </div>

        <Card className="border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
          <CardHeader>
            <CardTitle>Analysis Tasks</CardTitle>
            <CardDescription>Pull request analysis tasks across all projects.</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((index) => (
                  <Skeleton key={index} className="h-12 w-full" />
                ))}
              </div>
            ) : projectList.length === 0 ? (
              <div className="py-12 text-center">
                <Activity className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                <h3 className="mb-2 text-lg font-semibold">No analysis tasks yet</h3>
                <p className="text-sm text-muted-foreground">
                  New pull requests will appear here automatically after repository analysis begins.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Project</TableHead>
                    <TableHead>PR</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Risk score</TableHead>
                    <TableHead>Submitted</TableHead>
                    <TableHead>Action</TableHead>
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
