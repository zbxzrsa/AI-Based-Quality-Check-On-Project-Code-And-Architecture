'use client'

import { useMemo } from 'react'
import { RouteGuard } from '@/components/auth/RouteGuard'
import { MainLayout } from '@/components/layout/main-layout'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  CalendarClock,
  FolderGit2,
  GitPullRequest,
  AlertTriangle,
  TrendingUp,
  Eye,
  RefreshCw,
  AlertCircle,
  ShieldCheck
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import dynamic from 'next/dynamic'
import { apiGet } from '@/lib/api-client'

// Lazy load components for better performance
const RecentActivity = dynamic(() => import('@/components/dashboard/RecentActivity').then(mod => mod.RecentActivity), {
  loading: () => <Skeleton className="h-[400px] w-full" />,
  ssr: false
})

const QuickActions = dynamic(() => import('@/components/dashboard/QuickActions').then(mod => mod.QuickActions), {
  loading: () => <Skeleton className="h-[300px] w-full" />,
  ssr: false
})

// API service functions
const fetchDashboardStats = async (): Promise<DashboardMetrics> => {
  return apiGet<DashboardMetrics>('/api/dashboard/stats', {
    next: { revalidate: 300 },
  })
}

interface DashboardStats {
  totalProjects: number
  pendingReviews: number
  criticalIssues: number
  architectureHealthScore: number
  projectGrowth: number
  reviewEfficiency: number
  securityScore: number
  lastUpdated: string
}

interface DashboardMetrics {
  stats: DashboardStats
  trends: {
    projects: number
    reviews: number
    issues: number
    health: number
  }
  alerts: Array<{
    id: string
    type: 'warning' | 'error' | 'info'
    message: string
    actionUrl?: string
  }>
}

export default function DashboardPage() {
  // Use React Query for data fetching with caching and error handling
  const {
    data: dashboardData,
    isLoading,
    error,
    refetch,
    isRefetching
  } = useQuery<DashboardMetrics>({
    queryKey: ['dashboard'],
    queryFn: fetchDashboardStats,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
  })

  // Memoize computed values for performance
  const stats = useMemo(() => dashboardData?.stats, [dashboardData])
  const trends = useMemo(() => dashboardData?.trends, [dashboardData])
  const alerts = useMemo(() => dashboardData?.alerts || [], [dashboardData])

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400'
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getHealthScoreBg = (score: number) => {
    if (score >= 80) return 'bg-green-100 dark:bg-green-900/20'
    if (score >= 60) return 'bg-yellow-100 dark:bg-yellow-900/20'
    return 'bg-red-100 dark:bg-red-900/20'
  }

  // Handle manual refresh
  const handleRefresh = () => {
    refetch()
  }

  const overviewCards = stats ? [
    {
      title: 'Total Projects',
      value: stats.totalProjects,
      detail: `${trends?.projects ? `${trends.projects > 0 ? '+' : ''}${trends.projects}` : '0'} from last month`,
      icon: FolderGit2,
      valueClassName: 'text-foreground',
      accentClassName: 'bg-blue-500',
    },
    {
      title: 'Pending Reviews',
      value: stats.pendingReviews,
      detail: 'Requires attention',
      icon: GitPullRequest,
      valueClassName: 'text-foreground',
      accentClassName: 'bg-amber-500',
    },
    {
      title: 'Critical Issues',
      value: stats.criticalIssues,
      detail: 'Needs immediate action',
      icon: AlertTriangle,
      valueClassName: 'text-destructive',
      accentClassName: 'bg-red-500',
    },
    {
      title: 'Architecture Health',
      value: `${stats.architectureHealthScore}%`,
      detail:
        stats.architectureHealthScore >= 80
          ? 'Excellent'
          : stats.architectureHealthScore >= 60
            ? 'Good'
            : 'Needs attention',
      icon: TrendingUp,
      valueClassName: getHealthScoreColor(stats.architectureHealthScore),
      accentClassName: 'bg-emerald-500',
      badgeClassName: getHealthScoreBg(stats.architectureHealthScore),
    },
  ] : []

  return (
    <RouteGuard>
      <MainLayout>
        <div className="space-y-6">
          <PageHeader
            title="Dashboard"
            description="Welcome back! Here's an overview of your projects and reviews."
            actions={
              <Button
                onClick={handleRefresh}
                disabled={isRefetching}
                variant="outline"
                size="sm"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isRefetching ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            }
          />

          {stats && (
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-lg border bg-card px-4 py-3">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-4 w-4 text-green-600" />
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                      Security score
                    </p>
                    <p className="text-sm font-semibold">{stats.securityScore || 95}% compliance rating</p>
                  </div>
                </div>
              </div>
              <div className="rounded-lg border bg-card px-4 py-3">
                <div className="flex items-center gap-3">
                  <TrendingUp className="h-4 w-4 text-blue-600" />
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                      Review efficiency
                    </p>
                    <p className="text-sm font-semibold">{stats.reviewEfficiency || 87}% completion speed</p>
                  </div>
                </div>
              </div>
              <div className="rounded-lg border bg-card px-4 py-3">
                <div className="flex items-center gap-3">
                  <CalendarClock className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                      Last updated
                    </p>
                    <p className="text-sm font-semibold">
                      {stats.lastUpdated ? new Date(stats.lastUpdated).toLocaleString() : 'Just now'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load dashboard data. Please try again.
                <Button
                  variant="link"
                  className="p-0 h-auto ml-2 text-destructive underline"
                  onClick={handleRefresh}
                >
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {/* Critical Alerts */}
          {alerts.length > 0 && (
            <div className="space-y-2">
              {alerts.slice(0, 3).map((alert) => (
                <Alert key={alert.id} variant={alert.type === 'error' ? 'destructive' : 'default'}>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {alert.message}
                    {alert.actionUrl && (
                      <Button variant="link" className="p-0 h-auto ml-2 underline">
                        Take Action
                      </Button>
                    )}
                  </AlertDescription>
                </Alert>
              ))}
            </div>
          )}

          {/* Overview Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {isLoading ? (
              <>
                {[...Array(4)].map((_, i) => (
                  <Card key={i}>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-4 w-4" />
                    </CardHeader>
                    <CardContent>
                      <Skeleton className="h-8 w-16 mb-2" />
                      <Skeleton className="h-3 w-32" />
                    </CardContent>
                  </Card>
                ))}
              </>
            ) : stats ? (
              <>
                {overviewCards.map((item) => (
                  <Card key={item.title} className="overflow-hidden">
                    <div className={`h-1 w-full ${item.accentClassName}`} />
                    <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
                      <div className="space-y-1">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                          {item.title}
                        </CardTitle>
                        <div className={`text-3xl font-semibold ${item.valueClassName}`}>
                          {item.value}
                        </div>
                      </div>
                      <item.icon className="mt-1 h-5 w-5 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                      {item.badgeClassName ? (
                        <div className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${item.badgeClassName}`}>
                          <span className={item.valueClassName}>{item.detail}</span>
                        </div>
                      ) : (
                        <div className="flex items-center text-xs text-muted-foreground">
                          <Eye className="mr-1 h-3 w-3" />
                          <span>{item.detail}</span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </>
            ) : null}
          </div>

          {/* Recent Activity and Quick Actions - Lazy Loaded */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
            <RecentActivity isLoading={isLoading} />
            <QuickActions />
          </div>

        </div>
      </MainLayout>
    </RouteGuard>
  )
}
