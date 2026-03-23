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
  // ADMIN: Full system control - all permissions
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
  // MANAGER: Project oversight & ROI
  [Role.MANAGER]: [
    Permission.VIEW_USER,
    Permission.CREATE_PROJECT,
    Permission.DELETE_PROJECT,
    Permission.UPDATE_PROJECT,
    Permission.VIEW_PROJECT,
    Permission.VIEW_CONFIG,
    Permission.EXPORT_REPORT,
  ],
  // REVIEWER: Read/Write analysis
  [Role.REVIEWER]: [
    Permission.UPDATE_PROJECT,
    Permission.VIEW_PROJECT,
    Permission.VIEW_CONFIG,
    Permission.EXPORT_REPORT,
  ],
  // PROGRAMMER: CRUD own branch
  [Role.PROGRAMMER]: [
    Permission.CREATE_PROJECT,
    Permission.UPDATE_PROJECT,
    Permission.VIEW_PROJECT,
    Permission.VIEW_CONFIG,
    Permission.EXPORT_REPORT,
  ],
  // DEVELOPER: Developer role
  [Role.DEVELOPER]: [
    Permission.CREATE_PROJECT,
    Permission.UPDATE_PROJECT,
    Permission.VIEW_PROJECT,
    Permission.VIEW_CONFIG,
  ],
  // COMPLIANCE_OFFICER: Compliance officer role
  [Role.COMPLIANCE_OFFICER]: [
    Permission.VIEW_PROJECT,
    Permission.VIEW_CONFIG,
  ],
  // VISITOR: Read-only grants
  [Role.VISITOR]: [
    Permission.VIEW_PROJECT,
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
