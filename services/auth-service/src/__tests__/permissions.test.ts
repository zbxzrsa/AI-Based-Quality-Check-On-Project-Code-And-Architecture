import { PermissionService } from '../services/permissions';
import { Role } from '@shared/types';

describe('PermissionService', () => {
  describe('createRole', () => {
    it('should create administrator role with full permissions', () => {
      // Act
      const role = PermissionService.createRole('administrator');

      // Assert
      expect(role.name).toBe('administrator');
      expect(role.permissions).toHaveLength(1);
      expect(role.permissions[0]?.resource).toBe('*');
      expect(role.permissions[0]?.actions).toEqual(['*']);
    });

    it('should create programmer role with appropriate permissions', () => {
      // Act
      const role = PermissionService.createRole('programmer');

      // Assert
      expect(role.name).toBe('programmer');
      expect(role.permissions.length).toBeGreaterThan(0);
      
      // Check for key programmer permissions
      const projectPermission = role.permissions.find((p: any) => p.resource === 'projects');
      expect(projectPermission).toBeTruthy();
      expect(projectPermission?.actions).toContain('read');
      expect(projectPermission?.actions).toContain('create');
      expect(projectPermission?.actions).toContain('update');
    });

    it('should create visitor role with read-only permissions', () => {
      // Act
      const role = PermissionService.createRole('visitor');

      // Assert
      expect(role.name).toBe('visitor');
      expect(role.permissions.length).toBeGreaterThan(0);
      
      // All permissions should be read-only
      role.permissions.forEach((permission: any) => {
        expect(permission.actions).toEqual(['read']);
      });
    });
  });

  describe('hasPermission', () => {
    let adminRole: Role;
    let programmerRole: Role;
    let visitorRole: Role;

    beforeEach(() => {
      adminRole = PermissionService.createRole('administrator');
      programmerRole = PermissionService.createRole('programmer');
      visitorRole = PermissionService.createRole('visitor');
    });

    it('should grant administrator access to any resource and action', () => {
      // Act & Assert
      expect(PermissionService.hasPermission([adminRole], 'projects', 'delete')).toBe(true);
      expect(PermissionService.hasPermission([adminRole], 'users', 'create')).toBe(true);
      expect(PermissionService.hasPermission([adminRole], 'system', 'admin')).toBe(true);
    });

    it('should grant programmer access to allowed resources and actions', () => {
      // Act & Assert
      expect(PermissionService.hasPermission([programmerRole], 'projects', 'read')).toBe(true);
      expect(PermissionService.hasPermission([programmerRole], 'projects', 'create')).toBe(true);
      expect(PermissionService.hasPermission([programmerRole], 'analysis', 'trigger')).toBe(true);
    });

    it('should deny programmer access to admin-only actions', () => {
      // Act & Assert
      expect(PermissionService.hasPermission([programmerRole], 'users', 'delete')).toBe(false);
      expect(PermissionService.hasPermission([programmerRole], 'system', 'admin')).toBe(false);
    });

    it('should grant visitor read access to allowed resources', () => {
      // Act & Assert
      expect(PermissionService.hasPermission([visitorRole], 'projects', 'read')).toBe(true);
      expect(PermissionService.hasPermission([visitorRole], 'analysis', 'read')).toBe(true);
      expect(PermissionService.hasPermission([visitorRole], 'dashboard', 'read')).toBe(true);
    });

    it('should deny visitor write access to any resource', () => {
      // Act & Assert
      expect(PermissionService.hasPermission([visitorRole], 'projects', 'create')).toBe(false);
      expect(PermissionService.hasPermission([visitorRole], 'analysis', 'trigger')).toBe(false);
      expect(PermissionService.hasPermission([visitorRole], 'reviews', 'update')).toBe(false);
    });

    it('should grant access if user has multiple roles and one allows the action', () => {
      // Act & Assert
      expect(PermissionService.hasPermission([visitorRole, programmerRole], 'projects', 'create')).toBe(true);
      expect(PermissionService.hasPermission([programmerRole, adminRole], 'users', 'delete')).toBe(true);
    });

    it('should deny access if no roles allow the action', () => {
      // Act & Assert
      expect(PermissionService.hasPermission([visitorRole], 'projects', 'delete')).toBe(false);
      expect(PermissionService.hasPermission([programmerRole, visitorRole], 'users', 'delete')).toBe(false);
    });

    it('should handle empty roles array', () => {
      // Act & Assert
      expect(PermissionService.hasPermission([], 'projects', 'read')).toBe(false);
    });
  });

  describe('getAllPermissions', () => {
    it('should return all permissions for administrator', () => {
      // Arrange
      const adminRole = PermissionService.createRole('administrator');

      // Act
      const permissions = PermissionService.getAllPermissions([adminRole]);

      // Assert
      expect(permissions).toContain('*:*');
    });

    it('should return specific permissions for programmer', () => {
      // Arrange
      const programmerRole = PermissionService.createRole('programmer');

      // Act
      const permissions = PermissionService.getAllPermissions([programmerRole]);

      // Assert
      expect(permissions).toContain('projects:read');
      expect(permissions).toContain('projects:create');
      expect(permissions).toContain('analysis:trigger');
      expect(permissions).not.toContain('*:*');
    });

    it('should combine permissions from multiple roles', () => {
      // Arrange
      const programmerRole = PermissionService.createRole('programmer');
      const visitorRole = PermissionService.createRole('visitor');

      // Act
      const permissions = PermissionService.getAllPermissions([programmerRole, visitorRole]);

      // Assert
      expect(permissions).toContain('projects:read');
      expect(permissions).toContain('projects:create');
      expect(permissions.length).toBeGreaterThan(0);
    });

    it('should deduplicate permissions from multiple roles', () => {
      // Arrange
      const role1 = PermissionService.createRole('programmer');
      const role2 = PermissionService.createRole('programmer');

      // Act
      const permissions = PermissionService.getAllPermissions([role1, role2]);

      // Assert
      const readPermissions = permissions.filter(p => p === 'projects:read');
      expect(readPermissions).toHaveLength(1);
    });
  });

  describe('validateRequiredPermissions', () => {
    let programmerRole: Role;

    beforeEach(() => {
      programmerRole = PermissionService.createRole('programmer');
    });

    it('should validate when user has all required permissions', () => {
      // Arrange
      const requiredPermissions = [
        { resource: 'projects', action: 'read' },
        { resource: 'analysis', action: 'read' },
      ];

      // Act
      const result = PermissionService.validateRequiredPermissions([programmerRole], requiredPermissions);

      // Assert
      expect(result.isValid).toBe(true);
      expect(result.missingPermissions).toHaveLength(0);
    });

    it('should identify missing permissions', () => {
      // Arrange
      const requiredPermissions = [
        { resource: 'projects', action: 'read' },
        { resource: 'users', action: 'delete' }, // Not allowed for programmer
      ];

      // Act
      const result = PermissionService.validateRequiredPermissions([programmerRole], requiredPermissions);

      // Assert
      expect(result.isValid).toBe(false);
      expect(result.missingPermissions).toHaveLength(1);
      expect(result.missingPermissions[0]).toEqual({ resource: 'users', action: 'delete' });
    });
  });

  describe('isAdministrator', () => {
    it('should return true for administrator role', () => {
      // Arrange
      const adminRole = PermissionService.createRole('administrator');

      // Act
      const result = PermissionService.isAdministrator([adminRole]);

      // Assert
      expect(result).toBe(true);
    });

    it('should return false for non-administrator roles', () => {
      // Arrange
      const programmerRole = PermissionService.createRole('programmer');
      const visitorRole = PermissionService.createRole('visitor');

      // Act
      const result = PermissionService.isAdministrator([programmerRole, visitorRole]);

      // Assert
      expect(result).toBe(false);
    });

    it('should return true if one of multiple roles is administrator', () => {
      // Arrange
      const adminRole = PermissionService.createRole('administrator');
      const programmerRole = PermissionService.createRole('programmer');

      // Act
      const result = PermissionService.isAdministrator([programmerRole, adminRole]);

      // Assert
      expect(result).toBe(true);
    });
  });

  describe('hasAnyRole', () => {
    let roles: Role[];

    beforeEach(() => {
      roles = [
        PermissionService.createRole('programmer'),
        PermissionService.createRole('visitor'),
      ];
    });

    it('should return true when user has one of the required roles', () => {
      // Act
      const result = PermissionService.hasAnyRole(roles, ['programmer', 'administrator']);

      // Assert
      expect(result).toBe(true);
    });

    it('should return false when user has none of the required roles', () => {
      // Act
      const result = PermissionService.hasAnyRole(roles, ['administrator']);

      // Assert
      expect(result).toBe(false);
    });

    it('should return false for empty required roles', () => {
      // Act
      const result = PermissionService.hasAnyRole(roles, []);

      // Assert
      expect(result).toBe(false);
    });

    it('should return false for empty user roles', () => {
      // Act
      const result = PermissionService.hasAnyRole([], ['programmer']);

      // Assert
      expect(result).toBe(false);
    });
  });
});