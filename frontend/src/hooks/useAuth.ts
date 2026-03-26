'use client';

/**
 * Compatibility auth hooks built on top of AuthContext.
 *
 * This keeps historical imports working while ensuring the app uses the
 * cookie-based session flow from `contexts/AuthContext`.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { LoginFormData, RegisterFormData } from '@/lib/validations/auth';
import { useAuth as useSessionAuth } from '@/contexts/AuthContext';

export function useLogin() {
  const auth = useSessionAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LoginFormData) => {
      await auth.login(data.email, data.password);
      return auth.user;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
  });
}

export function useRegister() {
  const auth = useSessionAuth();

  return useMutation({
    mutationFn: async (data: RegisterFormData) => {
      await auth.register(data.email, data.password, data.fullName || '');
      return auth.user;
    },
  });
}

export function useLogout() {
  const auth = useSessionAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await auth.logout();
    },
    onSuccess: () => {
      queryClient.setQueryData(['user'], null);
    },
  });
}

export function useUser() {
  const auth = useSessionAuth();
  return {
    data: auth.user,
    isLoading: auth.loading,
  };
}

export function useIsAuthenticated() {
  const auth = useSessionAuth();
  return {
    isAuthenticated: auth.isAuthenticated,
    isLoading: auth.loading,
    user: auth.user,
  };
}

export function useRefreshToken() {
  const auth = useSessionAuth();

  return useMutation({
    mutationFn: async () => {
      const refreshed = await auth.refreshToken();
      if (!refreshed) {
        throw new Error('Failed to refresh token');
      }
      return refreshed;
    },
  });
}
