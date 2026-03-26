'use client'

import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'
import { Loader2, Github, ExternalLink, RefreshCw, ShieldCheck, X } from 'lucide-react'
import { useCreateProject } from '@/hooks/useProjects'
import { apiGet } from '@/lib/api-client'

const projectSchema = z.object({
  github_repo_url: z.string().url().optional().or(z.literal('')),
  name: z.string().min(3, 'Name must be at least 3 characters'),
  description: z.string().optional().or(z.literal('')),
})

type ProjectFormData = z.infer<typeof projectSchema>

type WizardStep = 'github' | 'select-repo' | 'confirm'

interface AddProjectModalProps {
  open: boolean
  onClose: () => void
  existingProjects?: Array<{
    id: string
    name: string
    github_repo_url?: string | null
  }>
}

interface GitHubRepo {
  id: number
  name: string
  full_name: string
  description: string | null
  html_url: string
  private: boolean
  language: string | null
}

interface GitHubConnectionStatus {
  connected: boolean
  username?: string | null
}

interface GitHubRepositoriesResponse {
  detail?: string
  repositories?: GitHubRepo[]
}

const GITHUB_CLIENT_ID = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || 'Ov23lidr2qGzsgBCOrXH'
const GITHUB_REDIRECT_URI =
  process.env.NEXT_PUBLIC_GITHUB_REDIRECT_URI || 'http://localhost:3000/api/github/callback'

function normalizeRepoUrl(url?: string | null) {
  if (!url) return null
  return url.trim().replace(/\.git$/i, '').replace(/\/+$/, '').toLowerCase()
}

export function AddProjectModal({ open, onClose, existingProjects = [] }: AddProjectModalProps) {
  const { toast } = useToast()
  const createProject = useCreateProject()
  const [step, setStep] = useState<WizardStep>('github')
  const [mounted, setMounted] = useState(false)
  const [githubUsername, setGithubUsername] = useState<string | null>(null)
  const [repositories, setRepositories] = useState<GitHubRepo[]>([])
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null)
  const [loadingRepos, setLoadingRepos] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      github_repo_url: '',
      name: '',
      description: '',
    },
  })

  const selectedRepoLabel = useMemo(() => {
    if (!selectedRepo) return ''
    return `${selectedRepo.full_name}${selectedRepo.language ? ` | ${selectedRepo.language}` : ''}`
  }, [selectedRepo])

  const linkedRepoMap = useMemo(() => {
    const entries = existingProjects
      .filter((project) => Boolean(project.github_repo_url))
      .map((project) => [normalizeRepoUrl(project.github_repo_url), project] as const)
      .filter((entry): entry is readonly [string, (typeof existingProjects)[number]] => Boolean(entry[0]))

    return new Map(entries)
  }, [existingProjects])

  const hasAvailableRepositories = useMemo(
    () => repositories.some((repo) => !linkedRepoMap.has(normalizeRepoUrl(repo.html_url) || '')),
    [repositories, linkedRepoMap]
  )

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!open) {
      return
    }
    void checkGitHubConnection()
  }, [open])

  useEffect(() => {
    if (!open || typeof document === 'undefined') {
      return
    }

    const originalOverflow = document.body.style.overflow
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        handleClose()
      }
    }

    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  const resetWizard = () => {
    reset()
    setStep('github')
    setSelectedRepo(null)
    setRepositories([])
  }

  const handleClose = () => {
    resetWizard()
    onClose()
  }

  const checkGitHubConnection = async () => {
    try {
      const data = await apiGet<GitHubConnectionStatus>('/api/github/status', {
        cache: 'no-store',
        timeoutMs: 8000,
      }).catch(() => ({ connected: false, username: null }))

      setGithubUsername(data.username ?? null)

      if (data.connected) {
        setStep('select-repo')
        await fetchRepositories()
      } else {
        setStep('github')
      }
    } catch {
      setGithubUsername(null)
      setStep('github')
    }
  }

  const connectGitHub = () => {
    const redirectUri = encodeURIComponent(GITHUB_REDIRECT_URI)
    const scope = encodeURIComponent('repo,read:user')
    const state = crypto.randomUUID()
    sessionStorage.setItem('github_oauth_state', state)
    window.location.href = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${redirectUri}&scope=${scope}&state=${state}`
  }

  const fetchRepositories = async () => {
    setLoadingRepos(true)

    try {
      const data = await apiGet<GitHubRepositoriesResponse>('/api/github/repositories', {
        cache: 'no-store',
        timeoutMs: 15000,
      })
      setRepositories(Array.isArray(data.repositories) ? data.repositories : [])
    } catch (error) {
      setStep('github')
      toast({
        variant: 'destructive',
        title: 'GitHub connection required',
        description: error instanceof Error ? error.message : 'Reconnect GitHub and try again.',
      })
    } finally {
      setLoadingRepos(false)
    }
  }

  const handleRepoSelect = (repo: GitHubRepo) => {
    const existingProject = linkedRepoMap.get(normalizeRepoUrl(repo.html_url) || '')
    if (existingProject) {
      toast({
        variant: 'destructive',
        title: 'Repository already linked',
        description: `"${repo.full_name}" is already connected to project "${existingProject.name}".`,
      })
      return
    }

    setSelectedRepo(repo)
    setValue('github_repo_url', repo.html_url)
    setValue('name', repo.name)
    setValue('description', repo.description || '')
    setStep('confirm')
  }

  const onSubmit = async (data: ProjectFormData) => {
    try {
      const duplicateProject = selectedRepo
        ? linkedRepoMap.get(normalizeRepoUrl(selectedRepo.html_url) || '')
        : undefined

      if (duplicateProject) {
        toast({
          variant: 'destructive',
          title: 'Repository already linked',
          description: `"${selectedRepo?.full_name}" is already connected to project "${duplicateProject.name}".`,
        })
        setStep('select-repo')
        return
      }

      const payload = {
        name: data.name,
        description: data.description || undefined,
        github_repo_url: selectedRepo?.html_url || data.github_repo_url || undefined,
        language: selectedRepo?.language || undefined,
      }

      await createProject.mutateAsync(payload)
      toast({
        title: 'Project created',
        description: 'GitHub sync has started and pull requests will appear shortly.',
      })
      handleClose()
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Project creation failed',
        description: error instanceof Error ? error.message : 'Please try again.',
      })
    }
  }

  if (!mounted || !open) {
    return null
  }

  return createPortal(
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        aria-label="Close add project modal"
        onClick={handleClose}
      />
      <div className="absolute inset-0 flex items-center justify-center overflow-y-auto p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-project-title"
          aria-describedby="add-project-description"
          className="relative flex w-full min-h-0 flex-col gap-4 overflow-hidden rounded-lg border bg-background p-6 shadow-lg"
          style={{
            width: 'min(640px, calc(100vw - 2rem))',
            maxWidth: '640px',
            height: 'min(90vh, 720px)',
          }}
        >
        <div className="flex flex-col space-y-1.5 text-center sm:text-left">
          <h2 id="add-project-title" className="text-lg font-semibold leading-none tracking-tight">
            Add Project
          </h2>
          <p id="add-project-description" className="text-sm text-muted-foreground">
            Connect GitHub, choose a repository, and start live pull request review plus architecture analysis.
          </p>
        </div>

        <div
          className="flex min-h-0 flex-1 flex-col overflow-hidden"
          style={{ minHeight: 0, flex: '1 1 auto', display: 'flex', flexDirection: 'column' }}
        >
        {step === 'github' && (
          <div className="h-full space-y-4 overflow-y-auto py-2 pr-1" style={{ minHeight: 0 }}>
            <Card className="space-y-4 p-6 text-center">
              <Github className="mx-auto h-14 w-14 text-muted-foreground" />
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Connect your GitHub account</h3>
                <p className="text-sm text-muted-foreground">
                  We use GitHub OAuth to import repositories, sync pull requests, and publish AI review results.
                </p>
              </div>
              <div className="rounded-lg border bg-muted/40 p-4 text-left text-sm text-muted-foreground">
                <div className="mb-2 flex items-center gap-2 font-medium text-foreground">
                  <ShieldCheck className="h-4 w-4" />
                  What happens after connecting
                </div>
                <ul className="space-y-1">
                  <li>Import repositories from your account</li>
                  <li>Sync pull requests and branches in real time</li>
                  <li>Generate code review issues and architecture insights</li>
                </ul>
              </div>
              <Button onClick={connectGitHub} className="w-full">
                <Github className="mr-2 h-4 w-4" />
                Connect GitHub
              </Button>
            </Card>
          </div>
        )}

        {step === 'select-repo' && (
          <div
            className="grid min-h-0 flex-1 grid-rows-[auto,minmax(0,1fr)] gap-4 py-2"
            style={{ minHeight: 0, flex: '1 1 auto' }}
          >
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <p className="text-sm font-medium">Connected account</p>
                <p className="text-sm text-muted-foreground">{githubUsername || 'GitHub user'}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => void fetchRepositories()} disabled={loadingRepos}>
                  <RefreshCw className={`mr-2 h-4 w-4 ${loadingRepos ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setGithubUsername(null)
                    setStep('github')
                  }}
                >
                  Reconnect
                </Button>
              </div>
            </div>

            {loadingRepos ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : repositories.length > 0 && !hasAvailableRepositories ? (
              <Card className="p-6 text-center text-sm text-muted-foreground">
                All repositories from this GitHub account are already linked to existing projects.
              </Card>
            ) : repositories.length === 0 ? (
              <Card className="p-6 text-center text-sm text-muted-foreground">
                No repositories were found for this account.
              </Card>
            ) : (
              <div
                data-testid="repo-list-scroll-area"
                className="min-h-0 overflow-y-auto pr-1"
                style={{ minHeight: 0, overflowY: 'auto' }}
              >
                <div className="space-y-2">
                  {repositories.map((repo) => (
                    (() => {
                      const existingProject = linkedRepoMap.get(normalizeRepoUrl(repo.html_url) || '')
                      const isLinked = Boolean(existingProject)

                      return (
                        <Card
                          key={repo.id}
                          className={`p-4 transition-colors ${
                            isLinked
                              ? 'cursor-not-allowed border-dashed bg-muted/40 opacity-75'
                              : 'cursor-pointer hover:bg-accent'
                          }`}
                          onClick={() => !isLinked && handleRepoSelect(repo)}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <h4 className="font-medium">{repo.full_name}</h4>
                                {isLinked && <Badge variant="destructive">Already linked</Badge>}
                                {repo.private && <Badge variant="outline">Private</Badge>}
                                {repo.language && <Badge variant="secondary">{repo.language}</Badge>}
                              </div>
                              <p className="mt-1 text-sm text-muted-foreground">
                                {repo.description || 'No repository description'}
                              </p>
                              {existingProject && (
                                <p className="mt-2 text-xs text-muted-foreground">
                                  Linked to project: {existingProject.name}
                                </p>
                              )}
                            </div>
                            <ExternalLink className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
                          </div>
                        </Card>
                      )
                    })()
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {step === 'confirm' && selectedRepo && (
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="h-full space-y-4 overflow-y-auto py-2 pr-1"
            style={{ minHeight: 0, overflowY: 'auto' }}
          >
            <input type="hidden" {...register('github_repo_url')} />

            <Card className="space-y-2 bg-muted/40 p-4">
              <p className="text-sm font-medium">Selected repository</p>
              <p className="text-sm text-muted-foreground">{selectedRepoLabel}</p>
              <p className="text-xs text-muted-foreground">{selectedRepo.html_url}</p>
            </Card>

            <div className="space-y-2">
              <Label htmlFor="name">Project name</Label>
              <Input id="name" placeholder="Repository display name" {...register('name')} disabled={createProject.isPending} />
              {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input id="description" placeholder="Short project summary" {...register('description')} disabled={createProject.isPending} />
            </div>

            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button type="button" variant="outline" onClick={() => setStep('select-repo')} disabled={createProject.isPending}>
                Back
              </Button>
              <Button type="submit" disabled={createProject.isPending}>
                {createProject.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create project
              </Button>
            </div>
          </form>
        )}
        </div>

        {(step === 'github' || step === 'select-repo') && (
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
          </div>
        )}
          <button
            type="button"
            className="absolute right-4 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            onClick={handleClose}
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

