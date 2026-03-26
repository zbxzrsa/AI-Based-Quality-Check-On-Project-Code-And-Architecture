/**
 * usePermission Hook
 * Checks if user has specific permissions based on their role
 */
'use client';

import { useAuth } from '@/contexts/AuthContext';
import { Permission, Role } from '@/types/rbac';
import { useMemo } from 'react';

// Role-Permission mapping
const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  [Role.ADMIN]: [
    Permission.CREATE_USER,
    Permission.DELETE_USER,
    Permission.UPDATE_USER,
    Permission.VIEW_USER,
    Permission.CREATE_PROJECT,
    Permission.DELETE_PROJECT,
    Permission.UPDATE_PROJECT,
    Permission.VIEW_PROJECT,
    Permission.MODIFY_CONFIG,
    Permission.VIEW_CONFIG,
    Permission.EXPORT_REPORT,
  ],
  [Role.USER]: [
    Permission.CREATE_PROJECT,
    Permission.UPDATE_PROJECT,
    Permission.VIEW_PROJECT,
    Permission.VIEW_CONFIG,
    Permission.EXPORT_REPORT,
  ],
};

interface UsePermissionReturn {
  hasPermission: (permission: Permission) => boolean;
  loading: boolean;
}

export function usePermission(): UsePermissionReturn {
  const { user, loading } = useAuth();

  const userPermissions = useMemo(() => {
    if (!user?.role) return [];
    const role = user.role as Role;
    return ROLE_PERMISSIONS[role] || [];
  }, [user]);

  const hasPermission = (permission: Permission): boolean => {
    return userPermissions.includes(permission);
  };

  return {
    hasPermission,
    loading,
  };
}
