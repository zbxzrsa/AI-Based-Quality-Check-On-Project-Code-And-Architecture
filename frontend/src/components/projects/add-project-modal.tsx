// @ts-nocheck - Force cache refresh 2026-03-21T17:50:00
'use client'

import { useState, useEffect } from 'react'
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
  github_repo_url: z.string().optional().or(z.literal('')),
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
  language: string | null
}

export function AddProjectModal({ open, onClose }: AddProjectModalProps) {
  const { toast } = useToast()
  const createProject = useCreateProject()
  const [step, setStep] = useState<'github' | 'select-repo' | 'confirm'>('github')
  const [githubConnected, setGithubConnected] = useState(false)
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
    watch,
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      github_repo_url: '',
      name: '',
      description: '',
    },
  })

  // Check if GitHub is already connected
  useEffect(() => {
    if (open) {
      checkGitHubConnection()
    }
  }, [open])

  // Listen for GitHub connection success from URL params
  useEffect(() => {
    if (open) {
      const params = new URLSearchParams(window.location.search)
      if (params.get('github_connected') === 'true') {
        setTimeout(() => { checkGitHubConnection() }, 500)
        const url = new URL(window.location.href)
        url.searchParams.delete('github_connected')
        window.history.replaceState({}, '', url.toString())
      }
    }
  }, [open])

  const checkGitHubConnection = async () => {
    try {
      const response = await fetch('/api/github/status')
      if (response.ok) {
        const data = await response.json()
        setGithubConnected(data.connected)
        setGithubUsername(data.username)
        if (data.connected) {
          setStep('select-repo')
          fetchRepositories()
        } else {
          setStep('github')
        }
      } else {
        setStep('github')
      }
    } catch {
      // GitHub not configured or unavailable — show connect button
      setStep('github')
      setGithubConnected(false)
    }
  }

  const connectGitHub = () => {
    // GitHub Client ID (public value, safe to include in client-side code)
    const clientId = 'Ov23lidr2qGzsgBCOrXH'

    const redirectUri = encodeURIComponent(`${window.location.origin}/api/github/callback`)
    const scope = 'repo,read:user'
    const state = crypto.randomUUID()
    sessionStorage.setItem('github_oauth_state', state)
    window.location.href = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}&state=${state}`
  }

  const fetchRepositories = async () => {
    setLoadingRepos(true)
    try {
      const response = await fetch('/api/github/repositories')
      if (response.ok) {
        const data = await response.json()
        setRepositories(data.repositories || [])
      } else if (response.status === 401 || response.status === 400) {
        setGithubConnected(false)
        setStep('github')
        toast({ variant: 'destructive', title: 'GitHub 连接已断开', description: '请重新连接 GitHub 账号' })
      } else {
        toast({ variant: 'destructive', title: '获取仓库失败', description: '请重试或重新连接 GitHub' })
      }
    } catch {
      toast({ variant: 'destructive', title: '错误', description: '无法获取 GitHub 仓库列表' })
    } finally {
      setLoadingRepos(false)
    }
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
      // IMPORTANT: Use selectedRepo directly as source of truth for GitHub data
      // react-hook-form's setValue may not persist github_repo_url correctly
      const submitData: any = {
        name: data.name,
        description: data.description || undefined,
      }

      if (selectedRepo) {
        submitData.github_repo_url = selectedRepo.html_url
        submitData.language = selectedRepo.language || undefined
      }

      console.log('[AddProject] Submitting with data:', JSON.stringify(submitData))
      await createProject.mutateAsync(submitData)
      toast({ title: '项目已创建', description: '项目创建成功' })
      reset()
      setStep('github')
      setSelectedRepo(null)
      onClose()
    } catch (error: any) {
      const errorMessage = error.message || 'An error occurred'
      toast({
        variant: 'destructive',
        title: '创建失败',
        description: errorMessage.includes('已被关联')
          ? '该仓库已关联到现有项目，请选择其他仓库或检查已有项目'
          : errorMessage,
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
          <DialogTitle>添加新项目</DialogTitle>
          <DialogDescription>
            {step === 'github' && '连接 GitHub 账号，导入仓库并启用自动代码审查'}
            {step === 'select-repo' && '从 GitHub 账号中选择一个仓库'}
            {step === 'confirm' && '确认项目信息'}
          </DialogDescription>
        </DialogHeader>

        {/* Step 1: Connect GitHub */}
        {step === 'github' && (
          <div className="space-y-4 py-4">
            <Card className="p-6 text-center space-y-4">
              <Github className="h-16 w-16 mx-auto text-muted-foreground" />
              <div>
                <h3 className="text-lg font-semibold">连接 GitHub 账号</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  连接 GitHub 账号以导入仓库并启用自动代码审查
                </p>
              </div>
              <Button onClick={connectGitHub} className="w-full">
                <Github className="mr-2 h-4 w-4" />
                连接 GitHub
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
                <span className="text-sm font-medium">已连接: {githubUsername}</span>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={fetchRepositories}>刷新</Button>
                <Button variant="ghost" size="sm" onClick={() => { setGithubConnected(false); setStep('github') }}>
                  重新连接
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
                    <p className="text-sm text-muted-foreground">未找到仓库</p>
                  </Card>
                ) : (
                  repositories.map((repo) => (
                    <Card key={repo.id} className="p-4 cursor-pointer hover:bg-accent transition-colors" onClick={() => handleRepoSelect(repo)}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium">{repo.name}</h4>
                            {repo.private && <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">Private</span>}
                          </div>
                          {repo.description && <p className="text-sm text-muted-foreground mt-1">{repo.description}</p>}
                          <p className="text-xs text-muted-foreground mt-2">{repo.full_name}</p>
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
            <input type="hidden" {...register('github_repo_url')} />
            <Card className="p-4 bg-muted">
              <div className="flex items-center gap-2 mb-2">
                <Github className="h-4 w-4" />
                <span className="text-sm font-medium">已选择仓库</span>
              </div>
              <p className="text-sm">{selectedRepo.full_name}</p>
            </Card>

            <div className="space-y-2">
              <Label htmlFor="name">项目名称</Label>
              <Input id="name" placeholder="My Awesome Project" {...register('name')} disabled={createProject.isPending} />
              {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">描述（可选）</Label>
              <Input id="description" placeholder="项目简要描述" {...register('description')} disabled={createProject.isPending} />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setStep('select-repo')} disabled={createProject.isPending}>返回</Button>
              <Button type="submit" disabled={createProject.isPending}>
                {createProject.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                创建项目
              </Button>
            </DialogFooter>
          </form>
        )}

        {(step === 'github' || step === 'select-repo') && (
          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>取消</Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
