import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Mock data - replace with actual backend API call
    const reviews = [
      {
        id: '1',
        title: 'Add user authentication feature',
        repository: 'frontend-app',
        author: 'john.doe',
        status: 'approved',
        qualityScore: 92,
        securityScore: 95,
        createdAt: '2024-01-15T10:30:00Z',
        updatedAt: '2024-01-15T14:20:00Z',
      },
      {
        id: '2',
        title: 'Fix database connection pooling',
        repository: 'backend-api',
        author: 'jane.smith',
        status: 'in_progress',
        qualityScore: 85,
        securityScore: 88,
        createdAt: '2024-01-16T09:15:00Z',
        updatedAt: '2024-01-16T11:45:00Z',
      },
    ];

    return NextResponse.json(reviews);
  } catch (error) {
    console.error('Error fetching reviews:', error);
    return NextResponse.json(
      { error: 'Failed to fetch reviews' },
      { status: 500 }
    );
  }
}
