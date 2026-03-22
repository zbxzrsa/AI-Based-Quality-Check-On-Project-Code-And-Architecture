import { NextResponse } from 'next/server';

export async function GET() {
  const clientId = process.env.GITHUB_CLIENT_ID || process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || null;
  const callbackUrl =
    process.env.GITHUB_CALLBACK_URL || process.env.NEXT_PUBLIC_GITHUB_CALLBACK_URL || null;

  return NextResponse.json({
    clientId,
    callbackUrl,
  });
}
