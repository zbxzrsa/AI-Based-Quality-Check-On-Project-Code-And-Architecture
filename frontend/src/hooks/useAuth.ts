/**
 * Authentication API hooks
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import type { LoginFormData, RegisterFormData } from '@/lib/validations/auth';

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

/**
 * Login mutation hook
 */
export function useLogin() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LoginFormData) => {
      const response = await api.post<TokenResponse>('/auth/login', data);
      return response.data;
    },
    onSuccess: (data) => {
      // Store tokens
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      
      // Invalidate and refetch user data
      queryClient.invalidateQueries({ queryKey: ['user'] });
      
      // Redirect to dashboard
      router.push('/dashboard');
    },
  });
}

/**
 * Register mutation hook
 */
export function useRegister() {
  const router = useRouter();

  return useMutation({
    mutationFn: async (data: RegisterFormData) => {
      const response = await api.post<User>('/auth/register', {
        email: data.email,
        password: data.password,
        full_name: data.fullName,
      });
      return response.data;
    },
    onSuccess: () => {
      // Redirect to login page
      router.push('/auth/login?registered=true');
    },
  });
}

/**
 * Logout mutation hook
 */
export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await api.post('/auth/logout');
    },
    onSuccess: () => {
      // Clear tokens
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      
      // Clear user data
      queryClient.setQueryData(['user'], null);
      
      // Redirect to login
      router.push('/auth/login');
    },
  });
}

/**
 * Get current user query hook
 */
export function useUser() {
  return useQuery({
    queryKey: ['user'],
    queryFn: async () => {
      const token = localStorage.getItem('access_token');
      if (!token) return null;
      
      const response = await api.get<User>('/auth/me');
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });
}

/**
 * Check if user is authenticated
 */
export function useIsAuthenticated() {
  const { data: user, isLoading } = useUser();
  return {
    isAuthenticated: !!user,
    isLoading,
    user,
  };
}

/**
 * Refresh token mutation
 */
export function useRefreshToken() {
  return useMutation({
    mutationFn: async () => {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) throw new Error('No refresh token');

      const response = await api.post<TokenResponse>('/auth/refresh', {
        refresh_token: refreshToken,
      });
      return response.data;
    },
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
    },
  });
}
