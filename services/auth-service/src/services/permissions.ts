import { Role, Permission } from '@shared/types';
import { logger } from '../utils/logger';

export interface PermissionCheck {
  resource: string;
  action: string;
}

export class PermissionService {
  /**
   * Default role definitions with their permissions
   */
  private static readonly DEFAULT_ROLES: Record<string, Permission[]> = {
    administrator: [
      { resource: '*', actions: ['*'] }, // Full access to everything
    ],
    programmer: [
      { resource: 'projects', actions: ['read', 'create', 'update'] },
      { resource: 'analysis', actions: ['read', 'create', 'trigger'] },
      { resource: 'reviews', actions: ['read', 'create', 'update'] },
      { resource: 'architecture', actions: ['read', 'view'] },
      { resource: 'dashboard', actions: ['read'] },
      { resource: 'profile', actions: ['read', 'update'] },
    ],
    visitor: [
      { resource: 'projects', actions: ['read'] },
      { resource: 'analysis', actions: ['read'] },
      { resource: 'reviews', actions: ['read'] },
      { resource: 'architecture', actions: ['read'] },
      { resource: 'dashboard', actions: ['read'] },
      { resource: 'profile', actions: ['read'] },
    ],
  };

  /**
   * Get default permissions for a role
   */
  static getDefaultPermissions(roleName: string): Permission[] {
    return this.DEFAULT_ROLES[roleName] || [];
  }

  /**
   * Create a role with default permissions
   */
  static createRole(roleName: 'administrator' | 'programmer' | 'visitor'): Role {
    const permissions = this.getDefaultPermissions(roleName);
    return {
      name: roleName,
      permissions,
    };
  }

  /**
   * Check if a user has permission to perform an action on a resource
   */
  static hasPermission(
    userRoles: Role[],
    resource: string,
    action: string
  ): boolean {
    logger.debug('Checking permission:', { userRoles: userRoles.map(r => r.name), resource, action });

    // Check each role's permissions
    for (const role of userRoles) {
      if (this.roleHasPermission(role, resource, action)) {
        logger.debug('Permission granted via role:', role.name);
        return true;
      }
    }

    logger.debug('Permission denied');
    return false;
  }

  /**
   * Check if a specific role has permission for a resource and action
   */
  private static roleHasPermission(role: Role, resource: string, action: string): boolean {
    for (const permission of role.permissions) {
      // Check for wildcard resource access (administrator)
      if (permission.resource === '*') {
        return permission.actions.includes('*') || permission.actions.includes(action);
      }

      // Check for exact resource match
      if (permission.resource === resource) {
        return permission.actions.includes('*') || permission.actions.includes(action);
      }

      // Check for resource pattern matching (e.g., "projects.*" matches "projects.123")
      if (permission.resource.endsWith('*')) {
        const baseResource = permission.resource.slice(0, -1);
        if (resource.startsWith(baseResource)) {
          return permission.actions.includes('*') || permission.actions.includes(action);
        }
      }
    }

    return false;
  }

  /**
   * Get all permissions for a set of roles
   */
  static getAllPermissions(roles: Role[]): string[] {
    const permissions = new Set<string>();

    for (const role of roles) {
      for (const permission of role.permissions) {
        if (permission.resource === '*' && permission.actions.includes('*')) {
          permissions.add('*:*');
        } else {
          for (const action of permission.actions) {
            permissions.add(`${permission.resource}:${action}`);
          }
        }
      }
    }

    return Array.from(permissions);
  }

  /**
   * Validate that required permissions are met
   */
  static validateRequiredPermissions(
    userRoles: Role[],
    requiredPermissions: PermissionCheck[]
  ): { isValid: boolean; missingPermissions: PermissionCheck[] } {
    const missingPermissions: PermissionCheck[] = [];

    for (const required of requiredPermissions) {
      if (!this.hasPermission(userRoles, required.resource, required.action)) {
        missingPermissions.push(required);
      }
    }

    return {
      isValid: missingPermissions.length === 0,
      missingPermissions,
    };
  }

  /**
   * Check if a user is an administrator
   */
  static isAdministrator(roles: Role[]): boolean {
    return roles.some(role => role.name === 'administrator');
  }

  /**
   * Check if a user has any of the specified roles
   */
  static hasAnyRole(userRoles: Role[], requiredRoles: string[]): boolean {
    const userRoleNames = userRoles.map(role => role.name);
    return requiredRoles.some(role => userRoleNames.includes(role as 'administrator' | 'programmer' | 'visitor'));
  }
}