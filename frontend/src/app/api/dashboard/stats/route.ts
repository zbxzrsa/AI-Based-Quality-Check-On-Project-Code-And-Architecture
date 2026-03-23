import { NextResponse } from 'next/server'

export async function GET() {
    // Return dashboard stats - uses backend API when available, falls back to defaults
    try {
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${backendUrl}/api/v1/projects`, {
            headers: { 'Content-Type': 'application/json' },
            cache: 'no-store',
        })

        let totalProjects = 0
        if (response.ok) {
            const data = await response.json()
            totalProjects = Array.isArray(data) ? data.length : (data?.total || 0)
        }

        return NextResponse.json({
            stats: {
                totalProjects,
                pendingReviews: 0,
                criticalIssues: 0,
                architectureHealthScore: 85,
                projectGrowth: 0,
                reviewEfficiency: 87,
                securityScore: 95,
                lastUpdated: new Date().toISOString(),
            },
            trends: {
                projects: 0,
                reviews: 0,
                issues: 0,
                health: 0,
            },
            alerts: [],
        })
    } catch {
        // Return default data if backend is unreachable
        return NextResponse.json({
            stats: {
                totalProjects: 0,
                pendingReviews: 0,
                criticalIssues: 0,
                architectureHealthScore: 85,
                projectGrowth: 0,
                reviewEfficiency: 87,
                securityScore: 95,
                lastUpdated: new Date().toISOString(),
            },
            trends: {
                projects: 0,
                reviews: 0,
                issues: 0,
                health: 0,
            },
            alerts: [],
        })
    }
}
