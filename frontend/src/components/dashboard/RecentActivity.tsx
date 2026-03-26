'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
    GitPullRequest,
    AlertTriangle,
    FolderGit2,
    Network
} from 'lucide-react'

interface RecentActivityProps {
    isLoading: boolean
}

export function RecentActivity({ isLoading }: RecentActivityProps) {
    const activities = [
        {
            id: 'review-complete',
            icon: GitPullRequest,
            iconClassName: 'bg-primary/10 text-primary',
            title: 'New PR review completed',
            target: 'user-auth-service',
            time: '2 minutes ago',
            badge: { label: 'Passed', variant: 'success' as const },
        },
        {
            id: 'architecture-warning',
            icon: AlertTriangle,
            iconClassName: 'bg-yellow-500/10 text-yellow-600',
            title: 'Architecture drift detected',
            target: 'payment-service',
            time: '15 minutes ago',
            badge: { label: 'Warning', variant: 'warning' as const },
        },
        {
            id: 'project-added',
            icon: FolderGit2,
            iconClassName: 'bg-green-500/10 text-green-600',
            title: 'New project added',
            target: 'api-gateway',
            time: '1 hour ago',
            badge: { label: 'New', variant: 'default' as const },
        },
        {
            id: 'security-critical',
            icon: AlertTriangle,
            iconClassName: 'bg-red-500/10 text-red-600',
            title: 'Critical security issue found',
            target: 'auth-service',
            time: '3 hours ago',
            badge: { label: 'Critical', variant: 'destructive' as const },
        },
        {
            id: 'architecture-done',
            icon: Network,
            iconClassName: 'bg-blue-500/10 text-blue-600',
            title: 'Architecture analysis completed',
            target: 'microservices',
            time: '5 hours ago',
            badge: { label: 'Info', variant: 'info' as const },
        },
    ]

    return (
        <Card className="col-span-4">
            <CardHeader className="pb-4">
                <CardTitle className="text-lg">Recent Activity</CardTitle>
                <CardDescription>
                    Latest updates from your projects
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-3">
                    {isLoading ? (
                        <>
                            {[...Array(5)].map((_, i) => (
                                <div key={i} className="flex items-center space-x-4">
                                    <Skeleton className="h-10 w-10 rounded-full" />
                                    <div className="space-y-2 flex-1">
                                        <Skeleton className="h-4 w-full" />
                                        <Skeleton className="h-3 w-24" />
                                    </div>
                                </div>
                            ))}
                        </>
                    ) : (
                        activities.map((activity) => (
                            <div key={activity.id} className="flex items-start gap-4 rounded-lg border p-4">
                                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${activity.iconClassName}`}>
                                    <activity.icon className="h-5 w-5" />
                                </div>
                                <div className="min-w-0 flex-1 space-y-1">
                                    <p className="text-sm font-medium text-foreground">
                                        {activity.title} for <span className="text-primary">{activity.target}</span>
                                    </p>
                                    <p className="text-xs text-muted-foreground">{activity.time}</p>
                                </div>
                                <Badge variant={activity.badge.variant}>{activity.badge.label}</Badge>
                            </div>
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    )
}
