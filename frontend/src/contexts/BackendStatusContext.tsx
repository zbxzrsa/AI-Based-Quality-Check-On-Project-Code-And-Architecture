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
      const response = await fetch('/api/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
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
