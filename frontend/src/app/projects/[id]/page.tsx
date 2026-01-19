'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { MainLayout } from '@/components/layout/main-layout'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import {
  GitBranch,
  Settings,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  GitPullRequest,
  Activity,
  ArrowLeft
} from 'lucide-react'

interface ProjectDetail {
  id: string
  name: string
  description: string
  repository: string
  status: 'active' | 'inactive' | 'archived'
  healthScore: number
  lastAnalysis: string
  pendingReviews: number
  criticalIssues: number
  totalReviews: number
  averageReviewTime: string
  codeQualityScore: number
  securityScore: number
  maintainabilityScore: number
}

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setProject({
        id: params.id as string,
        name: 'User Authentication Service',
        description: 'Microservice handling user authentication and authorization',
        repository: 'github.com/company/user-auth-service',
        status: 'active',
        healthScore: 92,
        lastAnalysis: '2 hours ago',
        pendingReviews: 2,
        criticalIssues: 0,
        totalReviews: 45,
        averageReviewTime: '2.5 hours',
        codeQualityScore: 88,
        securityScore: 95,
        maintainabilityScore: 90,
      })
      setIsLoading(false)
    }, 1000)
  }, [params.id])

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  if (isLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <Skeleton className="h-12 w-3/4" />
          <Skeleton className="h-64 w-full" />
        </div>
      </MainLayout>
    )
  }

  if (!project) {
    return (
      <MainLayout>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertTriangle className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Project not found</h3>
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
          description={project.description}
          actions={
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => router.push('/projects')}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
              <Button onClick={() => router.push(`/projects/${project.id}/settings`)}>
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </Button>
            </div>
          }
        />

        {/* Project Overview Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Health Score</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${getHealthScoreColor(project.healthScore)}`}>
                {project.healthScore}%
              </div>
              <p className="text-xs text-muted-foreground">
                +5% from last week
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Reviews</CardTitle>
              <GitPullRequest className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{project.pendingReviews}</div>
              <p className="text-xs text-muted-foreground">
                Requires attention
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Critical Issues</CardTitle>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${project.criticalIssues > 0 ? 'text-destructive' : ''}`}>
                {project.criticalIssues}
              </div>
              <p className="text-xs text-muted-foreground">
                {project.criticalIssues === 0 ? 'All clear' : 'Needs attention'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Reviews</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{project.totalReviews}</div>
              <p className="text-xs text-muted-foreground">
                Avg: {project.averageReviewTime}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Tabbed Content */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="reviews">Reviews</TabsTrigger>
            <TabsTrigger value="architecture">Architecture</TabsTrigger>
            <TabsTrigger value="metrics">Metrics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Project Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Repository</p>
                    <div className="flex items-center mt-1">
                      <GitBranch className="mr-2 h-4 w-4" />
                      <p className="text-sm">{project.repository}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Status</p>
                    <Badge className="mt-1" variant={project.status === 'active' ? 'success' : 'secondary'}>
                      {project.status}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Last Analysis</p>
                    <div className="flex items-center mt-1">
                      <Clock className="mr-2 h-4 w-4" />
                      <p className="text-sm">{project.lastAnalysis}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Quality Metrics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium">Code Quality</p>
                      <span className={`text-sm font-bold ${getHealthScoreColor(project.codeQualityScore)}`}>
                        {project.codeQualityScore}%
                      </span>
                    </div>
                    <div className="w-full bg-secondary rounded-full h-2">
                      <div 
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${project.codeQualityScore}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium">Security</p>
                      <span className={`text-sm font-bold ${getHealthScoreColor(project.securityScore)}`}>
                        {project.securityScore}%
                      </span>
                    </div>
                    <div className="w-full bg-secondary rounded-full h-2">
                      <div 
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${project.securityScore}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium">Maintainability</p>
                      <span className={`text-sm font-bold ${getHealthScoreColor(project.maintainabilityScore)}`}>
                        {project.maintainabilityScore}%
                      </span>
                    </div>
                    <div className="w-full bg-secondary rounded-full h-2">
                      <div 
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${project.maintainabilityScore}%` }}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>Latest updates and changes</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-start space-x-4">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <CheckCircle className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium">
                          PR review completed for feature/user-login
                        </p>
                        <p className="text-xs text-muted-foreground">{i} hours ago</p>
                      </div>
                      <Badge variant="success">Passed</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="reviews">
            <Card>
              <CardHeader>
                <CardTitle>Pull Request Reviews</CardTitle>
                <CardDescription>Review history and pending reviews</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Pull request review list will be displayed here
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="architecture">
            <Card>
              <CardHeader>
                <CardTitle>Architecture Analysis</CardTitle>
                <CardDescription>Dependency graph and architectural insights</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Architecture visualization will be displayed here
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="metrics">
            <Card>
              <CardHeader>
                <CardTitle>Detailed Metrics</CardTitle>
                <CardDescription>Comprehensive quality and performance metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Detailed metrics and charts will be displayed here
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  )
}
