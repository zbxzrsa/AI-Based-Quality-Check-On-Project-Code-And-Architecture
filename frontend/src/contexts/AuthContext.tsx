'use client';

import { createContext, useContext, useEffect, useState, ReactNode, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Role, Permission } from '@/types/rbac';
import { apiGet, apiPost } from '@/lib/api-client';

// User type matching backend response
type User = {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  role: Role | null;
  permissions: Permission[];
  login: (email: string, password: string, returnUrl?: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  isAuthenticated: boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Role-Permission mapping
const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  [Role.ADMIN]: [
    Permission.VIEW_PROJECTS,
    Permission.CREATE_PROJECT,
    Permission.MODIFY_PROJECT,
    Permission.DELETE_PROJECT,
    Permission.VIEW_USERS,
    Permission.CREATE_USER,
    Permission.MODIFY_USER,
    Permission.DELETE_USER,
    Permission.VIEW_REVIEWS,
    Permission.CREATE_REVIEW,
    Permission.MODIFY_REVIEW,
    Permission.MODIFY_CONFIG,
  ],
  [Role.USER]: [
    Permission.VIEW_PROJECTS,
    Permission.CREATE_PROJECT,
    Permission.MODIFY_PROJECT,
    Permission.VIEW_REVIEWS,
    Permission.CREATE_REVIEW,
    Permission.MODIFY_REVIEW,
  ],
};

// Token refresh interval: 20 minutes (tokens expire in 24 hours, refresh well before)
const TOKEN_REFRESH_INTERVAL = 20 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [role, setRole] = useState<Role | null>(null);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const router = useRouter();
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Update role and permissions when user changes
  useEffect(() => {
    if (user) {
      setRole(user.role);
      setPermissions(ROLE_PERMISSIONS[user.role] || []);
    } else {
      setRole(null);
      setPermissions([]);
    }
  }, [user]);

  // Fetch current user from backend using httpOnly cookie
  const fetchCurrentUser = useCallback(async () => {
    try {
      const userData = await apiGet<User>('/api/auth/me', {
        cache: 'no-store',
        timeoutMs: 8000,
      });
      setUser(userData);
      return true;
    } catch {
      setUser(null);
      return false;
    }
  }, []);

  // Refresh access token using refresh token in httpOnly cookie
  const refreshToken = useCallback(async () => {
    try {
      await apiPost('/api/auth/refresh', undefined, {
        cache: 'no-store',
        timeoutMs: 8000,
      });
      await fetchCurrentUser();
      return true;
    } catch {
      setUser(null);
      return false;
    }
  }, [fetchCurrentUser]);

  // Setup automatic token refresh
  useEffect(() => {
    if (user) {
      // Clear any existing timer
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }

      // Set up periodic token refresh
      refreshTimerRef.current = setInterval(() => {
        refreshToken();
      }, TOKEN_REFRESH_INTERVAL);

      return () => {
        if (refreshTimerRef.current) {
          clearInterval(refreshTimerRef.current);
        }
      };
    }
  }, [user, refreshToken]);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      setLoading(true);
      await fetchCurrentUser();
      setLoading(false);
    };

    initAuth();
  }, [fetchCurrentUser]);

  const login = async (email: string, password: string, returnUrl?: string) => {
    setLoading(true);
    try {
      await apiPost('/api/auth/login', { email, password }, { timeoutMs: 8000 });

      // Fetch user data after successful login
      const userFetched = await fetchCurrentUser();
      
      if (!userFetched) {
        throw new Error('Failed to fetch user data');
      }
      
      // Redirect to returnUrl if provided, otherwise to dashboard
      const redirectUrl = returnUrl || '/dashboard';
      router.push(redirectUrl);
    } finally {
      setLoading(false);
    }
  };

  const register = async (email: string, password: string, name: string) => {
    setLoading(true);
    try {
      await apiPost('/api/auth/register', { email, password, name }, { timeoutMs: 8000 });

      // After successful registration, log the user in
      await login(email, password);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      // Clear refresh timer
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }

      await apiPost('/api/auth/logout', undefined, { timeoutMs: 8000 });

      setUser(null);
      setRole(null);
      setPermissions([]);
      router.push('/');
    } finally {
      setLoading(false);
    }
  };

  const isAuthenticated = user !== null;

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        role,
        permissions,
        login,
        register,
        logout,
        refreshToken,
        isAuthenticated,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export { AuthContext };
