'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, CheckCircle2, RefreshCw, X } from 'lucide-react';

export function BackendStatus() {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);
  const [isChecking, setIsChecking] = useState(false);

  const checkBackend = async () => {
    setIsChecking(true);
    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });
      setIsOnline(response.ok);
    } catch (error) {
      setIsOnline(false);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkBackend();
    // Check every 30 seconds
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, []);

  if (isOnline === null || isOnline === true || isDismissed) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-md">
      <Card className="p-4 border-yellow-500 bg-yellow-50 dark:bg-yellow-950/30">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold text-sm text-yellow-900 dark:text-yellow-100">
                  Backend Not Available
                </h3>
                <p className="text-xs text-yellow-800 dark:text-yellow-200 mt-1">
                  The backend server is not running. Some features may not work.
                  Start the backend server to enable full functionality.
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => setIsDismissed(true)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={checkBackend}
                disabled={isChecking}
                className="h-7 text-xs"
              >
                <RefreshCw
                  className={`h-3 w-3 mr-1 ${isChecking ? 'animate-spin' : ''}`}
                />
                Check Again
              </Button>
              <Button
                variant="outline"
                size="sm"
                asChild
                className="h-7 text-xs"
              >
                <a
                  href="http://localhost:8000/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open API Docs
                </a>
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
