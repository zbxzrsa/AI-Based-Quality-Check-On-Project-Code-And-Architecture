'use client';

import { SessionProvider } from 'next-auth/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { BackendStatusProvider } from '@/contexts/BackendStatusContext';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 1000 * 60 * 5, // 5 minutes
            gcTime: 1000 * 60 * 30, // 30 minutes
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  );

  return (
    <SessionProvider
      // Disable automatic session fetching to prevent errors when backend is down
      refetchInterval={0}
      refetchOnWindowFocus={false}
    >
      <BackendStatusProvider>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </BackendStatusProvider>
    </SessionProvider>
  );
}
