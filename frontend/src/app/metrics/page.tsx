'use client';

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import {
  TrendingUp,
  Activity,
  Code,
  Shield,
  GitPullRequest,
  Network,
  CheckCircle2,
  AlertCircle,
  Clock,
  GitBranch,
} from 'lucide-react';
import { useProjects, useProjectAnalytics } from '@/hooks/useProjects';
import type { Project } from '@/hooks/useProjects';

// Individual project metric card
function ProjectMetricCard({ project }: { project: Project }) {
  const router = useRouter();
  const { data: analytics, isLoading } = useProjectAnalytics(project.id);
  const metrics = analytics?.metrics || null;

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
      className="hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => router.push(`/projects/${project.id}`)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{project.name}</CardTitle>
          <Badge variant="outline">{project.language || 'Unknown'}</Badge>
        </div>
        <CardDescription className="text-xs">
          {project.github_repo_url
            ? project.github_repo_url.replace('https://github.com/', '')
            : '未关联仓库'}
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
            {/* Overall Health */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">总体健康</span>
              <span className={`text-lg font-bold ${getScoreColor(metrics.overall_health)}`}>
                {metrics.overall_health}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${getProgressColor(metrics.overall_health)}`}
                style={{ width: `${metrics.overall_health}%` }}
              />
            </div>

            {/* Metric Breakdown */}
            <div className="grid grid-cols-2 gap-2 pt-2">
              <div className="flex items-center gap-1.5">
                <Code className="h-3 w-3 text-blue-500" />
                <span className="text-xs text-muted-foreground">代码质量</span>
                <span className={`text-xs font-semibold ml-auto ${getScoreColor(metrics.code_quality)}`}>
                  {metrics.code_quality}%
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Shield className="h-3 w-3 text-green-500" />
                <span className="text-xs text-muted-foreground">安全评分</span>
                <span className={`text-xs font-semibold ml-auto ${getScoreColor(metrics.security_rating)}`}>
                  {metrics.security_rating}%
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Network className="h-3 w-3 text-purple-500" />
                <span className="text-xs text-muted-foreground">架构健康</span>
                <span className={`text-xs font-semibold ml-auto ${getScoreColor(metrics.architecture_health)}`}>
                  {metrics.architecture_health}%
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-cyan-500" />
                <span className="text-xs text-muted-foreground">测试覆盖</span>
                <span className={`text-xs font-semibold ml-auto ${getScoreColor(metrics.test_coverage)}`}>
                  {metrics.test_coverage}%
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <Activity className="h-6 w-6 text-muted-foreground mx-auto mb-1" />
            <p className="text-xs text-muted-foreground">分析中...</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function MetricsPage() {
  const { data: projects = [], isLoading } = useProjects();
  const projectList: Project[] = Array.isArray(projects) ? projects : [];

  // Summary statistics
  const totalProjects = projectList.length;
  const linkedProjects = projectList.filter(p => p.github_repo_url).length;
  const activeProjects = projectList.filter(p => p.is_active).length;

  // Language distribution
  const languageDistribution = useMemo(() => {
    const langCounts: Record<string, number> = {};
    projectList.forEach(p => {
      const lang = p.language || 'Unknown';
      langCounts[lang] = (langCounts[lang] || 0) + 1;
    });
    return Object.entries(langCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
  }, [projectList]);

  const langColors = [
    'bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500',
    'bg-red-500', 'bg-cyan-500', 'bg-pink-500', 'bg-orange-500',
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <TrendingUp className="h-8 w-8" />
            Metrics Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            Track code quality, architecture health, and project metrics
          </p>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">总项目数</p>
                <p className="text-3xl font-bold">{totalProjects}</p>
              </div>
              <Activity className="h-8 w-8 text-blue-500" />
            </div>
          </Card>
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">已关联仓库</p>
                <p className="text-3xl font-bold">{linkedProjects}</p>
              </div>
              <GitBranch className="h-8 w-8 text-green-500" />
            </div>
          </Card>
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">活跃项目</p>
                <p className="text-3xl font-bold">{activeProjects}</p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
          </Card>
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">语言类型</p>
                <p className="text-3xl font-bold">{languageDistribution.length}</p>
              </div>
              <Code className="h-8 w-8 text-purple-500" />
            </div>
          </Card>
        </div>

        {/* Language Distribution */}
        {languageDistribution.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">语言分布</CardTitle>
              <CardDescription>项目使用的编程语言统计</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {languageDistribution.map(([lang, count], index) => (
                  <div key={lang} className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${langColors[index % langColors.length]}`} />
                    <span className="text-sm font-medium w-24">{lang}</span>
                    <div className="flex-1">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${langColors[index % langColors.length]}`}
                          style={{ width: `${(count / totalProjects) * 100}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-sm text-muted-foreground w-12 text-right">
                      {count} 个
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Per-Project Metrics */}
        <div>
          <h2 className="text-xl font-semibold mb-4">项目详细指标</h2>
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Skeleton key={i} className="h-52" />
              ))}
            </div>
          ) : projectList.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <TrendingUp className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">暂无数据</h3>
                <p className="text-sm text-muted-foreground">
                  请先在项目页面中添加项目以查看指标
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
