'use client';

import { createContext, useContext, useEffect, useState, ReactNode, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Role, Permission } from '@/types/rbac';

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
  [Role.DEVELOPER]: [
    Permission.VIEW_PROJECTS,
    Permission.CREATE_PROJECT,
    Permission.MODIFY_PROJECT,
    Permission.VIEW_REVIEWS,
    Permission.CREATE_REVIEW,
    Permission.MODIFY_REVIEW,
  ],
  [Role.REVIEWER]: [
    Permission.VIEW_PROJECTS,
    Permission.VIEW_REVIEWS,
    Permission.CREATE_REVIEW,
    Permission.MODIFY_REVIEW,
  ],
  [Role.COMPLIANCE_OFFICER]: [
    Permission.VIEW_PROJECTS,
    Permission.VIEW_REVIEWS,
    Permission.MODIFY_CONFIG,
  ],
  [Role.MANAGER]: [
    Permission.VIEW_PROJECTS,
    Permission.VIEW_USERS,
    Permission.VIEW_REVIEWS,
  ],
  [Role.PROGRAMMER]: [
    Permission.VIEW_PROJECTS,
    Permission.CREATE_PROJECT,
    Permission.MODIFY_PROJECT,
    Permission.VIEW_REVIEWS,
  ],
  [Role.VISITOR]: [
    Permission.VIEW_PROJECTS,
    Permission.VIEW_REVIEWS,
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
      console.log('[AuthContext] Fetching current user from /api/auth/me');
      
      const response = await fetch('/api/auth/me', {
        method: 'GET',
        credentials: 'include', // Include httpOnly cookies
      });

      console.log('[AuthContext] /api/auth/me response:', response.status);

      if (response.ok) {
        const userData = await response.json();
        console.log('[AuthContext] User data received:', userData);
        setUser(userData);
        return true;
      } else {
        // 401 is expected when not logged in, don't log as error
        if (response.status === 401) {
          console.log('[AuthContext] No active session found');
        } else {
          const errorData = await response.text();
          console.error('[AuthContext] Failed to fetch user:', response.status, errorData);
        }
        setUser(null);
        return false;
      }
    } catch (error) {
      console.error('[AuthContext] Error fetching current user:', error);
      setUser(null);
      return false;
    }
  }, []);

  // Refresh access token using refresh token in httpOnly cookie
  const refreshToken = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include', // Include httpOnly cookies
      });

      if (response.ok) {
        // Token refreshed successfully, fetch updated user data
        await fetchCurrentUser();
        return true;
      } else {
        // Refresh failed, user needs to log in again
        setUser(null);
        return false;
      }
    } catch (error) {
      console.error('Error refreshing token:', error);
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
      console.log('[AuthContext] Starting login...', { email, returnUrl });
      
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include httpOnly cookies
        body: JSON.stringify({ email, password }),
      });

      console.log('[AuthContext] Login response:', response.status);

      if (!response.ok) {
        const error = await response.json();
        console.error('[AuthContext] Login failed:', error);
        throw new Error(error.detail || error.message || 'Login failed');
      }

      const loginData = await response.json();
      console.log('[AuthContext] Login successful:', loginData);

      // Fetch user data after successful login
      console.log('[AuthContext] Fetching current user...');
      const userFetched = await fetchCurrentUser();
      console.log('[AuthContext] User fetched:', userFetched);
      
      if (!userFetched) {
        console.error('[AuthContext] Failed to fetch user data after login');
        throw new Error('Failed to fetch user data');
      }
      
      // Redirect to returnUrl if provided, otherwise to dashboard
      const redirectUrl = returnUrl || '/dashboard';
      console.log('[AuthContext] Redirecting to:', redirectUrl);
      router.push(redirectUrl);
    } catch (error) {
      console.error('[AuthContext] Login error:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const register = async (email: string, password: string, name: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password, name }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || error.message || 'Registration failed');
      }

      // After successful registration, log the user in
      await login(email, password);
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
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

      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });

      setUser(null);
      setRole(null);
      setPermissions([]);
      router.push('/');
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
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
