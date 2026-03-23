'use client'

import { useState, useEffect, Suspense, useMemo, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { MainLayout } from '@/components/layout/main-layout'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
  Settings,
  RefreshCw,
  Filter,
  Download,
  Upload
} from 'lucide-react'
import { useProjects } from '@/hooks/useProjects'
import { AddProjectModal } from '@/components/projects/add-project-modal'
import { useToast } from '@/hooks/use-toast'
import { useDebounce } from '@/hooks/useDebounce'

// Skeleton components
function ProjectCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-3/4 mb-2" />
        <Skeleton className="h-4 w-full" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-20 w-full" />
      </CardContent>
    </Card>
  )
}

function ProjectListSkeleton() {
  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <Skeleton className="h-5 w-48 mb-1" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-6 w-16" />
        </div>
      </CardContent>
    </Card>
  )
}

interface Project {
  id: string
  name: string
  description?: string | null
  github_repo_url?: string | null
  language?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

interface ProjectCardProps {
  project: Project
  onClick: () => void
}

// Grid view card component
function ProjectGridCard({ project, onClick }: ProjectCardProps) {
  return (
    <Card
      className="hover:shadow-lg transition-shadow cursor-pointer"
      onClick={onClick}
      role="listitem"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      aria-label={`Project: ${project.name}`}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg">{project.name}</CardTitle>
            <CardDescription className="mt-1">
              {project.description || 'No description'}
            </CardDescription>
          </div>
          <Badge variant={project.is_active ? "success" : "secondary"}>
            {project.is_active ? 'Active' : 'Inactive'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center text-sm text-muted-foreground">
          <GitBranch className="mr-2 h-4 w-4" aria-hidden="true" />
          <span className="truncate">{project.github_repo_url || 'No repository'}</span>
        </div>

        {project.language && (
          <div className="flex items-center space-x-2">
            <Badge variant="outline">{project.language}</Badge>
          </div>
        )}

        <div className="flex items-center text-xs text-muted-foreground pt-2 border-t">
          <Clock className="mr-1 h-3 w-3" aria-hidden="true" />
          <time dateTime={project.updated_at}>
            Updated: {new Date(project.updated_at).toLocaleDateString()}
          </time>
        </div>
      </CardContent>
      <CardFooter className="flex justify-between">
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            onClick()
          }}
          aria-label={`View details for ${project.name}`}
        >
          View Details
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            // Could add settings navigation here
          }}
          aria-label={`Settings for ${project.name}`}
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
        </Button>
      </CardFooter>
    </Card>
  )
}

// List view card component
function ProjectListCard({ project, onClick }: ProjectCardProps) {
  return (
    <Card
      className="hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
      role="listitem"
    >
      <CardContent className="py-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <h3 className="font-semibold text-lg">{project.name}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {project.description || 'No description'}
                </p>
                <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                  {project.github_repo_url && (
                    <div className="flex items-center gap-1">
                      <GitBranch className="h-3 w-3" />
                      <span className="truncate max-w-xs">{project.github_repo_url}</span>
                    </div>
                  )}
                  {project.language && (
                    <Badge variant="outline" className="text-xs">{project.language}</Badge>
                  )}
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <time dateTime={project.updated_at}>
                      {new Date(project.updated_at).toLocaleDateString()}
                    </time>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={project.is_active ? "success" : "secondary"}>
              {project.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); onClick() }}>
              View Details
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ProjectsPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const { data: projects = [], isLoading, error, refetch, isRefetching } = useProjects()

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('name')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [selectedLanguage, setSelectedLanguage] = useState('all')

  // Debounce search for better performance
  const debouncedSearchTerm = useDebounce(searchTerm, 300)

  // Handle GitHub connection success/error from URL params
  useEffect(() => {
    const githubConnected = searchParams?.get('github_connected')
    const error = searchParams?.get('error')
    const errorDescription = searchParams?.get('error_description')
    const errorDetail = searchParams?.get('error_detail')

    if (githubConnected === 'true') {
      console.log('[Projects Page] GitHub connected successfully')
      toast({
        title: 'GitHub Connected',
        description: 'Your GitHub account has been connected successfully',
      })
      setShowCreateModal(true)
    } else if (error) {
      console.warn('[Projects Page] GitHub connection error:', error)
      console.warn('[Projects Page] Error detail:', errorDetail || errorDescription)

      const errorMsg = errorDetail || errorDescription || 'Failed to connect GitHub account'

      toast({
        variant: 'destructive',
        title: 'GitHub Connection Failed',
        description: errorMsg,
        duration: 10000,
      })
    }

    // Clean up URL params
    if (githubConnected || error) {
      const url = new URL(window.location.href)
      url.searchParams.delete('github_connected')
      url.searchParams.delete('error')
      url.searchParams.delete('error_description')
      url.searchParams.delete('error_detail')
      window.history.replaceState({}, '', url.toString())
    }
  }, [searchParams, toast])

  // Memoize filtered and sorted projects for performance
  const filteredProjects = useMemo(() => {
    return projects
      .filter(project => {
        const matchesSearch = project.name.toLowerCase().includes(debouncedSearchTerm.toLowerCase()) ||
          (project.description?.toLowerCase() || '').includes(debouncedSearchTerm.toLowerCase())

        const matchesStatus = selectedStatus === 'all' ||
          (selectedStatus === 'active' && project.is_active) ||
          (selectedStatus === 'inactive' && !project.is_active)

        const matchesLanguage = selectedLanguage === 'all' || project.language === selectedLanguage

        return matchesSearch && matchesStatus && matchesLanguage
      })
      .sort((a, b) => {
        switch (sortBy) {
          case 'name':
            return a.name.localeCompare(b.name)
          case 'recent':
            return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          case 'language':
            return (a.language || '').localeCompare(b.language || '')
          default:
            return 0
        }
      })
  }, [projects, debouncedSearchTerm, selectedStatus, selectedLanguage, sortBy])

  // Extract unique languages for filter
  const availableLanguages = useMemo(() => {
    const languages = new Set(projects.map(p => p.language).filter((lang): lang is string => Boolean(lang)))
    return Array.from(languages).sort()
  }, [projects])

  const handleRefresh = useCallback(() => {
    refetch()
  }, [refetch])

  const handleExport = useCallback(() => {
    // Export projects as CSV
    const csvContent = [
      ['Name', 'Description', 'Language', 'Repository', 'Status', 'Created', 'Updated'],
      ...filteredProjects.map(project => [
        project.name,
        project.description || '',
        project.language || '',
        project.github_repo_url || '',
        project.is_active ? 'Active' : 'Inactive',
        new Date(project.created_at).toLocaleDateString(),
        new Date(project.updated_at).toLocaleDateString()
      ])
    ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'projects.csv'
    a.click()
    URL.revokeObjectURL(url)
  }, [filteredProjects])

  return (
    <MainLayout>
      <div className="space-y-6" role="main" aria-labelledby="projects-title">
        <PageHeader
          title="Projects"
          description="Manage and monitor your code repositories"
          actions={
            <div className="flex gap-2">
              <Button
                onClick={handleRefresh}
                disabled={isRefetching}
                variant="outline"
                size="sm"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isRefetching ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button
                onClick={handleExport}
                variant="outline"
                size="sm"
              >
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
              <Button onClick={() => setShowCreateModal(true)} aria-label="Add new project">
                <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                Add Project
              </Button>
            </div>
          }
        />

        <AddProjectModal
          open={showCreateModal}
          onClose={() => setShowCreateModal(false)}
        />

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Failed to load projects. Please try again.
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

        {/* Filters and Controls */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col lg:flex-row gap-4" role="search" aria-label="Project filters">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  <Input
                    placeholder="Search projects..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9"
                    aria-label="Search projects by name or description"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                  <SelectTrigger className="w-32" aria-label="Filter by status">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                  <SelectTrigger className="w-32" aria-label="Filter by language">
                    <SelectValue placeholder="Language" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Languages</SelectItem>
                    {availableLanguages.map(lang => (
                      <SelectItem key={lang} value={lang}>{lang}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={sortBy} onValueChange={setSortBy}>
                  <SelectTrigger className="w-40" aria-label="Sort projects by">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="name">Name</SelectItem>
                    <SelectItem value="recent">Recently Updated</SelectItem>
                    <SelectItem value="language">Language</SelectItem>
                  </SelectContent>
                </Select>

                <div className="flex gap-1 border rounded-md p-1" role="group" aria-label="View mode">
                  <Button
                    variant={viewMode === 'grid' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('grid')}
                    aria-label="Grid view"
                    aria-pressed={viewMode === 'grid'}
                  >
                    <Grid3x3 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                  <Button
                    variant={viewMode === 'list' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('list')}
                    aria-label="List view"
                    aria-pressed={viewMode === 'list'}
                  >
                    <List className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Filter Summary */}
            {(debouncedSearchTerm || selectedStatus !== 'all' || selectedLanguage !== 'all') && (
              <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                <Filter className="h-4 w-4" />
                <span>
                  Showing {filteredProjects.length} of {projects.length} projects
                  {debouncedSearchTerm && ` matching "${debouncedSearchTerm}"`}
                  {selectedStatus !== 'all' && ` with status "${selectedStatus}"`}
                  {selectedLanguage !== 'all' && ` in "${selectedLanguage}"`}
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Projects Grid/List */}
        {isLoading ? (
          <div className={viewMode === 'grid' ? 'grid gap-4 md:grid-cols-2 lg:grid-cols-3' : 'space-y-4'}>
            {[...Array(6)].map((_, i) => (
              viewMode === 'grid' ? <ProjectCardSkeleton key={i} /> : <ProjectListSkeleton key={i} />
            ))}
          </div>
        ) : filteredProjects.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <GitBranch className="h-12 w-12 text-muted-foreground mb-4" aria-hidden="true" />
              <h3 className="text-lg font-semibold mb-2">
                {projects.length === 0 ? 'No projects found' : 'No projects match your filters'}
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                {projects.length === 0
                  ? 'Get started by adding your first project'
                  : 'Try adjusting your search or filters'
                }
              </p>
              <div className="flex gap-2">
                {projects.length === 0 ? (
                  <Button onClick={() => setShowCreateModal(true)} aria-label="Add your first project">
                    <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                    Add Project
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setSearchTerm('')
                        setSelectedStatus('all')
                        setSelectedLanguage('all')
                      }}
                    >
                      Clear Filters
                    </Button>
                    <Button onClick={() => setShowCreateModal(true)}>
                      <Plus className="mr-2 h-4 w-4" />
                      Add Project
                    </Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        ) : (
          <div
            className={viewMode === 'grid' ? 'grid gap-4 md:grid-cols-2 lg:grid-cols-3' : 'space-y-4'}
            role="list"
            aria-label="Projects list"
          >
            {filteredProjects.map((project) => (
              viewMode === 'grid' ? (
                <ProjectGridCard
                  key={project.id}
                  project={project}
                  onClick={() => router.push(`/projects/${project.id}`)}
                />
              ) : (
                <ProjectListCard
                  key={project.id}
                  project={project}
                  onClick={() => router.push(`/projects/${project.id}`)}
                />
              )
            ))}
          </div>
        )}

        {/* Load More / Pagination could be added here for large datasets */}
        {filteredProjects.length > 0 && (
          <div className="text-center text-sm text-muted-foreground">
            Showing {filteredProjects.length} projects
          </div>
        )}
      </div>
    </MainLayout>
  )
}

export default function ProjectsPage() {
  return (
    <Suspense fallback={
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title="Projects" description="Loading..." />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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
        </div>
      </MainLayout>
    }>
      <ProjectsPageContent />
    </Suspense>
  )
}
