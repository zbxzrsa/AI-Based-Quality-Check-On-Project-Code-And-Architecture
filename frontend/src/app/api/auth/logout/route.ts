import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { fetchBackendWithFallback } from '@/lib/server/backend';

export async function POST(_request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get('access_token')?.value;

    // Call backend logout endpoint if we have a token
    if (accessToken) {
      try {
        await fetchBackendWithFallback('/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });
      } catch (error) {
        // Continue with logout even if backend call fails
        console.error('Backend logout error:', error);
      }
    }

    // Clear cookies
    cookieStore.delete('access_token');
    cookieStore.delete('refresh_token');

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Logout error:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
