'use client'

import { useState, useEffect, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { Loader2, Github, ExternalLink } from 'lucide-react'
import { useCreateProject } from '@/hooks/useProjects'
import { Card } from '@/components/ui/card'

const projectSchema = z.object({
  github_repo_url: z.string().url('Must be a valid GitHub repository URL'),
  name: z.string().min(3, 'Name must be at least 3 characters'),
  description: z.string().optional().or(z.literal('')),
})

type ProjectFormData = z.infer<typeof projectSchema>

interface AddProjectModalProps {
  open: boolean
  onClose: () => void
}

interface GitHubRepo {
  id: number
  name: string
  full_name: string
  description: string | null
  html_url: string
  private: boolean
}

export function AddProjectModal({ open, onClose }: AddProjectModalProps) {
  const { toast } = useToast()
  const createProject = useCreateProject()
  const [step, setStep] = useState<'github' | 'select-repo' | 'confirm'>('github')
  const [githubUsername, setGithubUsername] = useState<string | null>(null)
  const [repositories, setRepositories] = useState<GitHubRepo[]>([])
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null)
  const [loadingRepos, setLoadingRepos] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      github_repo_url: '',
      name: '',
      description: '',
    },
  })

  const fetchRepositories = useCallback(async () => {
    setLoadingRepos(true)
    try {
      const response = await fetch('/api/github/status')

      if (response.ok) {
        const data = await response.json()
        setGithubUsername(data.username)

        if (data.connected) {
          setStep('select-repo')
          const repositoriesResponse = await fetch('/api/github/repositories')

          if (repositoriesResponse.ok) {
            const repositoriesData = await repositoriesResponse.json()
            setRepositories(repositoriesData.repositories || [])
          } else if (repositoriesResponse.status === 401 || repositoriesResponse.status === 400) {
            setStep('github')
            toast({
              variant: 'destructive',
              title: 'GitHub Connection Lost',
              description: 'Please reconnect your GitHub account',
            })
          } else {
            toast({
              variant: 'destructive',
              title: 'Failed to fetch repositories',
              description: 'Please try again or reconnect your GitHub account',
            })
          }
        } else {
          setStep('github')
        }
      } else {
        setStep('github')
      }
    } catch (error) {
      console.error('[GitHub] Failed to refresh connection state:', error)
      setStep('github')
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'Failed to fetch GitHub repositories',
      })
    } finally {
      setLoadingRepos(false)
    }
  }, [toast])

  const checkGitHubConnection = useCallback(async () => {
    try {
      const response = await fetch('/api/github/status')

      if (response.ok) {
        const data = await response.json()
        setGithubUsername(data.username)

        if (data.connected) {
          setStep('select-repo')
          await fetchRepositories()
        } else {
          setStep('github')
        }
      } else {
        setStep('github')
      }
    } catch (error) {
      console.error('[GitHub] Failed to check connection status:', error)
      setStep('github')
      setGithubUsername(null)
    }
  }, [fetchRepositories])

  // Check if GitHub is already connected
  useEffect(() => {
    if (open) {
      void checkGitHubConnection()
    }
  }, [checkGitHubConnection, open])

  // Listen for GitHub connection success from URL params
  useEffect(() => {
    if (open) {
      const params = new URLSearchParams(window.location.search)
      if (params.get('github_connected') === 'true') {
        const timeoutId = window.setTimeout(() => {
          void checkGitHubConnection()
        }, 500)
        
        const url = new URL(window.location.href)
        url.searchParams.delete('github_connected')
        window.history.replaceState({}, '', url.toString())

        return () => {
          window.clearTimeout(timeoutId)
        }
      }
    }
  }, [checkGitHubConnection, open])

  const connectGitHub = () => {
    // Redirect to GitHub OAuth
    const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID

    if (!clientId) {
      toast({
        variant: 'destructive',
        title: 'Configuration Error',
        description: 'GitHub Client ID is not configured. Please contact administrator.',
      })
      return
    }
    
    const redirectUri = encodeURIComponent(`${window.location.origin}/api/github/callback`)
    const scope = 'repo,read:user'
    const state = crypto.randomUUID()

    // Store state in sessionStorage for verification
    sessionStorage.setItem('github_oauth_state', state)

    const oauthUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}&state=${state}`
    window.location.href = oauthUrl
  }

  const handleRepoSelect = (repo: GitHubRepo) => {
    setSelectedRepo(repo)
    setValue('github_repo_url', repo.html_url)
    setValue('name', repo.name)
    setValue('description', repo.description || '')
    setStep('confirm')
  }

  const onSubmit = async (data: ProjectFormData) => {
    try {
      // Only send name and description to match backend schema
      await createProject.mutateAsync({
        name: data.name,
        description: data.description || undefined,
        github_repo_url: data.github_repo_url,
        language: selectedRepo?.language || undefined,
      })
      
      toast({
        title: 'Project Created',
        description: 'Project has been created successfully',
      })
      
      reset()
      setStep('github')
      setSelectedRepo(null)
      onClose()
    } catch (error: unknown) {
      console.error('[AddProjectModal] Error creating project:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'An error occurred'
      toast({
        variant: 'destructive',
        title: 'Creation Failed',
        description: errorMessage,
      })
    }
  }

  const handleClose = () => {
    reset()
    setStep('github')
    setSelectedRepo(null)
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Add New Project</DialogTitle>
          <DialogDescription>
            {step === 'github' && 'Connect your GitHub account to import repositories'}
            {step === 'select-repo' && 'Select a repository from your GitHub account'}
            {step === 'confirm' && 'Confirm project details'}
          </DialogDescription>
        </DialogHeader>

        {/* Step 1: Connect GitHub */}
        {step === 'github' && (
          <div className="space-y-4 py-4">
            <Card className="p-6 text-center space-y-4">
              <Github className="h-16 w-16 mx-auto text-muted-foreground" />
              <div>
                <h3 className="text-lg font-semibold">Connect GitHub Account</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  Connect your GitHub account to import repositories and enable automatic code reviews
                </p>
              </div>
              <Button onClick={connectGitHub} className="w-full">
                <Github className="mr-2 h-4 w-4" />
                Connect with GitHub
              </Button>
            </Card>
          </div>
        )}

        {/* Step 2: Select Repository */}
        {step === 'select-repo' && (
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Github className="h-5 w-5" />
                <span className="text-sm font-medium">
                  Connected as {githubUsername}
                </span>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={fetchRepositories}>
                  Refresh
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => {
                    setGithubUsername(null)
                    setRepositories([])
                    setSelectedRepo(null)
                    setStep('github')
                  }}
                >
                  Reconnect
                </Button>
              </div>
            </div>

            {loadingRepos ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="max-h-[400px] overflow-y-auto space-y-2">
                {repositories.length === 0 ? (
                  <Card className="p-6 text-center">
                    <p className="text-sm text-muted-foreground">
                      No repositories found
                    </p>
                  </Card>
                ) : (
                  repositories.map((repo) => (
                    <Card
                      key={repo.id}
                      className="p-4 cursor-pointer hover:bg-accent transition-colors"
                      onClick={() => handleRepoSelect(repo)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium">{repo.name}</h4>
                            {repo.private && (
                              <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                                Private
                              </span>
                            )}
                          </div>
                          {repo.description && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {repo.description}
                            </p>
                          )}
                          <p className="text-xs text-muted-foreground mt-2">
                            {repo.full_name}
                          </p>
                        </div>
                        <ExternalLink className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </Card>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        {/* Step 3: Confirm Details */}
        {step === 'confirm' && selectedRepo && (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
            <Card className="p-4 bg-muted">
              <div className="flex items-center gap-2 mb-2">
                <Github className="h-4 w-4" />
                <span className="text-sm font-medium">Selected Repository</span>
              </div>
              <p className="text-sm">{selectedRepo.full_name}</p>
            </Card>

            <div className="space-y-2">
              <Label htmlFor="name">Project Name</Label>
              <Input
                id="name"
                placeholder="My Awesome Project"
                {...register('name')}
                disabled={createProject.isPending}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Input
                id="description"
                placeholder="Brief description of your project"
                {...register('description')}
                disabled={createProject.isPending}
              />
              {errors.description && (
                <p className="text-sm text-destructive">{errors.description.message}</p>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep('select-repo')}
                disabled={createProject.isPending}
              >
                Back
              </Button>
              <Button type="submit" disabled={createProject.isPending}>
                {createProject.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Project
              </Button>
            </DialogFooter>
          </form>
        )}

        {step !== 'confirm' && (
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
            >
              Cancel
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
