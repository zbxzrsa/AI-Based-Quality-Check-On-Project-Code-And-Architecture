'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
    Plus,
    Eye,
    Network,
    AlertTriangle,
    ArrowRight
} from 'lucide-react'

export function QuickActions() {
    const actions = [
        {
            label: 'Add New Project',
            description: 'Create a repository entry and start tracking reviews.',
            icon: Plus,
        },
        {
            label: 'View All Reviews',
            description: 'Open the review list and inspect recent pull requests.',
            icon: Eye,
        },
        {
            label: 'Architecture Overview',
            description: 'Jump to branch topology and system health signals.',
            icon: Network,
        },
        {
            label: 'View Critical Issues',
            description: 'Focus on blockers and high priority findings first.',
            icon: AlertTriangle,
        },
    ]

    return (
        <Card className="col-span-3">
            <CardHeader className="pb-4">
                <CardTitle className="text-lg">Quick Actions</CardTitle>
                <CardDescription>
                    Common tasks and shortcuts
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
                {actions.map((action) => (
                    <Button
                        key={action.label}
                        variant="outline"
                        className="h-auto w-full justify-between rounded-lg px-4 py-3"
                    >
                        <div className="flex items-start gap-3 text-left">
                            <div className="mt-0.5 rounded-md bg-muted p-2">
                                <action.icon className="h-4 w-4" />
                            </div>
                            <div className="space-y-1">
                                <div className="text-sm font-medium">{action.label}</div>
                                <div className="text-xs text-muted-foreground">{action.description}</div>
                            </div>
                        </div>
                        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                    </Button>
                ))}
            </CardContent>
        </Card>
    )
}
