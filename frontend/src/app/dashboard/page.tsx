'use client'

import { useEffect, useState, useMemo } from 'react'
import { RouteGuard } from '@/components/auth/RouteGuard'
import { MainLayout } from '@/components/layout/main-layout'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  FolderGit2,
  GitPullRequest,
  AlertTriangle,
  TrendingUp,
  Eye,
  Network,
  RefreshCw,
  AlertCircle
} from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import dynamic from 'next/dynamic'

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
  const response = await fetch('/api/dashboard/stats', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    // Add cache control for better performance
    next: { revalidate: 300 } // Cache for 5 minutes
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard stats: ${response.status}`)
  }

  return response.json()
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
  const queryClient = useQueryClient()

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
                <Card className="hover:shadow-md transition-shadow">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      Total Projects
                    </CardTitle>
                    <FolderGit2 className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stats.totalProjects}</div>
                    <div className="flex items-center text-xs text-muted-foreground">
                      <TrendingUp className="h-3 w-3 mr-1" />
                      <span className={trends?.projects && trends.projects > 0 ? 'text-green-600' : 'text-muted-foreground'}>
                        {trends?.projects ? `${trends.projects > 0 ? '+' : ''}${trends.projects}` : '0'} from last month
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-shadow">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      Pending Reviews
                    </CardTitle>
                    <GitPullRequest className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stats.pendingReviews}</div>
                    <div className="flex items-center text-xs text-muted-foreground">
                      <Eye className="h-3 w-3 mr-1" />
                      <span>Requires attention</span>
                    </div>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-shadow">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      Critical Issues
                    </CardTitle>
                    <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-destructive">
                      {stats.criticalIssues}
                    </div>
                    <div className="flex items-center text-xs text-muted-foreground">
                      <AlertTriangle className="h-3 w-3 mr-1" />
                      <span>Needs immediate action</span>
                    </div>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-shadow">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      Architecture Health
                    </CardTitle>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className={`text-2xl font-bold ${getHealthScoreColor(stats.architectureHealthScore)}`}>
                      {stats.architectureHealthScore}%
                    </div>
                    <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getHealthScoreBg(stats.architectureHealthScore)}`}>
                      <span className={getHealthScoreColor(stats.architectureHealthScore)}>
                        {stats.architectureHealthScore >= 80 ? 'Excellent' :
                         stats.architectureHealthScore >= 60 ? 'Good' : 'Needs Attention'}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : null}
          </div>

          {/* Recent Activity and Quick Actions - Lazy Loaded */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
            <RecentActivity isLoading={isLoading} />
            <QuickActions />
          </div>

          {/* Performance Metrics */}
          {stats && (
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">Security Score</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">{stats.securityScore || 95}%</div>
                  <p className="text-xs text-muted-foreground">Compliance rating</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">Review Efficiency</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-600">{stats.reviewEfficiency || 87}%</div>
                  <p className="text-xs text-muted-foreground">Time to completion</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">Last Updated</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-sm font-medium">
                    {stats.lastUpdated ? new Date(stats.lastUpdated).toLocaleString() : 'Just now'}
                  </div>
                  <p className="text-xs text-muted-foreground">Data freshness</p>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </MainLayout>
    </RouteGuard>
  )
}
