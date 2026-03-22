import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const cookieStore = await cookies();
    const accessToken = cookieStore.get('access_token')?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/projects/${id}/architecture-analysis`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch architecture analysis' }));
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching architecture analysis:', error);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
