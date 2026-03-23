import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// Use BACKEND_URL for server-side (Docker network), fallback to NEXT_PUBLIC_BACKEND_URL for local dev
const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get('access_token')?.value;

    if (!accessToken) {
      return NextResponse.json(
        { connected: false, username: null },
        { status: 200 }
      );
    }

    // Check GitHub connection status from backend
    const response = await fetch(`${BACKEND_URL}/api/v1/github/status`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      // If backend returns error, assume not connected
      return NextResponse.json(
        { connected: false, username: null },
        { status: 200 }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('GitHub status check error:', error);
    // Return not connected on error to avoid blocking the UI
    return NextResponse.json(
      { connected: false, username: null },
      { status: 200 }
    );
  }
}
