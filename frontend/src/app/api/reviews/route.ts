import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

type Project = {
  id: string;
  name: string;
  github_repo_url?: string | null;
};

type PullRequest = {
  id: string;
  number: number;
  title: string;
  status: string;
  risk_score?: number | null;
  created_at: string;
  analyzed_at?: string | null;
};

type ProjectPullsResponse = {
  pull_requests: PullRequest[];
};

const toReviewStatus = (status: string): 'pending' | 'in_progress' | 'approved' | 'rejected' => {
  switch (status) {
    case 'analyzing':
      return 'in_progress';
    case 'approved':
    case 'reviewed':
    case 'merged':
      return 'approved';
    case 'rejected':
      return 'rejected';
    default:
      return 'pending';
  }
};

const toQualityScore = (riskScore?: number | null) => {
  if (typeof riskScore !== 'number') {
    return 85;
  }

  return Math.max(0, Math.min(100, 100 - riskScore));
};

const toSecurityScore = (riskScore?: number | null) => {
  if (typeof riskScore !== 'number') {
    return 88;
  }

  return Math.max(0, Math.min(100, 100 - Math.round(riskScore * 0.8)));
};

export async function GET() {
  try {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get('access_token')?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }

    const projectsResponse = await fetch(`${BACKEND_URL}/api/v1/rbac/projects`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!projectsResponse.ok) {
      const error = await projectsResponse.json().catch(() => ({ detail: 'Failed to fetch projects' }));
      return NextResponse.json(error, { status: projectsResponse.status });
    }

    const projects = (await projectsResponse.json()) as Project[];

    const pullResponses = await Promise.all(
      projects.map(async (project) => {
        const pullsResponse = await fetch(`${BACKEND_URL}/api/v1/github/projects/${project.id}/pulls?state=all`, {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
          cache: 'no-store',
        });

        if (!pullsResponse.ok) {
          return [];
        }

        const pullsData = (await pullsResponse.json()) as ProjectPullsResponse;

        return pullsData.pull_requests.map((pullRequest) => ({
          id: pullRequest.id,
          title: pullRequest.title,
          repository: project.name,
          author: project.github_repo_url || 'GitHub',
          status: toReviewStatus(pullRequest.status),
          qualityScore: toQualityScore(pullRequest.risk_score),
          securityScore: toSecurityScore(pullRequest.risk_score),
          createdAt: pullRequest.created_at,
          updatedAt: pullRequest.analyzed_at || pullRequest.created_at,
          prNumber: pullRequest.number,
        }));
      })
    );

    const reviews = pullResponses.flat().sort((a, b) => {
      return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
    });

    return NextResponse.json({ reviews });
  } catch (error) {
    console.error('Error fetching reviews:', error);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
