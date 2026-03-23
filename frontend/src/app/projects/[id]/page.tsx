'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { MainLayout } from '@/components/layout/main-layout'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
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
import { useToast } from '@/hooks/use-toast'
import {
  GitBranch,
  Settings,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  GitPullRequest,
  Activity,
  ArrowLeft,
  User,
  Trash2
} from 'lucide-react'
import { useProject, useProjectPullRequests, useDeleteProject, useProjectAnalytics, useProjectArchitectureAnalysis } from '@/hooks/useProjects'
import { useApiCall } from '@/hooks/useApiCall'
import HealthMetrics from '@/components/projects/HealthMetrics'

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params?.id as string || ''
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const { execute } = useApiCall()
  
  const { data: project, isLoading } = useProject(projectId)
  const { data: pullRequestsData = [] } = useProjectPullRequests(projectId)
  const { data: analytics, isLoading: analyticsLoading } = useProjectAnalytics(projectId)
  const { data: architectureAnalysis, isLoading: architectureLoading } = useProjectArchitectureAnalysis(projectId)
  const pullRequests = Array.isArray(pullRequestsData) ? pullRequestsData : []
  const deleteProject = useDeleteProject()

  const handleDeleteProject = async () => {
    await execute(
      () => deleteProject.mutateAsync(projectId),
      {
        successMessage: 'Project deleted successfully',
        errorMessage: 'Failed to delete project',
        onSuccess: () => router.push('/projects')
      }
    )
  }

  // useReal AI reviewData，showLoadingIfNone
  const healthMetrics = analytics?.metrics || null

  const overallHealth = analytics?.metrics?.overall_health || null

  // get详细的analyzedata
  const dependencyStats = analytics?.dependency_stats || { total: 0, circular: 0, outdated: 0, dependency_issues: 0 }
  const performanceMetrics = analytics?.performance_metrics || { avg_build_time: "0m", avg_test_time: "0m", avg_analysis_time: "0m", pr_review_time_avg: "0h" }
  const issueStats = analytics?.issue_stats || { critical: 0, high: 0, medium: 0, low: 0, security: 0, performance: 0, code_style: 0, best_practices: 0, total: 0 }
  const trends = analytics?.trends || { code_quality_change: 0, test_coverage_change: 0, issues_change: 0 }
  const recentAnalysisReviews = analytics?.recent_reviews || []

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
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
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
          description={project.description || 'No description'}
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
              <Button 
                variant="destructive" 
                onClick={() => setShowDeleteDialog(true)}
                disabled={deleteProject.isPending}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Project
              </Button>
            </div>
          }
        />

        {/* Delete Confirmation Dialog */}
        <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete the project
                <span className="font-semibold"> &quot;{project.name}&quot; </span>
                and all associated data including pull requests, reviews, and analysis results.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={deleteProject.isPending}>
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteProject}
                disabled={deleteProject.isPending}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleteProject.isPending ? 'Deleting...' : 'Delete Project'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Project Overview Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Overall Health</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {overallHealth !== null ? (
                <>
                  <div className={`text-2xl font-bold ${getHealthScoreColor(overallHealth)}`}>
                    {overallHealth}%
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Based on 4 metrics
                  </p>
                </>
              ) : (
                <div className="text-center py-4">
                  <Activity className="h-6 w-6 text-muted-foreground mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground">
                    Calculating...
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pull Requests</CardTitle>
              <GitPullRequest className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{pullRequests.length}</div>
              <p className="text-xs text-muted-foreground">
                Total analyzed
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Language</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{project.language || 'N/A'}</div>
              <p className="text-xs text-muted-foreground">
                Primary language
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Owner</CardTitle>
              <User className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-sm font-medium truncate">{project.owner_id}</div>
              <p className="text-xs text-muted-foreground">
                Project owner
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
            {/* Health Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Architectural Health Metrics</CardTitle>
                <CardDescription>Real-time analysis of code quality, security, and architecture</CardDescription>
              </CardHeader>
              <CardContent>
                {healthMetrics ? (
                  <HealthMetrics {...healthMetrics} />
                ) : (
                  <div className="flex items-center justify-center py-8">
                    <div className="text-center">
                      <Activity className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">
                        Analyzing project data...
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

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
                      <p className="text-sm truncate">{project.github_repo_url || 'No repository'}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Status</p>
                    <Badge className="mt-1" variant="success">
                      Active
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Created</p>
                    <div className="flex items-center mt-1">
                      <Clock className="mr-2 h-4 w-4" />
                      <p className="text-sm">{new Date(project.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Last Updated</p>
                    <div className="flex items-center mt-1">
                      <Clock className="mr-2 h-4 w-4" />
                      <p className="text-sm">{new Date(project.updated_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Recent Analysis Results</CardTitle>
                  <CardDescription>Latest code review and analysis findings</CardDescription>
                </CardHeader>
                <CardContent>
                  {recentAnalysisReviews.length > 0 ? (
                    <div className="space-y-4">
                      {recentAnalysisReviews.slice(0, 3).map((review: any) => (
                        <div key={review.pr_id} className="flex items-start space-x-4">
                          <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                            <GitPullRequest className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1 space-y-1">
                            <p className="text-sm font-medium">
                              PR #{review.pr_number}: {review.title}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {review.status} • {review.analyzed_at ? new Date(review.analyzed_at).toLocaleDateString() : 'Not analyzed yet'}
                            </p>
                          </div>
                          {review.risk_score && (
                            <Badge variant={review.risk_score > 70 ? 'destructive' : review.risk_score > 40 ? 'warning' : 'success'}>
                              Risk: {review.risk_score}
                            </Badge>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No analysis results yet</p>
                  )}
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
                  {pullRequests.length > 0 ? (
                    pullRequests.slice(0, 5).map((pr: any) => (
                      <div key={pr.id} className="flex items-start space-x-4">
                        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <CheckCircle className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1 space-y-1">
                          <p className="text-sm font-medium">
                            PR #{pr.github_pr_number}: {pr.title}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {pr.files_changed} files • +{pr.lines_added} -{pr.lines_deleted} • {new Date(pr.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <Badge variant="success">{pr.status}</Badge>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No recent activity</p>
                  )}
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
                {pullRequests.length > 0 ? (
                  <div className="space-y-4">
                    {pullRequests.map((pr: any) => (
                      <Card key={pr.id} className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <GitPullRequest className="h-5 w-5 text-primary" />
                              <h4 className="font-semibold">PR #{pr.github_pr_number}: {pr.title}</h4>
                              <Badge variant={
                                pr.status === 'merged' ? 'success' : 
                                pr.status === 'closed' ? 'destructive' : 
                                'default'
                              }>
                                {pr.status}
                              </Badge>
                            </div>
                            
                            {pr.description && (
                              <p className="text-sm text-muted-foreground mb-3">
                                {pr.description}
                              </p>
                            )}
                            
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                              <div>
                                <p className="text-muted-foreground">Files Changed</p>
                                <p className="font-medium">{pr.files_changed || 0}</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground">Lines Added</p>
                                <p className="font-medium text-green-600">+{pr.lines_added || 0}</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground">Lines Deleted</p>
                                <p className="font-medium text-red-600">-{pr.lines_deleted || 0}</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground">Risk Score</p>
                                <p className={`font-medium ${
                                  pr.risk_score > 70 ? 'text-red-600' : 
                                  pr.risk_score > 40 ? 'text-yellow-600' : 
                                  'text-green-600'
                                }`}>
                                  {pr.risk_score || 'N/A'}
                                </p>
                              </div>
                            </div>
                            
                            <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                              <span>Branch: {pr.branch_name}</span>
                              <span>Created: {new Date(pr.created_at).toLocaleDateString()}</span>
                              {pr.analyzed_at && (
                                <span>Analyzed: {new Date(pr.analyzed_at).toLocaleDateString()}</span>
                              )}
                            </div>
                          </div>
                          
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => router.push(`/projects/${projectId}/pulls/${pr.id}`)}
                          >
                            View Details
                          </Button>
                        </div>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <GitPullRequest className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No Pull Requests</h3>
                    <p className="text-sm text-muted-foreground">
                      Pull requests will appear here once they are created and analyzed
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="architecture">
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Architecture Analysis</CardTitle>
                  <CardDescription>Dependency graph and architectural insights</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {/* Architecture Health Score */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <Card className="p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm text-muted-foreground">Architecture Health</p>
                            <p className="text-2xl font-bold text-green-600">{healthMetrics ? healthMetrics.architecture_health : 'N/A'}%</p>
                          </div>
                          <CheckCircle className="h-8 w-8 text-green-600" />
                        </div>
                      </Card>
                      
                      <Card className="p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm text-muted-foreground">Code Quality</p>
                            <p className="text-2xl font-bold text-blue-600">{healthMetrics ? healthMetrics.code_quality : 'N/A'}%</p>
                          </div>
                          <Activity className="h-8 w-8 text-blue-600" />
                        </div>
                      </Card>
                      
                      <Card className="p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm text-muted-foreground">Test Coverage</p>
                            <p className="text-2xl font-bold text-purple-600">{healthMetrics ? healthMetrics.test_coverage : 'N/A'}%</p>
                          </div>
                          <TrendingUp className="h-8 w-8 text-purple-600" />
                        </div>
                      </Card>
                    </div>
                    
                    {/* Architecture Insights */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Card className="p-4">
                        <h4 className="font-semibold mb-3 flex items-center gap-2">
                          <CheckCircle className="h-5 w-5 text-green-600" />
                          Strengths
                        </h4>
                        {architectureAnalysis?.strengths ? (
                          <ul className="space-y-2 text-sm">
                            {architectureAnalysis.strengths.map((strength: string, index: number) => (
                              <li key={index} className="flex items-start gap-2">
                                <span className="text-green-600">✓</span>
                                <span>{strength}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="flex items-center justify-center py-4">
                            <Activity className="h-6 w-6 text-muted-foreground mx-auto mr-2" />
                            <p className="text-sm text-muted-foreground">Analyzing strengths...</p>
                          </div>
                        )}
                      </Card>
                      
                      <Card className="p-4">
                        <h4 className="font-semibold mb-3 flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5 text-yellow-600" />
                          Recommendations
                        </h4>
                        {architectureAnalysis?.recommendations ? (
                          <ul className="space-y-2 text-sm">
                            {architectureAnalysis.recommendations.map((recommendation: string, index: number) => (
                              <li key={index} className="flex items-start gap-2">
                                <span className="text-yellow-600">⚠</span>
                                <span>{recommendation}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="flex items-center justify-center py-4">
                            <Activity className="h-6 w-6 text-muted-foreground mx-auto mr-2" />
                            <p className="text-sm text-muted-foreground">Generating recommendations...</p>
                          </div>
                        )}
                      </Card>
                    </div>
                    
                    {/* Dependency Information */}
                    <Card className="p-4">
                      <h4 className="font-semibold mb-3">Dependency Analysis</h4>
                      {analytics?.dependency_stats ? (
                        <div className="space-y-3">
                          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                            <div>
                              <p className="font-medium">Total Dependencies</p>
                              <p className="text-sm text-muted-foreground">External packages and modules</p>
                            </div>
                            <Badge variant="outline" className="text-lg">
                              {analytics.dependency_stats.total || 0}
                            </Badge>
                          </div>
                          
                          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                            <div>
                              <p className="font-medium">Circular Dependencies</p>
                              <p className="text-sm text-muted-foreground">Modules with circular references</p>
                            </div>
                            <Badge variant={analytics.dependency_stats.circular > 0 ? 'destructive' : 'outline'}>
                              {analytics.dependency_stats.circular || 0}
                            </Badge>
                          </div>
                          
                          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                            <div>
                              <p className="font-medium">Outdated Dependencies</p>
                              <p className="text-sm text-muted-foreground">Packages that need updates</p>
                            </div>
                            <Badge variant={analytics.dependency_stats.outdated > 0 ? 'warning' : 'outline'}>
                              {analytics.dependency_stats.outdated || 0}
                            </Badge>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground text-center py-4">
                          No dependency analysis data available yet
                        </p>
                      )}
                    </Card>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="metrics">
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Detailed Metrics</CardTitle>
                  <CardDescription>Comprehensive quality and performance metrics</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {/* Code Quality Metrics */}
                    <div>
                      <h4 className="font-semibold mb-4">Code Quality Metrics</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <Card className="p-4">
                          <p className="text-sm text-muted-foreground mb-1">Maintainability Index</p>
                          <p className="text-2xl font-bold text-green-600">
                            {healthMetrics ? healthMetrics.code_quality : 'N/A'}
                          </p>
                          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-green-600 h-2 rounded-full" 
                              style={{ width: healthMetrics ? `${healthMetrics.code_quality}%` : '0%' }}
                            />
                          </div>
                        </Card>
                        
                        <Card className="p-4">
                          <p className="text-sm text-muted-foreground mb-1">Code Complexity</p>
                          <p className="text-2xl font-bold text-blue-600">
                            {healthMetrics ? (100 - healthMetrics.code_quality) : 'N/A'}%
                          </p>
                          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full" 
                              style={{ width: healthMetrics ? `${100 - healthMetrics.code_quality}%` : '0%' }}
                            />
                          </div>
                        </Card>
                        
                        <Card className="p-4">
                          <p className="text-sm text-muted-foreground mb-1">Test Coverage</p>
                          <p className="text-2xl font-bold text-purple-600">
                            {healthMetrics ? healthMetrics.test_coverage : 'N/A'}%
                          </p>
                          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-purple-600 h-2 rounded-full" 
                              style={{ width: healthMetrics ? `${healthMetrics.test_coverage}%` : '0%' }}
                            />
                          </div>
                        </Card>
                        
                        <Card className="p-4">
                          <p className="text-sm text-muted-foreground mb-1">Security Rating</p>
                          <p className="text-2xl font-bold text-green-600">
                            {healthMetrics ? healthMetrics.security_rating : 'N/A'}%
                          </p>
                          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-green-600 h-2 rounded-full" 
                              style={{ width: healthMetrics ? `${healthMetrics.security_rating}%` : '0%' }}
                            />
                          </div>
                        </Card>
                      </div>
                    </div>
                    
                    {/* Performance Metrics */}
                    {analytics?.performance_metrics && (
                      <div>
                        <h4 className="font-semibold mb-4">Performance Metrics</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <Card className="p-4">
                            <div className="flex items-center justify-between mb-2">
                              <p className="text-sm text-muted-foreground">Build Time</p>
                              <Clock className="h-4 w-4 text-muted-foreground" />
                            </div>
                            <p className="text-2xl font-bold">
                              {analytics.performance_metrics.avg_build_time || 'N/A'}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">Average build duration</p>
                          </Card>
                          
                          <Card className="p-4">
                            <div className="flex items-center justify-between mb-2">
                              <p className="text-sm text-muted-foreground">Test Execution</p>
                              <Activity className="h-4 w-4 text-muted-foreground" />
                            </div>
                            <p className="text-2xl font-bold">
                              {analytics.performance_metrics.avg_test_time || 'N/A'}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">Average test duration</p>
                          </Card>
                          
                          <Card className="p-4">
                            <div className="flex items-center justify-between mb-2">
                              <p className="text-sm text-muted-foreground">Code Analysis</p>
                              <TrendingUp className="h-4 w-4 text-muted-foreground" />
                            </div>
                            <p className="text-2xl font-bold">
                              {analytics.performance_metrics.avg_analysis_time || 'N/A'}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">Average analysis time</p>
                          </Card>
                        </div>
                      </div>
                    )}
                    
                    {/* Issue Statistics */}
                    {analytics?.issue_stats && (
                      <div>
                        <h4 className="font-semibold mb-4">Issue Statistics</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <Card className="p-4">
                            <h5 className="font-medium mb-3">Issues by Severity</h5>
                            <div className="space-y-3">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <div className="w-3 h-3 rounded-full bg-red-600" />
                                  <span className="text-sm">Critical</span>
                                </div>
                                <Badge variant="destructive">
                                  {analytics.issue_stats.critical || 0}
                                </Badge>
                              </div>
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <div className="w-3 h-3 rounded-full bg-orange-600" />
                                  <span className="text-sm">High</span>
                                </div>
                                <Badge variant="warning">
                                  {analytics.issue_stats.high || 0}
                                </Badge>
                              </div>
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <div className="w-3 h-3 rounded-full bg-yellow-600" />
                                  <span className="text-sm">Medium</span>
                                </div>
                                <Badge variant="outline">
                                  {analytics.issue_stats.medium || 0}
                                </Badge>
                              </div>
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <div className="w-3 h-3 rounded-full bg-blue-600" />
                                  <span className="text-sm">Low</span>
                                </div>
                                <Badge variant="outline">
                                  {analytics.issue_stats.low || 0}
                                </Badge>
                              </div>
                            </div>
                          </Card>
                          
                          <Card className="p-4">
                            <h5 className="font-medium mb-3">Issues by Type</h5>
                            <div className="space-y-3">
                              <div className="flex items-center justify-between">
                                <span className="text-sm">Security</span>
                                <Badge variant="destructive">
                                  {analytics.issue_stats.security || 0}
                                </Badge>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-sm">Performance</span>
                                <Badge variant="warning">
                                  {analytics.issue_stats.performance || 0}
                                </Badge>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-sm">Code Style</span>
                                <Badge variant="outline">
                                  {analytics.issue_stats.code_style || 0}
                                </Badge>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-sm">Best Practices</span>
                                <Badge variant="outline">
                                  {analytics.issue_stats.best_practices || 0}
                                </Badge>
                              </div>
                            </div>
                          </Card>
                        </div>
                      </div>
                    )}
                    
                    {/* Trend Information */}
                    {analytics?.trends && (
                      <Card className="p-4">
                        <h5 className="font-medium mb-3">Trend Analysis</h5>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="text-center p-4 bg-green-50 rounded-lg">
                            <TrendingUp className="h-8 w-8 text-green-600 mx-auto mb-2" />
                            <p className="text-2xl font-bold text-green-600">
                              {analytics.trends.code_quality_change > 0 ? '+' : ''}{analytics.trends.code_quality_change}%
                            </p>
                            <p className="text-sm text-muted-foreground">Code Quality</p>
                            <p className="text-xs text-muted-foreground mt-1">vs last month</p>
                          </div>
                          <div className="text-center p-4 bg-blue-50 rounded-lg">
                            <TrendingUp className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                            <p className="text-2xl font-bold text-blue-600">
                              {analytics.trends.test_coverage_change > 0 ? '+' : ''}{analytics.trends.test_coverage_change}%
                            </p>
                            <p className="text-sm text-muted-foreground">Test Coverage</p>
                            <p className="text-xs text-muted-foreground mt-1">vs last month</p>
                          </div>
                          <div className="text-center p-4 bg-purple-50 rounded-lg">
                            <TrendingUp className="h-8 w-8 text-purple-600 mx-auto mb-2" />
                            <p className="text-2xl font-bold text-purple-600">
                              {analytics.trends.issues_change > 0 ? '+' : ''}{analytics.trends.issues_change}%
                            </p>
                            <p className="text-sm text-muted-foreground">Issues Found</p>
                            <p className="text-xs text-muted-foreground mt-1">vs last month</p>
                          </div>
                        </div>
                      </Card>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  )
}
