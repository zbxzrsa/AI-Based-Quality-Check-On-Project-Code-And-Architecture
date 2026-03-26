'use client';

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Activity,
  CheckCircle2,
  Code,
  Network,
  Shield,
  TrendingUp,
  GitBranch,
} from 'lucide-react';
import { useProjects, useProjectAnalytics } from '@/hooks/useProjects';
import type { Project } from '@/hooks/useProjects';

function ProjectMetricCard({ project }: { project: Project }) {
  const router = useRouter();
  const { data: analytics, isLoading } = useProjectAnalytics(project.id);
  const metrics = analytics?.metrics ?? null;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return 'bg-green-600';
    if (score >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={() => router.push(`/projects/${project.id}`)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">{project.name}</CardTitle>
          <Badge variant="outline">{project.language || 'Unknown'}</Badge>
        </div>
        <CardDescription className="text-xs">
          {project.github_repo_url
            ? project.github_repo_url.replace('https://github.com/', '')
            : 'Repository not connected'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ) : metrics ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Overall health</span>
              <span className={`text-lg font-bold ${getScoreColor(metrics.overall_health)}`}>
                {metrics.overall_health}%
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-gray-200">
              <div
                className={`h-2 rounded-full ${getProgressColor(metrics.overall_health)}`}
                style={{ width: `${metrics.overall_health}%` }}
              />
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2">
              <div className="flex items-center gap-1.5">
                <Code className="h-3 w-3 text-blue-500" />
                <span className="text-xs text-muted-foreground">Code quality</span>
                <span className={`ml-auto text-xs font-semibold ${getScoreColor(metrics.code_quality)}`}>
                  {metrics.code_quality}%
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Shield className="h-3 w-3 text-green-500" />
                <span className="text-xs text-muted-foreground">Security rating</span>
                <span className={`ml-auto text-xs font-semibold ${getScoreColor(metrics.security_rating)}`}>
                  {metrics.security_rating}%
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Network className="h-3 w-3 text-purple-500" />
                <span className="text-xs text-muted-foreground">Architecture health</span>
                <span className={`ml-auto text-xs font-semibold ${getScoreColor(metrics.architecture_health)}`}>
                  {metrics.architecture_health}%
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-cyan-500" />
                <span className="text-xs text-muted-foreground">Test coverage</span>
                <span className={`ml-auto text-xs font-semibold ${getScoreColor(metrics.test_coverage)}`}>
                  {metrics.test_coverage}%
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-4 text-center">
            <Activity className="mx-auto mb-1 h-6 w-6 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">Analysis data is still loading.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function MetricsPage() {
  const { data: projects = [], isLoading } = useProjects();
  const projectList: Project[] = Array.isArray(projects) ? projects : [];

  const totalProjects = projectList.length;
  const linkedProjects = projectList.filter((project) => project.github_repo_url).length;
  const activeProjects = projectList.filter((project) => project.is_active).length;

  const languageDistribution = useMemo(() => {
    const languageCounts: Record<string, number> = {};

    projectList.forEach((project) => {
      const language = project.language || 'Unknown';
      languageCounts[language] = (languageCounts[language] || 0) + 1;
    });

    return Object.entries(languageCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
  }, [projectList]);

  const languageColors = [
    'bg-blue-500',
    'bg-green-500',
    'bg-yellow-500',
    'bg-purple-500',
    'bg-red-500',
    'bg-cyan-500',
    'bg-pink-500',
    'bg-orange-500',
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Metrics Dashboard"
          description="Track code quality, architecture health, repository coverage, and language distribution with the same dashboard layout used across the workspace."
        />

        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <Card className="border-white/70 bg-white/80 p-5 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total projects</p>
                <p className="text-3xl font-bold">{totalProjects}</p>
              </div>
              <Activity className="h-8 w-8 text-blue-500" />
            </div>
          </Card>
          <Card className="border-white/70 bg-white/80 p-5 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Connected repositories</p>
                <p className="text-3xl font-bold">{linkedProjects}</p>
              </div>
              <GitBranch className="h-8 w-8 text-green-500" />
            </div>
          </Card>
          <Card className="border-white/70 bg-white/80 p-5 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active projects</p>
                <p className="text-3xl font-bold">{activeProjects}</p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
          </Card>
          <Card className="border-white/70 bg-white/80 p-5 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Languages tracked</p>
                <p className="text-3xl font-bold">{languageDistribution.length}</p>
              </div>
              <Code className="h-8 w-8 text-purple-500" />
            </div>
          </Card>
        </div>

        {languageDistribution.length > 0 && (
          <Card className="border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
            <CardHeader>
              <CardTitle className="text-lg">Language Distribution</CardTitle>
              <CardDescription>Programming language usage across connected projects.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {languageDistribution.map(([language, count], index) => (
                  <div key={language} className="flex items-center gap-3">
                    <div
                      className={`h-3 w-3 rounded-full ${languageColors[index % languageColors.length]}`}
                    />
                    <span className="w-24 text-sm font-medium">{language}</span>
                    <div className="flex-1">
                      <div className="h-2 w-full rounded-full bg-gray-200">
                        <div
                          className={`h-2 rounded-full ${languageColors[index % languageColors.length]}`}
                          style={{ width: totalProjects > 0 ? `${(count / totalProjects) * 100}%` : '0%' }}
                        />
                      </div>
                    </div>
                    <span className="w-16 text-right text-sm text-muted-foreground">
                      {count} project{count === 1 ? '' : 's'}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <div>
          <h2 className="mb-4 text-xl font-semibold">Project metrics</h2>
          {isLoading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map((index) => (
                <Skeleton key={index} className="h-52" />
              ))}
            </div>
          ) : projectList.length === 0 ? (
            <Card className="border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <TrendingUp className="mb-4 h-12 w-12 text-muted-foreground" />
                <h3 className="mb-2 text-lg font-semibold">No data yet</h3>
                <p className="text-sm text-muted-foreground">
                  Add a project from the Projects page to start viewing metrics.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {projectList.map((project) => (
                <ProjectMetricCard key={project.id} project={project} />
              ))}
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
