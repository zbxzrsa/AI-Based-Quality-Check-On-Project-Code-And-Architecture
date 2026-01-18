'use client';

import { AuthContext, AuthProvider as BaseAuthProvider } from './AuthContext';
import { useSession } from 'next-auth/react';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  
  return (
    <BaseAuthProvider session={session} status={status}>
      {children}
    </BaseAuthProvider>
  );
}

export { AuthContext } from './AuthContext';
