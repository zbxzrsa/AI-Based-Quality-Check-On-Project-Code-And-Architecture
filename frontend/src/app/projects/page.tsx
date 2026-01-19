'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { MainLayout } from '@/components/layout/main-layout'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { 
  Plus, 
  Search, 
  Grid3x3, 
  List, 
  GitBranch,
  Clock,
  AlertTriangle,
  CheckCircle,
  Settings
} from 'lucide-react'

interface Project {
  id: string
  name: string
  description: string
  repository: string
  status: 'active' | 'inactive' | 'archived'
  healthScore: number
  lastAnalysis: string
  pendingReviews: number
  criticalIssues: number
}

export default function ProjectsPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('name')
  const [filterStatus, setFilterStatus] = useState('all')

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setProjects([
        {
          id: '1',
          name: 'User Authentication Service',
          description: 'Microservice handling user authentication and authorization',
          repository: 'github.com/company/user-auth-service',
          status: 'active',
          healthScore: 92,
          lastAnalysis: '2 hours ago',
          pendingReviews: 2,
          criticalIssues: 0,
        },
        {
          id: '2',
          name: 'Payment Gateway',
          description: 'Payment processing and transaction management',
          repository: 'github.com/company/payment-gateway',
          status: 'active',
          healthScore: 78,
          lastAnalysis: '5 hours ago',
          pendingReviews: 1,
          criticalIssues: 2,
        },
        {
          id: '3',
          name: 'API Gateway',
          description: 'Central API gateway for microservices',
          repository: 'github.com/company/api-gateway',
          status: 'active',
          healthScore: 85,
          lastAnalysis: '1 day ago',
          pendingReviews: 0,
          criticalIssues: 1,
        },
        {
          id: '4',
          name: 'Order Management',
          description: 'Order processing and fulfillment system',
          repository: 'github.com/company/order-management',
          status: 'active',
          healthScore: 95,
          lastAnalysis: '3 hours ago',
          pendingReviews: 3,
          criticalIssues: 0,
        },
        {
          id: '5',
          name: 'Notification Service',
          description: 'Email and push notification service',
          repository: 'github.com/company/notification-service',
          status: 'inactive',
          healthScore: 65,
          lastAnalysis: '1 week ago',
          pendingReviews: 0,
          criticalIssues: 5,
        },
        {
          id: '6',
          name: 'Analytics Dashboard',
          description: 'Business intelligence and analytics platform',
          repository: 'github.com/company/analytics-dashboard',
          status: 'active',
          healthScore: 88,
          lastAnalysis: '4 hours ago',
          pendingReviews: 1,
          criticalIssues: 0,
        },
      ])
      setIsLoading(false)
    }, 1000)
  }, [])

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getHealthScoreBadge = (score: number) => {
    if (score >= 80) return 'success'
    if (score >= 60) return 'warning'
    return 'destructive'
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'inactive':
        return 'secondary'
      case 'archived':
        return 'outline'
      default:
        return 'default'
    }
  }

  const filteredProjects = projects
    .filter(project => {
      const matchesSearch = project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          project.description.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesStatus = filterStatus === 'all' || project.status === filterStatus
      return matchesSearch && matchesStatus
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name)
        case 'health':
          return b.healthScore - a.healthScore
        case 'recent':
          return 0 // Would sort by date in real implementation
        default:
          return 0
      }
    })

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Projects"
          description="Manage and monitor your code repositories"
          actions={
            <Button onClick={() => router.push('/projects/new')}>
              <Plus className="mr-2 h-4 w-4" />
              Add Project
            </Button>
          }
        />

        {/* Filters and Controls */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search projects..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>

              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-full md:w-[180px]">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>

              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-full md:w-[180px]">
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="name">Name</SelectItem>
                  <SelectItem value="health">Health Score</SelectItem>
                  <SelectItem value="recent">Recently Updated</SelectItem>
                </SelectContent>
              </Select>

              <div className="flex gap-2">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'outline'}
                  size="icon"
                  onClick={() => setViewMode('grid')}
                >
                  <Grid3x3 className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'default' : 'outline'}
                  size="icon"
                  onClick={() => setViewMode('list')}
                >
                  <List className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Projects Grid/List */}
        {isLoading ? (
          <div className={viewMode === 'grid' ? 'grid gap-4 md:grid-cols-2 lg:grid-cols-3' : 'space-y-4'}>
            {[...Array(6)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-6 w-3/4 mb-2" />
                  <Skeleton className="h-4 w-full" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-20 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredProjects.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <GitBranch className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No projects found</h3>
              <p className="text-sm text-muted-foreground mb-4">
                {searchTerm ? 'Try adjusting your search or filters' : 'Get started by adding your first project'}
              </p>
              <Button onClick={() => router.push('/projects/new')}>
                <Plus className="mr-2 h-4 w-4" />
                Add Project
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className={viewMode === 'grid' ? 'grid gap-4 md:grid-cols-2 lg:grid-cols-3' : 'space-y-4'}>
            {filteredProjects.map((project) => (
              <Card 
                key={project.id} 
                className="hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => router.push(`/projects/${project.id}`)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg">{project.name}</CardTitle>
                      <CardDescription className="mt-1">
                        {project.description}
                      </CardDescription>
                    </div>
                    <Badge variant={getStatusBadge(project.status)}>
                      {project.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center text-sm text-muted-foreground">
                    <GitBranch className="mr-2 h-4 w-4" />
                    <span className="truncate">{project.repository}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-muted-foreground">Health:</span>
                      <span className={`text-lg font-bold ${getHealthScoreColor(project.healthScore)}`}>
                        {project.healthScore}%
                      </span>
                    </div>
                    <Badge variant={getHealthScoreBadge(project.healthScore)}>
                      {project.healthScore >= 80 ? (
                        <CheckCircle className="mr-1 h-3 w-3" />
                      ) : (
                        <AlertTriangle className="mr-1 h-3 w-3" />
                      )}
                      {project.healthScore >= 80 ? 'Healthy' : project.healthScore >= 60 ? 'Warning' : 'Critical'}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                    <div>
                      <p className="text-xs text-muted-foreground">Pending Reviews</p>
                      <p className="text-lg font-semibold">{project.pendingReviews}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Critical Issues</p>
                      <p className={`text-lg font-semibold ${project.criticalIssues > 0 ? 'text-destructive' : ''}`}>
                        {project.criticalIssues}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center text-xs text-muted-foreground">
                    <Clock className="mr-1 h-3 w-3" />
                    Last analysis: {project.lastAnalysis}
                  </div>
                </CardContent>
                <CardFooter className="flex justify-between">
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      router.push(`/projects/${project.id}`)
                    }}
                  >
                    View Details
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      router.push(`/projects/${project.id}/settings`)
                    }}
                  >
                    <Settings className="h-4 w-4" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  )
}
