import { NextResponse } from 'next/server';
import {
  BackendFetchError,
  fetchBackendWithFallback,
  getBackendBaseCandidates,
} from '@/lib/server/backend';

export async function GET() {
  const backendCandidates = getBackendBaseCandidates();

  try {
    const { response, backendUrl } = await fetchBackendWithFallback(
      '/health/live',
      { method: 'GET', cache: 'no-store' },
      5000
    );

    if (!response.ok) {
      return NextResponse.json(
        { status: 'unhealthy', backendStatus: response.status, backendUrl },
        { status: response.status }
      );
    }

    return NextResponse.json({ status: 'ok', backendUrl }, { status: 200 });
  } catch (error) {
    if (error instanceof BackendFetchError) {
      return NextResponse.json(
        {
          status: 'unavailable',
          error: 'Backend health check failed',
          attempted: error.attempted,
          details: error.details,
        },
        { status: 503 }
      );
    }

    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      {
        status: 'unavailable',
        error: 'Backend health check failed',
        attempted: backendCandidates,
        details: [message],
      },
      { status: 503 }
    );
  }
}
