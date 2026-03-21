import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();

    const response = await fetch(`${BACKEND_URL}/api/v1/analyze/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body,
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { detail: errorText || `Analyze request failed with ${response.status}` },
        { status: response.status }
      );
    }

    const headers = new Headers();
    headers.set('Content-Type', response.headers.get('Content-Type') || 'text/event-stream');
    headers.set('Cache-Control', 'no-cache');
    headers.set('Connection', 'keep-alive');

    return new Response(response.body, {
      status: 200,
      headers,
    });
  } catch {
    return NextResponse.json(
      { detail: 'Failed to proxy analyze request to backend' },
      { status: 500 }
    );
  }
}
