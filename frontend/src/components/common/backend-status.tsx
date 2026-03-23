'use client';

/**
 * Backend Status Component
 * 
 * Displays backend availability status and provides retry functionality.
 * Shows a prominent banner when backend is unavailable.
 * 
 * Validates Requirements: 3.2, 3.3, 3.4, 3.5, 3.6
 */

import React, { useState, useEffect } from 'react';
import { AlertTriangle, X, RefreshCw } from 'lucide-react';
import { useBackendStatus } from '@/hooks/useBackendStatus';
import { Button } from '@/components/ui/button';

export function BackendStatusBanner() {
  const { isOnline, isChecking, retry } = useBackendStatus();
  const [isDismissed, setIsDismissed] = useState(false);

  // Auto-dismiss banner when backend becomes available
  useEffect(() => {
    if (isOnline === true) {
      setIsDismissed(false);
    }
  }, [isOnline]);

  // Don't show banner if backend is online or status is unknown
  if (isOnline !== false || isDismissed) {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800 dark:text-red-200">
              Backend Not Available
            </p>
            <p className="text-xs text-red-700 dark:text-red-300 mt-1">
              The backend server is currently unavailable. Some features may not work properly.
              <a 
                href="/docs" 
                className="ml-2 underline hover:no-underline"
              >
                View API docs
              </a>
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 ml-4">
          <Button
            variant="outline"
            size="sm"
            onClick={retry}
            disabled={isChecking}
            className="bg-white dark:bg-gray-800 border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900/30"
          >
            {isChecking ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Checking...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </>
            )}
          </Button>

          <button
            onClick={() => setIsDismissed(true)}
            className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 p-1"
            aria-label="Dismiss banner"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default BackendStatusBanner;
