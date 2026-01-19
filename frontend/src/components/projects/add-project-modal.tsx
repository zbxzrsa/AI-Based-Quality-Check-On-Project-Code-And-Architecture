'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import axios from 'axios'
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
import { Loader2 } from 'lucide-react'

const projectSchema = z.object({
  name: z.string().min(3, 'Name must be at least 3 characters'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  repository: z.string().url('Must be a valid URL').or(z.string().regex(/^[\w-]+\/[\w-]+\/[\w-]+$/, 'Must be a valid repository path')),
  webhookUrl: z.string().url('Must be a valid webhook URL').optional().or(z.literal('')),
})

type ProjectFormData = z.infer<typeof projectSchema>

interface AddProjectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
  project?: {
    id: string
    name: string
    description: string
    repository: string
    webhookUrl?: string
  }
}

export function AddProjectModal({ open, onOpenChange, onSuccess, project }: AddProjectModalProps) {
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(false)
  const isEdit = !!project

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: project || {
      name: '',
      description: '',
      repository: '',
      webhookUrl: '',
    },
  })

  const onSubmit = async (data: ProjectFormData) => {
    setIsLoading(true)

    try {
      if (isEdit) {
        await axios.put(`/api/v1/projects/${project.id}`, data)
        toast({
          title: 'Project Updated',
          description: 'Project has been updated successfully',
        })
      } else {
        await axios.post('/api/v1/projects', data)
        toast({
          title: 'Project Created',
          description: 'Project has been created successfully',
        })
      }
      
      reset()
      onOpenChange(false)
      onSuccess?.()
    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: isEdit ? 'Update Failed' : 'Creation Failed',
        description: error.response?.data?.detail || 'An error occurred',
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Project' : 'Add New Project'}</DialogTitle>
          <DialogDescription>
            {isEdit ? 'Update project information' : 'Add a new project to start code review and analysis'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Project Name</Label>
            <Input
              id="name"
              placeholder="My Awesome Project"
              {...register('name')}
              disabled={isLoading}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              placeholder="Brief description of your project"
              {...register('description')}
              disabled={isLoading}
            />
            {errors.description && (
              <p className="text-sm text-destructive">{errors.description.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="repository">Repository URL</Label>
            <Input
              id="repository"
              placeholder="https://github.com/username/repo or github.com/username/repo"
              {...register('repository')}
              disabled={isLoading}
            />
            {errors.repository && (
              <p className="text-sm text-destructive">{errors.repository.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Enter the full repository URL or path (e.g., github.com/user/repo)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="webhookUrl">Webhook URL (Optional)</Label>
            <Input
              id="webhookUrl"
              placeholder="https://your-domain.com/webhook"
              {...register('webhookUrl')}
              disabled={isLoading}
            />
            {errors.webhookUrl && (
              <p className="text-sm text-destructive">{errors.webhookUrl.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Configure webhook to receive real-time updates
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEdit ? 'Update Project' : 'Create Project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
