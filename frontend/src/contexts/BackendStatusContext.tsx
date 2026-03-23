'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

export interface BackendStatusContextType {
  isOnline: boolean | null;
  isChecking: boolean;
  retry: () => Promise<void>;
  lastChecked: Date | null;
}

const BackendStatusContext = createContext<BackendStatusContextType | undefined>(undefined);

export function BackendStatusProvider({ children }: { children: React.ReactNode }) {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkBackendHealth = useCallback(async () => {
    setIsChecking(true);
    try {
      // Health endpoint is at root level, not under /api/v1
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const baseUrl = apiUrl.replace('/api/v1', '');
      
      const response = await fetch(`${baseUrl}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      setIsOnline(response.ok);
      setLastChecked(new Date());
    } catch (error) {
      setIsOnline(false);
      setLastChecked(new Date());
    } finally {
      setIsChecking(false);
    }
  }, []);

  // Check backend health on mount
  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  // Poll backend health every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      checkBackendHealth();
    }, 30000);

    return () => clearInterval(interval);
  }, [checkBackendHealth]);

  const value: BackendStatusContextType = {
    isOnline,
    isChecking,
    retry: checkBackendHealth,
    lastChecked,
  };

  return (
    <BackendStatusContext.Provider value={value}>
      {children}
    </BackendStatusContext.Provider>
  );
}

export function useBackendStatusContext() {
  const context = useContext(BackendStatusContext);
  if (context === undefined) {
    throw new Error('useBackendStatusContext must be used within BackendStatusProvider');
  }
  return context;
}
