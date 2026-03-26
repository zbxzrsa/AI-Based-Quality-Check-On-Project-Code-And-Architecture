'use client'

import Link from 'next/link'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { MainLayout } from '@/components/layout/main-layout'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import ArchitectureGraph from '@/components/architecture/architecture-graph'
import SystemArchitectureGraph from '@/components/architecture/system-architecture-graph'
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  GitBranch,
  Loader2,
  Play,
  RefreshCw,
  Settings,
  ShieldCheck,
  Trash2,
} from 'lucide-react'
import {
  useArchitectureOverview,
  useBranchArchitecture,
  useDeleteProject,
  useProject,
  useProjectAnalytics,
  useProjectArchitectureAnalysis,
  useProjectBranches,
  useProjectIssues,
  useProjectPullRequests,
  useSyncProject,
  type ProjectIssue,
  type PullRequest,
  type RecentReview,
} from '@/hooks/useProjects'
import { useToast } from '@/hooks/use-toast'
import { apiPost } from '@/lib/api-client'

const LIVE_STATUSES = ['pending', 'analyzing', 'in_progress']

const formatDate = (value?: string | null) => {
  if (!value) return 'Not available'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Not available' : date.toLocaleString()
}

const scoreClass = (score?: number | null) => {
  if (typeof score !== 'number') return 'text-muted-foreground'
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

const statusVariant = (status?: string) => {
  switch ((status || '').toLowerCase()) {
    case 'approved':
    case 'merged':
    case 'completed':
    case 'reviewed':
    case 'healthy':
    case 'active':
      return 'success' as const
    case 'analyzing':
    case 'in_progress':
    case 'pending':
    case 'open':
    case 'warning':
      return 'warning' as const
    case 'failed':
    case 'rejected':
    case 'closed':
    case 'critical':
      return 'destructive' as const
    default:
      return 'outline' as const
  }
}

const severityVariant = (severity?: string) => {
  switch ((severity || '').toLowerCase()) {
    case 'critical':
    case 'high':
      return 'destructive' as const
    case 'medium':
      return 'warning' as const
    case 'low':
    case 'info':
      return 'outline' as const
    default:
      return 'secondary' as const
  }
}

const toSentenceCase = (value?: string | null) => {
  if (!value) return 'Unknown'
  return value.replace(/[_-]/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg border border-dashed p-8 text-center">
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  )
}

function MetricCard({
  title,
  value,
  detail,
  valueClassName = '',
}: {
  title: string
  value: string
  detail: string
  valueClassName?: string
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${valueClassName}`}>{value}</div>
        <p className="text-xs text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  )
}

function PullRequestList({
  pullRequests,
  analyzingPRId,
  onAnalyze,
}: {
  pullRequests: PullRequest[]
  analyzingPRId: string | null
  onAnalyze: (prId: string) => Promise<void>
}) {
  if (pullRequests.length === 0) {
    return (
      <EmptyState
        title="No pull requests yet"
        description="Connect a repository and run a sync to load pull requests for live review."
      />
    )
  }

  return (
    <div className="space-y-4">
      {pullRequests.map((pr) => {
        const isAnalyzing = analyzingPRId === pr.id || pr.status === 'analyzing'
        const isLiveGitHubOnly = pr.id.startsWith('github-')

        return (
          <Card key={pr.id}>
            <CardContent className="flex flex-col gap-4 p-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold">
                    PR #{pr.github_pr_number}: {pr.title}
                  </h3>
                  <Badge variant={statusVariant(pr.status)}>{toSentenceCase(pr.status)}</Badge>
                  <Badge variant="outline">{pr.branch_name || 'No branch'}</Badge>
                  {LIVE_STATUSES.includes(pr.status) && (
                    <Badge variant="secondary" className="gap-1">
                      <Activity className="h-3 w-3" />
                      Live
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  {pr.description || 'No pull request description provided.'}
                </p>
                <div className="grid gap-3 text-sm text-muted-foreground md:grid-cols-2 xl:grid-cols-4">
                  <p>
                    Files changed:{' '}
                    <span className="font-medium text-foreground">{pr.files_changed}</span>
                  </p>
                  <p>
                    Lines added:{' '}
                    <span className="font-medium text-green-600">+{pr.lines_added}</span>
                  </p>
                  <p>
                    Lines deleted:{' '}
                    <span className="font-medium text-red-600">-{pr.lines_deleted}</span>
                  </p>
                  <p>
                    Analyzed:{' '}
                    <span className="font-medium text-foreground">
                      {formatDate(pr.analyzed_at || pr.updated_at)}
                    </span>
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => void onAnalyze(pr.id)}
                    disabled={isAnalyzing || isLiveGitHubOnly}
                  >
                    {isAnalyzing ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    {isLiveGitHubOnly
                      ? 'Sync before review'
                      : pr.analyzed_at
                        ? 'Re-run review'
                        : 'Start review'}
                  </Button>
                  {!isLiveGitHubOnly && (
                    <Button asChild variant="outline" size="sm">
                      <Link href={`/reviews/${pr.id}`}>Open review</Link>
                    </Button>
                  )}
                </div>
              </div>
              <div className="min-w-[140px] rounded-lg border p-4 text-center">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Risk score</p>
                <p className={`mt-2 text-3xl font-bold ${scoreClass(pr.risk_score)}`}>
                  {typeof pr.risk_score === 'number' ? pr.risk_score : 'N/A'}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Live review status updates every few seconds
                </p>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function IssueList({ issues }: { issues: ProjectIssue[] }) {
  if (issues.length === 0) {
    return (
      <EmptyState
        title="No static review issues"
        description="Run repository sync and pull request analysis to populate issue findings."
      />
    )
  }

  return (
    <div className="space-y-4">
      {issues.map((issue) => (
        <Card key={issue.id}>
          <CardContent className="space-y-3 p-5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={severityVariant(issue.severity)}>{toSentenceCase(issue.severity)}</Badge>
              <Badge variant="outline">{toSentenceCase(issue.category)}</Badge>
              {issue.rule_name && <Badge variant="secondary">{issue.rule_name}</Badge>}
            </div>
            <p className="font-medium">{issue.message}</p>
            <div className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
              <p>
                File:{' '}
                <span className="font-medium text-foreground">
                  {issue.file_path || 'Unknown file'}
                </span>
              </p>
              <p>
                Line:{' '}
                <span className="font-medium text-foreground">{issue.line_number ?? 'N/A'}</span>
              </p>
              <p>
                Detected:{' '}
                <span className="font-medium text-foreground">{formatDate(issue.created_at)}</span>
              </p>
              <p>
                Rule ID:{' '}
                <span className="font-medium text-foreground">{issue.rule_id || 'N/A'}</span>
              </p>
            </div>
            {issue.suggested_fix && (
              <div className="rounded-lg bg-muted/50 p-3 text-sm">
                <p className="font-medium">Suggested fix</p>
                <p className="mt-1 text-muted-foreground">{issue.suggested_fix}</p>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function RelatedFindingsFallback({
  title,
  description,
  pullRequests,
  recentReviews,
}: {
  title: string
  description: string
  pullRequests: PullRequest[]
  recentReviews: RecentReview[]
}) {
  const relatedReviews = recentReviews.slice(0, 5)
  const relatedPullRequests = pullRequests.slice(0, 5)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          No explicit findings are stored for this tab yet. The latest repository review context is shown below so you can still inspect related activity.
        </CardContent>
      </Card>

      {relatedReviews.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {relatedReviews.map((review) => (
            <Card key={review.pr_id}>
              <CardContent className="space-y-3 p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusVariant(review.status)}>
                    {toSentenceCase(review.status)}
                  </Badge>
                  <Badge variant="outline">PR #{review.pr_number}</Badge>
                </div>
                <p className="font-medium">{review.title}</p>
                <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
                  <p>
                    Risk score:{' '}
                    <span className="font-medium text-foreground">
                      {typeof review.risk_score === 'number' ? review.risk_score : 'N/A'}
                    </span>
                  </p>
                  <p>
                    Last analyzed:{' '}
                    <span className="font-medium text-foreground">
                      {formatDate(review.analyzed_at)}
                    </span>
                  </p>
                  <p>
                    Files changed:{' '}
                    <span className="font-medium text-foreground">{review.files_changed}</span>
                  </p>
                  <p>
                    Diff size:{' '}
                    <span className="font-medium text-foreground">
                      +{review.lines_added} / -{review.lines_deleted}
                    </span>
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : relatedPullRequests.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {relatedPullRequests.map((pr) => (
            <Card key={pr.id}>
              <CardContent className="space-y-3 p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusVariant(pr.status)}>{toSentenceCase(pr.status)}</Badge>
                  <Badge variant="outline">PR #{pr.github_pr_number}</Badge>
                </div>
                <p className="font-medium">{pr.title}</p>
                <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
                  <p>
                    Branch:{' '}
                    <span className="font-medium text-foreground">{pr.branch_name || 'Unknown'}</span>
                  </p>
                  <p>
                    Risk score:{' '}
                    <span className="font-medium text-foreground">
                      {typeof pr.risk_score === 'number' ? pr.risk_score : 'N/A'}
                    </span>
                  </p>
                  <p>
                    Files changed:{' '}
                    <span className="font-medium text-foreground">{pr.files_changed}</span>
                  </p>
                  <p>
                    Updated:{' '}
                    <span className="font-medium text-foreground">
                      {formatDate(pr.analyzed_at || pr.updated_at || pr.created_at)}
                    </span>
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No related review context yet"
          description="Sync GitHub to import pull requests and generate repository review context for this tab."
        />
      )}
    </div>
  )
}

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const projectId = (params?.id as string) || ''
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [selectedBranchId, setSelectedBranchId] = useState('')
  const [analyzingPRId, setAnalyzingPRId] = useState<string | null>(null)
  const hasAutoTriggeredSync = useRef(false)

  const {
    data: project,
    isLoading,
  } = useProject(projectId)
  const pullRequestsQuery = useProjectPullRequests(projectId)
  const analyticsQuery = useProjectAnalytics(projectId)
  const architectureAnalysisQuery = useProjectArchitectureAnalysis(projectId)
  const branchesQuery = useProjectBranches(projectId)
  const architectureOverviewQuery = useArchitectureOverview(projectId)
  const issuesQuery = useProjectIssues(projectId)
  const branchArchitectureQuery = useBranchArchitecture(projectId, selectedBranchId)
  const deleteProject = useDeleteProject()
  const syncProject = useSyncProject()

  const pullRequests = pullRequestsQuery.data || []
  const analytics = analyticsQuery.data
  const architectureAnalysis = architectureAnalysisQuery.data
  const branches = branchesQuery.data || []
  const architectureOverview = architectureOverviewQuery.data
  const issues = issuesQuery.data?.issues || []
  const branchArchitecture = branchArchitectureQuery.data
  const metrics = analytics?.metrics || null
  const recentReviews = analytics?.recent_reviews || []
  const dependencyStats = analytics?.dependency_stats
  const performanceMetrics = analytics?.performance_metrics
  const trendStats = analytics?.trends

  useEffect(() => {
    if (!branches.length) {
      if (selectedBranchId) setSelectedBranchId('')
      return
    }

    if (!selectedBranchId || !branches.some((branch) => branch.id === selectedBranchId)) {
      setSelectedBranchId(branches[0].id)
    }
  }, [branches, selectedBranchId])

  useEffect(() => {
    if (!projectId || !project?.github_repo_url || hasAutoTriggeredSync.current) {
      return
    }

    if (syncProject.isPending || pullRequestsQuery.isLoading || branchesQuery.isLoading) {
      return
    }

    if (pullRequests.length > 0 || branches.length > 0) {
      return
    }

    hasAutoTriggeredSync.current = true

    void syncProject.mutateAsync(projectId).then(
      () => {
        toast({
          title: 'GitHub sync started',
          description: 'Importing pull requests, issues, and branches for this project.',
        })
      },
      (error) => {
        toast({
          variant: 'destructive',
          title: 'Automatic sync failed',
          description: error instanceof Error ? error.message : 'Please try Sync GitHub manually.',
        })
      }
    )
  }, [
    branches.length,
    branchesQuery.isLoading,
    project?.github_repo_url,
    projectId,
    pullRequests.length,
    pullRequestsQuery.isLoading,
    syncProject,
    toast,
  ])

  const selectedBranch = useMemo(
    () => branches.find((branch) => branch.id === selectedBranchId) || null,
    [branches, selectedBranchId]
  )

  const securityHotspots = useMemo(
    () =>
      issues.filter((issue) => {
        const severity = issue.severity.toLowerCase()
        const category = (issue.category || '').toLowerCase()
        return category.includes('security') || severity === 'critical' || severity === 'high'
      }),
    [issues]
  )

  const livePullRequests = useMemo(
    () => pullRequests.filter((pr) => LIVE_STATUSES.includes(pr.status)),
    [pullRequests]
  )

  const lastReviewTimestamp = useMemo(() => {
    const timestamps = [
      analytics?.analysis_timestamp,
      architectureAnalysis?.analysis_timestamp,
      ...pullRequests.map((pr) => pr.analyzed_at || pr.updated_at || null),
      ...issues.map((issue) => issue.created_at || null),
    ]
      .filter(Boolean)
      .map((value) => new Date(value as string).getTime())
      .filter((value) => !Number.isNaN(value))

    if (!timestamps.length) return null
    return new Date(Math.max(...timestamps)).toISOString()
  }, [analytics?.analysis_timestamp, architectureAnalysis?.analysis_timestamp, issues, pullRequests])

  const summaryHighlights = useMemo(() => {
    const items: string[] = []

    if (typeof metrics?.overall_health === 'number') {
      items.push(`Overall health is ${metrics.overall_health}% based on live review and architecture signals.`)
    }
    if (typeof analytics?.reviewed_prs === 'number' && typeof analytics?.total_prs === 'number') {
      items.push(`${analytics.reviewed_prs} of ${analytics.total_prs} pull requests have completed review.`)
    }
    if (typeof analytics?.issue_stats?.total === 'number') {
      items.push(`${analytics.issue_stats.total} static findings are currently tracked across the repository.`)
    }
    if (branches.length > 0) {
      items.push(`${branches.length} active branches are available for architecture comparison.`)
    }
    if (livePullRequests.length > 0) {
      items.push(`${livePullRequests.length} pull requests are still streaming fresh analysis results.`)
    }

    return items
  }, [
    analytics?.issue_stats?.total,
    analytics?.reviewed_prs,
    analytics?.total_prs,
    branches.length,
    livePullRequests.length,
    metrics?.overall_health,
  ])

  const handleDeleteProject = async () => {
    try {
      await deleteProject.mutateAsync(projectId)
      toast({
        title: 'Project deleted',
        description: 'The project and its analysis data were removed.',
      })
      router.push('/projects')
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Delete failed',
        description: error instanceof Error ? error.message : 'Unable to delete this project.',
      })
    }
  }

  const handleSync = async () => {
    try {
      await syncProject.mutateAsync(projectId)
      toast({
        title: 'Sync started',
        description: 'GitHub pull requests and branch data are being refreshed now.',
      })
      void Promise.allSettled([
        pullRequestsQuery.refetch(),
        analyticsQuery.refetch(),
        issuesQuery.refetch(),
        branchesQuery.refetch(),
        architectureOverviewQuery.refetch(),
      ])
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Sync failed',
        description: error instanceof Error ? error.message : 'Unable to sync the project right now.',
      })
    }
  }

  const handleAnalyze = async (prId: string) => {
    try {
      setAnalyzingPRId(prId)
      await apiPost(`/api/github/analyze/${prId}`)
      toast({
        title: 'Review started',
        description: 'The pull request is being reviewed and this page will refresh automatically.',
      })
      void Promise.allSettled([
        pullRequestsQuery.refetch(),
        analyticsQuery.refetch(),
        issuesQuery.refetch(),
        architectureOverviewQuery.refetch(),
        branchesQuery.refetch(),
        branchArchitectureQuery.refetch(),
      ])
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Review failed to start',
        description:
          error instanceof Error ? error.message : 'Unable to start live pull request review.',
      })
    } finally {
      setAnalyzingPRId(null)
    }
  }

  if (isLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <Skeleton className="h-12 w-3/4" />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, index) => (
              <Skeleton key={index} className="h-32" />
            ))}
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </MainLayout>
    )
  }

  if (!project) {
    return (
      <MainLayout>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertTriangle className="mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="mb-2 text-lg font-semibold">Project not found</h3>
            <Button onClick={() => router.push('/projects')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Projects
            </Button>
          </CardContent>
        </Card>
      </MainLayout>
    )
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title={project.name}
          description={project.description || 'No project description available.'}
          actions={
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => router.push('/projects')}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
              <Button
                variant="outline"
                onClick={handleSync}
                disabled={syncProject.isPending}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${syncProject.isPending ? 'animate-spin' : ''}`}
                />
                Sync GitHub
              </Button>
              <Button onClick={() => router.push(`/projects/${project.id}/settings`)}>
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </Button>
              <Button
                variant="destructive"
                onClick={() => setShowDeleteDialog(true)}
                disabled={deleteProject.isPending}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </Button>
            </div>
          }
        />

        <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete project?</AlertDialogTitle>
              <AlertDialogDescription>
                This permanently removes the project, pull request history, review comments,
                and architecture analysis.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={deleteProject.isPending}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteProject}
                disabled={deleteProject.isPending}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleteProject.isPending ? 'Deleting...' : 'Delete project'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            title="Overall Health"
            value={typeof metrics?.overall_health === 'number' ? `${metrics.overall_health}%` : 'N/A'}
            detail="Combined quality, security, architecture, and test signals"
            valueClassName={scoreClass(metrics?.overall_health)}
          />
          <MetricCard
            title="Pull Requests"
            value={String(pullRequests.length)}
            detail="Imported from GitHub and available for review"
          />
          <MetricCard
            title="Static Issues"
            value={String(analytics?.issue_stats?.total ?? issues.length)}
            detail="Current findings from AI review and rule-based analysis"
          />
          <MetricCard
            title="Branches"
            value={String(branches.length)}
            detail="Branches available for architecture exploration"
          />
        </div>

        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-medium">Live review pipeline</p>
              <p className="text-sm text-muted-foreground">
                Project details, issues, pull requests, and architecture graphs refresh every 5 seconds.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <Badge variant={project.github_repo_url ? 'success' : 'warning'}>
                {project.github_repo_url ? 'GitHub connected' : 'GitHub missing'}
              </Badge>
              <Badge variant={livePullRequests.length > 0 ? 'warning' : 'success'}>
                {livePullRequests.length > 0
                  ? `${livePullRequests.length} reviews running`
                  : 'No active reviews'}
              </Badge>
              <Badge variant="outline" className="gap-1">
                <Clock3 className="h-3 w-3" />
                Last update: {formatDate(lastReviewTimestamp)}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="flex h-auto flex-wrap justify-start gap-2 bg-transparent p-0">
            {[
              'Overview',
              'Analysis',
              'Summary',
              'Issues',
              'Architecture',
              'Security hotspots',
              'Intended architecture',
              'Pull Requests',
              'Branches',
            ].map((tab) => (
              <TabsTrigger
                key={tab}
                value={tab.toLowerCase().replace(/\s+/g, '-')}
                className="border"
              >
                {tab}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
              <Card>
                <CardHeader>
                  <CardTitle>Project profile</CardTitle>
                  <CardDescription>Repository, ownership, and live integration status.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Repository</p>
                    <p className="mt-1 break-all text-sm">
                      {project.github_repo_url || 'Not connected yet'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Primary language</p>
                    <p className="mt-1 text-sm">{project.language || 'Unknown'}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Owner</p>
                    <p className="mt-1 text-sm">{project.owner_id}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Status</p>
                    <div className="mt-1">
                      <Badge variant={project.is_active ? 'success' : 'outline'}>
                        {project.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Created</p>
                    <p className="mt-1 text-sm">{formatDate(project.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Last updated</p>
                    <p className="mt-1 text-sm">{formatDate(project.updated_at)}</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Review readiness</CardTitle>
                  <CardDescription>Whether the project is ready for real-time GitHub review.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Authentication</span>
                    <Badge variant="success">Available</Badge>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>GitHub repository linked</span>
                    <Badge variant={project.github_repo_url ? 'success' : 'warning'}>
                      {project.github_repo_url ? 'Connected' : 'Missing'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Pull request data</span>
                    <Badge variant={pullRequests.length > 0 ? 'success' : 'warning'}>
                      {pullRequests.length > 0 ? 'Loaded' : 'Pending sync'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Architecture graph</span>
                    <Badge variant={architectureOverview?.nodes?.length ? 'success' : 'warning'}>
                      {architectureOverview?.nodes?.length ? 'Ready' : 'Generating'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Last live refresh</span>
                    <span className="font-medium">{formatDate(lastReviewTimestamp)}</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="analysis" className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-3">
              <Card className="xl:col-span-2">
                <CardHeader>
                  <CardTitle>Quality analysis</CardTitle>
                  <CardDescription>
                    Current project health based on analytics and review signals.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Code quality</p>
                    <p className={`mt-2 text-2xl font-bold ${scoreClass(metrics?.code_quality)}`}>
                      {metrics?.code_quality ?? 'N/A'}%
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Security rating</p>
                    <p className={`mt-2 text-2xl font-bold ${scoreClass(metrics?.security_rating)}`}>
                      {metrics?.security_rating ?? 'N/A'}%
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Architecture health</p>
                    <p className={`mt-2 text-2xl font-bold ${scoreClass(metrics?.architecture_health)}`}>
                      {metrics?.architecture_health ?? 'N/A'}%
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Test coverage</p>
                    <p className={`mt-2 text-2xl font-bold ${scoreClass(metrics?.test_coverage)}`}>
                      {metrics?.test_coverage ?? 'N/A'}%
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Trend snapshot</CardTitle>
                  <CardDescription>Latest month-over-month movement.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="rounded-lg border p-3">
                    <p className="text-muted-foreground">Code quality change</p>
                    <p className="mt-1 text-lg font-semibold">{trendStats?.code_quality_change ?? 0}%</p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-muted-foreground">Test coverage change</p>
                    <p className="mt-1 text-lg font-semibold">{trendStats?.test_coverage_change ?? 0}%</p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-muted-foreground">Issue volume change</p>
                    <p className="mt-1 text-lg font-semibold">{trendStats?.issues_change ?? 0}%</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Dependency analysis</CardTitle>
                  <CardDescription>Dependency health and circularity signals.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Total dependencies</p>
                    <p className="mt-2 text-2xl font-bold">{dependencyStats?.total ?? 0}</p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Circular dependencies</p>
                    <p className="mt-2 text-2xl font-bold">{dependencyStats?.circular ?? 0}</p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Outdated dependencies</p>
                    <p className="mt-2 text-2xl font-bold">{dependencyStats?.outdated ?? 0}</p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Dependency issues</p>
                    <p className="mt-2 text-2xl font-bold">{dependencyStats?.dependency_issues ?? 0}</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Pipeline timing</CardTitle>
                  <CardDescription>Operational timings for build, test, and review workflow.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Average build time</span>
                    <span className="font-medium">{performanceMetrics?.avg_build_time || 'N/A'}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Average test time</span>
                    <span className="font-medium">{performanceMetrics?.avg_test_time || 'N/A'}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Average analysis time</span>
                    <span className="font-medium">{performanceMetrics?.avg_analysis_time || 'N/A'}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Average PR review time</span>
                    <span className="font-medium">{performanceMetrics?.pr_review_time_avg || 'N/A'}</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="summary" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Executive summary</CardTitle>
                <CardDescription>
                  A concise view of project review readiness and current findings.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {summaryHighlights.length > 0 ? (
                  summaryHighlights.map((item) => (
                    <div
                      key={item}
                      className="flex items-start gap-3 rounded-lg border p-4 text-sm"
                    >
                      <CheckCircle2 className="mt-0.5 h-4 w-4 text-green-600" />
                      <span>{item}</span>
                    </div>
                  ))
                ) : (
                  <EmptyState
                    title="Summary will appear here"
                    description="Sync GitHub and run analysis to generate a fuller project summary."
                  />
                )}
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Recent review activity</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {recentReviews.length > 0 ? (
                    recentReviews.slice(0, 5).map((review) => (
                      <div key={review.pr_id} className="rounded-lg border p-4 text-sm">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium">
                            PR #{review.pr_number}: {review.title}
                          </p>
                          <Badge variant={statusVariant(review.status)}>
                            {toSentenceCase(review.status)}
                          </Badge>
                        </div>
                        <p className="mt-2 text-muted-foreground">
                          Risk score: {review.risk_score ?? 'N/A'} | Reviewed:{' '}
                          {formatDate(review.analyzed_at)}
                        </p>
                      </div>
                    ))
                  ) : (
                    <EmptyState
                      title="No review history yet"
                      description="Recent pull request reviews will be listed here after the first analysis run."
                    />
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Issue distribution</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Critical</span>
                    <Badge variant="destructive">{analytics?.issue_stats?.critical ?? 0}</Badge>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>High</span>
                    <Badge variant="destructive">{analytics?.issue_stats?.high ?? 0}</Badge>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Medium</span>
                    <Badge variant="warning">{analytics?.issue_stats?.medium ?? 0}</Badge>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <span>Low</span>
                    <Badge variant="outline">{analytics?.issue_stats?.low ?? 0}</Badge>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="issues">
            {issues.length > 0 ? (
              <IssueList issues={issues} />
            ) : (
              <RelatedFindingsFallback
                title="Issue context"
                description="Static issue findings have not been generated for this repository yet."
                pullRequests={pullRequests}
                recentReviews={recentReviews}
              />
            )}
          </TabsContent>

          <TabsContent value="architecture" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Architecture overview</CardTitle>
                <CardDescription>
                  Live overall architecture generated from the latest review and repository analysis.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {architectureOverview?.nodes?.length ? (
                  <SystemArchitectureGraph
                    nodes={architectureOverview.nodes}
                    edges={architectureOverview.edges}
                    groups={architectureOverview.groups}
                  />
                ) : (
                  <EmptyState
                    title="Architecture graph is still warming up"
                    description="Once analysis is available, the system components and relationships will appear here."
                  />
                )}
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Architecture health</CardTitle>
                  <CardDescription>Current overview generated from live architecture data.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Overall</p>
                    <p className="mt-2 text-2xl font-bold">
                      {toSentenceCase(architectureOverview?.health_summary?.overall || 'unknown')}
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Components</p>
                    <p className="mt-2 text-2xl font-bold">
                      {architectureOverview?.health_summary?.total_components ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Warnings</p>
                    <p className="mt-2 text-2xl font-bold">
                      {architectureOverview?.health_summary?.warning_components ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Violations</p>
                    <p className="mt-2 text-2xl font-bold">
                      {architectureOverview?.health_summary?.total_violations ?? 0}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Architecture recommendations</CardTitle>
                  <CardDescription>Rule-based or AI-generated improvement guidance.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-green-600" />
                      <p className="font-medium">Strengths</p>
                    </div>
                    {architectureAnalysis?.strengths?.length ? (
                      architectureAnalysis.strengths.map((strength) => (
                        <div key={strength} className="rounded-lg border p-4 text-sm">
                          {strength}
                        </div>
                      ))
                    ) : (
                      <EmptyState
                        title="No strengths listed yet"
                        description="Strengths will appear after architecture analysis completes."
                      />
                    )}
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-600" />
                      <p className="font-medium">Recommendations</p>
                    </div>
                    {architectureAnalysis?.recommendations?.length ? (
                      architectureAnalysis.recommendations.map((recommendation) => (
                        <div key={recommendation} className="rounded-lg border p-4 text-sm">
                          {recommendation}
                        </div>
                      ))
                    ) : (
                      <EmptyState
                        title="No recommendations listed yet"
                        description="Recommendations will appear after architecture analysis completes."
                      />
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="security-hotspots" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Security hotspots</CardTitle>
                <CardDescription>
                  High-risk findings are filtered from the most recent live review output.
                </CardDescription>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Last refreshed from review data at {formatDate(lastReviewTimestamp)}.
              </CardContent>
            </Card>
            {securityHotspots.length > 0 ? (
              <IssueList issues={securityHotspots} />
            ) : (
              <RelatedFindingsFallback
                title="Security review context"
                description="No explicit security hotspots were detected in stored review findings yet."
                pullRequests={pullRequests}
                recentReviews={recentReviews}
              />
            )}
          </TabsContent>

          <TabsContent value="intended-architecture" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Intended architecture</CardTitle>
                <CardDescription>
                  The target system shape inferred from the current architecture service.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Overall status</p>
                    <p className="mt-2 text-2xl font-bold">
                      {toSentenceCase(architectureOverview?.health_summary?.overall || 'unknown')}
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Components</p>
                    <p className="mt-2 text-2xl font-bold">
                      {architectureOverview?.health_summary?.total_components ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Healthy components</p>
                    <p className="mt-2 text-2xl font-bold">
                      {architectureOverview?.health_summary?.healthy_components ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Critical components</p>
                    <p className="mt-2 text-2xl font-bold">
                      {architectureOverview?.health_summary?.critical_components ?? 0}
                    </p>
                  </div>
                </div>

                {architectureOverview?.groups?.length ? (
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {architectureOverview.groups.map((group) => (
                      <div key={group.id} className="rounded-lg border p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-medium">{group.label}</p>
                          <span
                            className="h-3 w-3 rounded-full border"
                            style={{ backgroundColor: group.color, borderColor: group.borderColor }}
                          />
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">
                          Logical architecture zone used in the live overview graph.
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="No target architecture groups yet"
                    description="Architecture grouping will appear once the overview endpoint returns data."
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="pull-requests" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Pull requests</CardTitle>
                <CardDescription>
                  Start or re-run review directly here and watch the latest results stream back.
                </CardDescription>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Pull request data, review state, and risk scores refresh automatically from GitHub and the review pipeline.
              </CardContent>
            </Card>
            <PullRequestList
              pullRequests={pullRequests}
              analyzingPRId={analyzingPRId}
              onAnalyze={handleAnalyze}
            />
          </TabsContent>

          <TabsContent value="branches" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Branch architecture</CardTitle>
                <CardDescription>
                  Compare branch-level architecture based on the latest analyzed pull request for each branch.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {branches.length > 0 ? (
                  <>
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                      <div className="w-full max-w-sm">
                        <Select value={selectedBranchId} onValueChange={setSelectedBranchId}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select a branch" />
                          </SelectTrigger>
                          <SelectContent>
                            {branches.map((branch) => (
                              <SelectItem key={branch.id} value={branch.id}>
                                {branch.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      {selectedBranch && (
                        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                          <Badge variant={statusVariant(selectedBranch.health_status)}>
                            {toSentenceCase(selectedBranch.health_status)}
                          </Badge>
                          <Badge variant="outline" className="gap-1">
                            <GitBranch className="h-3 w-3" />
                            {selectedBranch.name}
                          </Badge>
                          <span>Updated {formatDate(selectedBranch.last_commit_date)}</span>
                        </div>
                      )}
                    </div>

                    {branchArchitectureQuery.isLoading ? (
                      <Skeleton className="h-[600px] w-full" />
                    ) : branchArchitecture?.nodes?.length ? (
                      <ArchitectureGraph
                        nodes={branchArchitecture.nodes}
                        edges={branchArchitecture.edges}
                      />
                    ) : (
                      <EmptyState
                        title="No branch architecture graph yet"
                        description="Start or re-run pull request reviews to generate branch-level architecture data."
                      />
                    )}

                    {branchArchitecture?.statistics && (
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <div className="rounded-lg border p-4">
                          <p className="text-sm text-muted-foreground">Components</p>
                          <p className="mt-2 text-2xl font-bold">
                            {branchArchitecture.statistics.total_components}
                          </p>
                        </div>
                        <div className="rounded-lg border p-4">
                          <p className="text-sm text-muted-foreground">Dependencies</p>
                          <p className="mt-2 text-2xl font-bold">
                            {branchArchitecture.statistics.total_dependencies}
                          </p>
                        </div>
                        <div className="rounded-lg border p-4">
                          <p className="text-sm text-muted-foreground">Circular dependencies</p>
                          <p className="mt-2 text-2xl font-bold">
                            {branchArchitecture.statistics.circular_dependencies}
                          </p>
                        </div>
                        <div className="rounded-lg border p-4">
                          <p className="text-sm text-muted-foreground">Architecture findings</p>
                          <p className="mt-2 text-2xl font-bold">
                            {branchArchitecture.statistics.violations_count}
                          </p>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <EmptyState
                    title="No branch data available"
                    description="Run a GitHub sync to populate branch-level architecture information."
                  />
                )}
              </CardContent>
            </Card>

            {branches.length > 0 && (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {branches.map((branch) => (
                  <Card key={branch.id}>
                    <CardContent className="space-y-3 p-5">
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <p className="font-semibold">{branch.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {branch.last_commit || 'No recent commit message'}
                          </p>
                        </div>
                        <Badge variant={statusVariant(branch.health_status)}>
                          {toSentenceCase(branch.health_status)}
                        </Badge>
                      </div>
                      <div className="space-y-2 text-sm text-muted-foreground">
                        <p>
                          Last commit date:{' '}
                          <span className="font-medium text-foreground">
                            {formatDate(branch.last_commit_date)}
                          </span>
                        </p>
                        <p>
                          Components:{' '}
                          <span className="font-medium text-foreground">{branch.components_count}</span>
                        </p>
                        <p>
                          Complexity:{' '}
                          <span className="font-medium text-foreground">{branch.complexity}</span>
                        </p>
                        <p>
                          Circular dependencies:{' '}
                          <span className="font-medium text-foreground">
                            {branch.circular_dependencies}
                          </span>
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  )
}
