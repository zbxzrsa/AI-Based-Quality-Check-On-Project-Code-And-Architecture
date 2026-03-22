'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function TestCorsPage() {
    const [result, setResult] = useState<string>('');
    const [loading, setLoading] = useState(false);

    const getErrorMessage = (error: unknown) =>
        error instanceof Error ? error.message : 'Unknown request error';

    const testCors = async () => {
        setLoading(true);
        setResult('');

        try {
            const response = await fetch('http://localhost:8000/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (response.ok) {
                const data = await response.json();
                setResult(`SUCCESS: CORS test passed.\n\nResponse: ${JSON.stringify(data, null, 2)}`);
            } else {
                setResult(`HTTP error: ${response.status} ${response.statusText}`);
            }
        } catch (error: unknown) {
            setResult(`CORS error: ${getErrorMessage(error)}`);
        } finally {
            setLoading(false);
        }
    };

    const testHealthEndpoint = async () => {
        setLoading(true);
        setResult('');

        try {
            const response = await fetch('http://localhost:8000/health', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (response.ok) {
                const data = await response.json();
                setResult(`SUCCESS: Health check passed.\n\nResponse: ${JSON.stringify(data, null, 2)}`);
            } else {
                setResult(`HTTP error: ${response.status} ${response.statusText}`);
            }
        } catch (error: unknown) {
            setResult(`Request error: ${getErrorMessage(error)}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container mx-auto p-6">
            <Card>
                <CardHeader>
                    <CardTitle>CORS Test Page</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex space-x-4">
                        <Button
                            onClick={testCors}
                            disabled={loading}
                            variant="default"
                        >
                            {loading ? 'Testing...' : 'Test Root Path (/)'}
                        </Button>

                        <Button
                            onClick={testHealthEndpoint}
                            disabled={loading}
                            variant="outline"
                        >
                            {loading ? 'Testing...' : 'Test Health Check (/health)'}
                        </Button>
                    </div>

                    {result && (
                        <div className="mt-4">
                            <h3 className="text-lg font-semibold mb-2">Test result:</h3>
                            <pre className="bg-gray-100 p-4 rounded-lg text-sm whitespace-pre-wrap">
                                {result}
                            </pre>
                        </div>
                    )}

                    <div className="mt-6 text-sm text-gray-600">
                        <h4 className="font-semibold">Description:</h4>
                        <ul className="list-disc list-inside mt-2 space-y-1">
                            <li>This page verifies whether the frontend can reach the backend API.</li>
                            <li>If you see a CORS error, the backend cross-origin configuration likely needs attention.</li>
                            <li>Make sure the backend service is running on `http://localhost:8000`.</li>
                        </ul>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
