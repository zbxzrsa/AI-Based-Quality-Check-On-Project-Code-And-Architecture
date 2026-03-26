import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// Use BACKEND_URL for server-side (Docker network), fallback to NEXT_PUBLIC_BACKEND_URL for local dev
const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const cookieStore = await cookies();
    const accessToken = cookieStore.get('access_token')?.value;

    if (!accessToken) {
      return NextResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/github/projects/${id}/sync`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();

    if (typeof data?.message === 'string' && data.message.toLowerCase().startsWith('sync failed')) {
      return NextResponse.json(data, { status: 502 });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error syncing project:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
