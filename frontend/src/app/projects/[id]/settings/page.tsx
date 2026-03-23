'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { MainLayout } from '@/components/layout/main-layout'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { useToast } from '@/hooks/use-toast'
import { ArrowLeft, Loader2, Save } from 'lucide-react'

const settingsSchema = z.object({
  qualityThreshold: z.number().min(0).max(100),
  securityThreshold: z.number().min(0).max(100),
  maintainabilityThreshold: z.number().min(0).max(100),
  enableEmailNotifications: z.boolean(),
  enableSlackNotifications: z.boolean(),
  slackWebhookUrl: z.string().url().optional().or(z.literal('')),
  webhookUrl: z.string().url().optional().or(z.literal('')),
  webhookSecret: z.string().optional(),
})

type SettingsFormData = z.infer<typeof settingsSchema>

export default function ProjectSettingsPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [isSaving, setIsSaving] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      qualityThreshold: 80,
      securityThreshold: 90,
      maintainabilityThreshold: 75,
      enableEmailNotifications: true,
      enableSlackNotifications: false,
      slackWebhookUrl: '',
      webhookUrl: '',
      webhookSecret: '',
    },
  })

  const onSubmit = async () => {
    setIsSaving(true)

    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      toast({
        title: 'Settings Saved',
        description: 'Project settings have been updated successfully',
      })
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Save Failed',
        description: 'Failed to save project settings',
      })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Project Settings"
          description="Configure quality thresholds, notifications, and integrations"
          actions={
            <Button variant="outline" onClick={() => router.back()}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          }
        />

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Quality Thresholds */}
          <Card>
            <CardHeader>
              <CardTitle>Quality Thresholds</CardTitle>
              <CardDescription>
                Set minimum quality scores for code reviews
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="qualityThreshold">Code Quality Threshold</Label>
                  <span className="text-sm text-muted-foreground">
                    {watch('qualityThreshold')}%
                  </span>
                </div>
                <Input
                  id="qualityThreshold"
                  type="range"
                  min="0"
                  max="100"
                  {...register('qualityThreshold', { valueAsNumber: true })}
                />
                <p className="text-xs text-muted-foreground">
                  PRs below this threshold will be flagged
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="securityThreshold">Security Threshold</Label>
                  <span className="text-sm text-muted-foreground">
                    {watch('securityThreshold')}%
                  </span>
                </div>
                <Input
                  id="securityThreshold"
                  type="range"
                  min="0"
                  max="100"
                  {...register('securityThreshold', { valueAsNumber: true })}
                />
                <p className="text-xs text-muted-foreground">
                  Security issues below this threshold will block merging
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="maintainabilityThreshold">Maintainability Threshold</Label>
                  <span className="text-sm text-muted-foreground">
                    {watch('maintainabilityThreshold')}%
                  </span>
                </div>
                <Input
                  id="maintainabilityThreshold"
                  type="range"
                  min="0"
                  max="100"
                  {...register('maintainabilityThreshold', { valueAsNumber: true })}
                />
                <p className="text-xs text-muted-foreground">
                  Code maintainability score threshold
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Notification Preferences */}
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Configure how you want to receive notifications
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="enableEmailNotifications">Email Notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Receive email notifications for reviews and issues
                  </p>
                </div>
                <Switch
                  id="enableEmailNotifications"
                  checked={watch('enableEmailNotifications')}
                  onCheckedChange={(checked) => setValue('enableEmailNotifications', checked)}
                />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="enableSlackNotifications">Slack Notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Send notifications to Slack channel
                  </p>
                </div>
                <Switch
                  id="enableSlackNotifications"
                  checked={watch('enableSlackNotifications')}
                  onCheckedChange={(checked) => setValue('enableSlackNotifications', checked)}
                />
              </div>

              {watch('enableSlackNotifications') && (
                <div className="space-y-2">
                  <Label htmlFor="slackWebhookUrl">Slack Webhook URL</Label>
                  <Input
                    id="slackWebhookUrl"
                    placeholder="https://hooks.slack.com/services/..."
                    {...register('slackWebhookUrl')}
                  />
                  {errors.slackWebhookUrl && (
                    <p className="text-sm text-destructive">{errors.slackWebhookUrl.message}</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Webhook Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>Webhook Configuration</CardTitle>
              <CardDescription>
                Configure webhooks for GitHub integration
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="webhookUrl">Webhook URL</Label>
                <Input
                  id="webhookUrl"
                  placeholder="https://your-domain.com/webhook"
                  {...register('webhookUrl')}
                />
                {errors.webhookUrl && (
                  <p className="text-sm text-destructive">{errors.webhookUrl.message}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  This URL will receive webhook events from GitHub
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="webhookSecret">Webhook Secret</Label>
                <Input
                  id="webhookSecret"
                  type="password"
                  placeholder="Enter webhook secret"
                  {...register('webhookSecret')}
                />
                <p className="text-xs text-muted-foreground">
                  Secret key for webhook signature verification
                </p>
              </div>

              <div className="rounded-lg bg-muted p-4">
                <h4 className="text-sm font-medium mb-2">Setup Instructions</h4>
                <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
                  <li>Go to your GitHub repository settings</li>
                  <li>Navigate to Webhooks section</li>
                  <li>Add the webhook URL above</li>
                  <li>Select events: Pull requests, Push, Issues</li>
                  <li>Add the secret key for security</li>
                </ol>
              </div>
            </CardContent>
          </Card>

          {/* Save Button */}
          <div className="flex justify-end gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <Save className="mr-2 h-4 w-4" />
              Save Settings
            </Button>
          </div>
        </form>
      </div>
    </MainLayout>
  )
}
