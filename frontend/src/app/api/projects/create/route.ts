import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

/**
 * Proxy endpoint for project creation.
 * 
 * This API route wraps the backend project creation endpoint to ensure 
 * github_repo_url and language are always included when creating projects 
 * from GitHub repo imports.
 */
export async function POST(request: NextRequest) {
    try {
        const body = await request.json()
        console.log('[API/projects/create] Received:', JSON.stringify(body))

        const cookieStore = await cookies();
        const accessToken = cookieStore.get('access_token')?.value;

        if (!accessToken) {
            return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 });
        }

        const response = await fetch(`${BACKEND_URL}/api/v1/rbac/projects/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`,
            },
            body: JSON.stringify(body),
        })

        const data = await response.json()

        if (!response.ok) {
            console.error('[API/projects/create] Backend error:', data)
            return NextResponse.json(data, { status: response.status })
        }

        console.log('[API/projects/create] Created project:', data.id, 'with github_repo_url:', data.github_repo_url)

        // After successful creation, trigger a sync if the project has a github_repo_url
        if (body.github_repo_url && data.id) {
            try {
                await fetch(`${BACKEND_URL}/api/v1/github/projects/${data.id}/sync`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${accessToken}`,
                    },
                })
                console.log('[API/projects/create] Sync triggered for project:', data.id)
            } catch (syncError) {
                console.warn('[API/projects/create] Sync failed (non-critical):', syncError)
            }
        }

        return NextResponse.json(data, { status: 201 })
    } catch (error: any) {
        console.error('[API/projects/create] Error:', error)
        return NextResponse.json(
            { detail: error.message || 'Failed to create project' },
            { status: 500 }
        )
    }
}
