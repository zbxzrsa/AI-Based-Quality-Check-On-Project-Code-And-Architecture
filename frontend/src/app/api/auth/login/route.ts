import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { fetchBackendWithFallback } from '@/lib/server/backend';

async function parseBackendError(response: Response) {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    return response.json().catch(() => ({ detail: 'Authentication request failed' }));
  }

  const text = await response.text().catch(() => '');
  return { detail: text || 'Authentication request failed' };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password } = body;

    if (!email || !password) {
      return NextResponse.json(
        { detail: 'Email and password are required' },
        { status: 400 }
      );
    }

    // Call backend login endpoint
    const { response } = await fetchBackendWithFallback('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await parseBackendError(response);
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    
    const token = data.access_token;
    const refreshToken = data.refresh_token;
    
    if (!token) {
      return NextResponse.json(
        { detail: 'No token received from server', response: data },
        { status: 500 }
      );
    }

    // Store tokens in httpOnly cookies
    const cookieStore = await cookies();
    
    // Access token cookie (8 hours - extended from 1 hour)
    cookieStore.set('access_token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 8, // 8 hours
      path: '/',
    });

    // Store refresh token if available
    if (refreshToken) {
      cookieStore.set('refresh_token', refreshToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 60 * 60 * 24 * 7, // 7 days
        path: '/',
      });
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Login error:', error);
    const detail = error instanceof Error ? error.message : 'Internal server error';
    return NextResponse.json(
      { detail },
      { status: 500 }
    );
  }
}
