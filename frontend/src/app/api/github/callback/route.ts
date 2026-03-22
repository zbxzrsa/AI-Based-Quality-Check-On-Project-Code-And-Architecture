import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// Use BACKEND_URL for server-side (Docker network), fallback to NEXT_PUBLIC_BACKEND_URL for local dev
const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const code = searchParams.get('code');
    const error = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');
    const state = searchParams.get('state');

    if (error) {
      return NextResponse.redirect(
        new URL(`/projects?error=${encodeURIComponent(error)}&error_description=${encodeURIComponent(errorDescription || '')}`, request.url)
      );
    }

    if (!code) {
      return NextResponse.redirect(
        new URL('/projects?error=no_code', request.url)
      );
    }

    const cookieStore = await cookies();
    const storedState = cookieStore.get('github_oauth_state')?.value;
    const accessToken = cookieStore.get('access_token')?.value;

    if (!state || !storedState || state !== storedState) {
      const response = NextResponse.redirect(
        new URL('/projects?error=invalid_github_oauth_state', request.url)
      );
      response.cookies.delete('github_oauth_state');
      return response;
    }

    if (!accessToken) {
      const response = NextResponse.redirect(
        new URL('/login?returnUrl=/projects', request.url)
      );
      response.cookies.delete('github_oauth_state');
      return response;
    }
    
    // Exchange code for GitHub token via backend
    const response = await fetch(`${BACKEND_URL}/api/v1/github/connect`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ code }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      
      // Extract detailed error message
      const errorDetail = errorData.detail || 'Unknown error';
      const errorMessage = typeof errorDetail === 'string' 
        ? errorDetail 
        : JSON.stringify(errorDetail);
      
      const redirectResponse = NextResponse.redirect(
        new URL(`/projects?error=github_connection_failed&error_detail=${encodeURIComponent(errorMessage)}`, request.url)
      );
      redirectResponse.cookies.delete('github_oauth_state');
      return redirectResponse;
    }

    await response.json();

    // Redirect back to projects page with success flag
    const redirectResponse = NextResponse.redirect(
      new URL('/projects?github_connected=true', request.url)
    );
    redirectResponse.cookies.delete('github_oauth_state');
    return redirectResponse;
  } catch (error) {
    console.error('[GitHub Callback] Unexpected error:', error);
    const response = NextResponse.redirect(
      new URL('/projects?error=internal_error', request.url)
    );
    response.cookies.delete('github_oauth_state');
    return response;
  }
}
