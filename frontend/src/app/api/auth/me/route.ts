import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { fetchBackendWithFallback } from '@/lib/server/backend';

async function parseBackendError(response: Response) {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    return response.json().catch(() => ({ detail: 'Failed to fetch current user' }));
  }

  const text = await response.text().catch(() => '');
  return { detail: text || 'Failed to fetch current user' };
}

export async function GET(_request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get('access_token')?.value;

    if (!accessToken) {
      return NextResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Call backend to get current user
    const { response } = await fetchBackendWithFallback('/api/v1/auth/me', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      // Token might be expired, clear cookies
      if (response.status === 401) {
        cookieStore.delete('access_token');
        cookieStore.delete('refresh_token');
      }

      const error = await parseBackendError(response);
      return NextResponse.json(error, { status: response.status });
    }

    const userData = await response.json();
    return NextResponse.json(userData);
  } catch (error) {
    console.error('Get current user error:', error);
    const detail = error instanceof Error ? error.message : 'Internal server error';
    return NextResponse.json(
      { detail },
      { status: 500 }
    );
  }
}
