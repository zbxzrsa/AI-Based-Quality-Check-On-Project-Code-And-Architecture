import * as fc from 'fast-check';
import { AuthenticationService } from '../services/authentication';
import { UserService } from '../services/user';
import { PermissionService } from '../services/permissions';
import { JWTService } from '../utils/jwt';
import { RedisService } from '../services/redis';
import { AuditService } from '../services/audit';
import { User, AuthToken, Role } from '@shared/types';

// Mock dependencies
jest.mock('../services/user');
jest.mock('../services/permissions');
jest.mock('../utils/jwt');
jest.mock('../services/redis');
jest.mock('../services/audit');

const mockUserService = UserService as jest.Mocked<typeof UserService>;
const mockPermissionService = PermissionService as jest.Mocked<typeof PermissionService>;
const mockJWTService = JWTService as jest.Mocked<typeof JWTService>;
const mockRedisService = RedisService as jest.Mocked<typeof RedisService>;
const mockAuditService = AuditService as jest.Mocked<typeof AuditService>;

describe('Property-Based Tests: Authentication Service', () => {
  let authService: AuthenticationService;
  let mockRedisClient: any;

  beforeEach(() => {
    authService = new AuthenticationService();
    jest.clearAllMocks();

    // Mock Redis client
    mockRedisClient = {
      setEx: jest.fn().mockResolvedValue('OK'),
      get: jest.fn().mockResolvedValue('{"userId":"test"}'),
      del: jest.fn().mockResolvedValue(1),
    };
    mockRedisService.getClient.mockReturnValue(mockRedisClient);

    // Default mock implementations
    mockAuditService.logSuccessfulLogin.mockResolvedValue();
    mockAuditService.logFailedLogin.mockResolvedValue();
    mockAuditService.logAuthorizationFailure.mockResolvedValue();
    mockAuditService.logTokenRefresh.mockResolvedValue();
    mockAuditService.logLogout.mockResolvedValue();
  });

  /**
   * **Feature: ai-code-review-platform, Property 4: Authentication and Authorization Consistency**
   * **Validates: Requirements 6.1, 6.2, 6.4, 6.5**
   * 
   * For any user request to protected resources, the authentication system should correctly 
   * verify permissions based on assigned roles and log security events appropriately.
   */
  describe('Property 4: Authentication and Authorization Consistency', () => {
    // Generators for property-based testing
    const roleNameArb = fc.constantFrom('administrator', 'programmer', 'visitor') as fc.Arbitrary<'administrator' | 'programmer' | 'visitor'>;
    
    const permissionArb = fc.record({
      resource: fc.oneof(
        fc.constant('*'),
        fc.constantFrom('projects', 'analysis', 'reviews', 'architecture', 'dashboard', 'profile', 'users', 'system')
      ),
      actions: fc.oneof(
        fc.constant(['*']),
        fc.array(fc.constantFrom('read', 'create', 'update', 'delete', 'trigger', 'view', 'admin'), { minLength: 1, maxLength: 4 })
      )
    });

    const roleArb = fc.record({
      name: roleNameArb,
      permissions: fc.array(permissionArb, { minLength: 1, maxLength: 5 })
    }) as fc.Arbitrary<Role>;

    const userArb = fc.record({
      id: fc.string({ minLength: 1, maxLength: 50 }),
      email: fc.emailAddress(),
      name: fc.string({ minLength: 1, maxLength: 100 }),
      roles: fc.array(roleArb, { minLength: 1, maxLength: 3 }),
      preferences: fc.record({
        theme: fc.constantFrom('light', 'dark') as fc.Arbitrary<'light' | 'dark'>,
        notifications: fc.record({
          email: fc.boolean(),
          inApp: fc.boolean(),
          webhooks: fc.boolean()
        }),
        analysisSettings: fc.record({
          enabledRules: fc.array(fc.string(), { maxLength: 5 }),
          qualityThresholds: fc.array(fc.record({
            metric: fc.string(),
            threshold: fc.float({ min: 0, max: 100 }),
            operator: fc.constantFrom('gt', 'lt', 'eq', 'gte', 'lte') as fc.Arbitrary<'gt' | 'lt' | 'eq' | 'gte' | 'lte'>
          }), { maxLength: 3 }),
          preferredAIModel: fc.constantFrom('gpt-4', 'claude-3.5') as fc.Arbitrary<'gpt-4' | 'claude-3.5'>
        })
      }),
      lastLogin: fc.date()
    }) as fc.Arbitrary<User>;

    const credentialsArb = fc.record({
      email: fc.emailAddress(),
      password: fc.string({ minLength: 8, maxLength: 128 })
    });

    const authTokenArb = fc.record({
      userId: fc.string({ minLength: 1, maxLength: 50 }),
      roles: fc.array(roleNameArb, { minLength: 1, maxLength: 3 }),
      permissions: fc.array(fc.string(), { minLength: 1, maxLength: 10 }),
      expiresAt: fc.date({ min: new Date(Date.now() + 1000) }), // Future date
      refreshToken: fc.string({ minLength: 10, maxLength: 100 })
    });

    const resourceActionArb = fc.record({
      resource: fc.constantFrom('projects', 'analysis', 'reviews', 'architecture', 'dashboard', 'profile', 'users', 'system', 'admin'),
      action: fc.constantFrom('read', 'create', 'update', 'delete', 'trigger', 'view', 'admin')
    });

    const clientInfoArb = fc.record({
      ipAddress: fc.ipV4(),
      userAgent: fc.string({ minLength: 10, maxLength: 200 })
    });

    it('Property 4.1: Valid authentication always produces valid tokens with correct role-based permissions', async () => {
      await fc.assert(
        fc.asyncProperty(
          userArb,
          credentialsArb,
          clientInfoArb,
          async (user, credentials, clientInfo) => {
            // Arrange
            mockUserService.verifyCredentials.mockResolvedValue(user);
            const expectedPermissions = ['projects:read', 'analysis:read']; // Simplified for testing
            mockPermissionService.getAllPermissions.mockReturnValue(expectedPermissions);
            
            const expectedToken: AuthToken = {
              userId: user.id,
              roles: user.roles.map(r => r.name),
              permissions: expectedPermissions,
              expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
              refreshToken: 'refresh_token_123'
            };
            mockJWTService.generateToken.mockReturnValue(expectedToken);

            // Act
            const result = await authService.authenticate(credentials, clientInfo.ipAddress, clientInfo.userAgent);

            // Assert - Token structure consistency
            expect(result.userId).toBe(user.id);
            expect(result.roles).toEqual(user.roles.map(r => r.name));
            expect(result.permissions).toEqual(expectedPermissions);
            expect(result.expiresAt).toBeInstanceOf(Date);
            expect(result.refreshToken).toBeTruthy();

            // Assert - Audit logging consistency
            expect(mockAuditService.logSuccessfulLogin).toHaveBeenCalledWith(
              user.id,
              clientInfo.ipAddress,
              clientInfo.userAgent
            );

            // Assert - Permission service called with correct roles
            expect(mockPermissionService.getAllPermissions).toHaveBeenCalledWith(user.roles);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('Property 4.2: Authorization decisions are consistent with role-based permissions', async () => {
      await fc.assert(
        fc.asyncProperty(
          authTokenArb,
          resourceActionArb,
          userArb,
          clientInfoArb,
          async (token, resourceAction, user, clientInfo) => {
            // Arrange
            mockJWTService.isTokenExpired.mockReturnValue(false);
            mockUserService.getUserById.mockResolvedValue(user);
            
            // Test both permission granted and denied scenarios
            const hasPermission = Math.random() > 0.5;
            mockPermissionService.hasPermission.mockReturnValue(hasPermission);

            // Act
            const result = await authService.authorize(
              token,
              resourceAction.resource,
              resourceAction.action,
              clientInfo.ipAddress,
              clientInfo.userAgent
            );

            // Assert - Authorization result consistency
            expect(result).toBe(hasPermission);

            // Assert - Permission check called with correct parameters
            expect(mockPermissionService.hasPermission).toHaveBeenCalledWith(
              user.roles,
              resourceAction.resource,
              resourceAction.action
            );

            // Assert - Audit logging for denied access
            if (!hasPermission) {
              expect(mockAuditService.logAuthorizationFailure).toHaveBeenCalledWith(
                token.userId,
                resourceAction.resource,
                resourceAction.action,
                clientInfo.ipAddress,
                clientInfo.userAgent
              );
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('Property 4.3: Expired tokens are always rejected with appropriate audit logging', async () => {
      await fc.assert(
        fc.asyncProperty(
          authTokenArb,
          resourceActionArb,
          clientInfoArb,
          async (token, resourceAction, clientInfo) => {
            // Arrange - Force token to be expired
            mockJWTService.isTokenExpired.mockReturnValue(true);

            // Act
            const result = await authService.authorize(
              token,
              resourceAction.resource,
              resourceAction.action,
              clientInfo.ipAddress,
              clientInfo.userAgent
            );

            // Assert - Always deny expired tokens
            expect(result).toBe(false);

            // Assert - Audit failure logged for expired token
            expect(mockAuditService.logAuthorizationFailure).toHaveBeenCalledWith(
              token.userId,
              resourceAction.resource,
              resourceAction.action,
              clientInfo.ipAddress,
              clientInfo.userAgent
            );

            // Assert - Permission check should not be called for expired tokens
            expect(mockPermissionService.hasPermission).not.toHaveBeenCalled();
          }
        ),
        { numRuns: 100 }
      );
    });

    it('Property 4.4: Invalid sessions are always rejected with security event logging', async () => {
      await fc.assert(
        fc.asyncProperty(
          authTokenArb,
          resourceActionArb,
          clientInfoArb,
          async (token, resourceAction, clientInfo) => {
            // Arrange - Token not expired but session invalid
            mockJWTService.isTokenExpired.mockReturnValue(false);
            mockRedisClient.get.mockResolvedValue(null); // No session found

            // Act
            const result = await authService.authorize(
              token,
              resourceAction.resource,
              resourceAction.action,
              clientInfo.ipAddress,
              clientInfo.userAgent
            );

            // Assert - Always deny invalid sessions
            expect(result).toBe(false);

            // Assert - Security event logged
            expect(mockAuditService.logAuthorizationFailure).toHaveBeenCalledWith(
              token.userId,
              resourceAction.resource,
              resourceAction.action,
              clientInfo.ipAddress,
              clientInfo.userAgent
            );
          }
        ),
        { numRuns: 100 }
      );
    });

    it('Property 4.5: Administrator role always has access to any resource and action', async () => {
      await fc.assert(
        fc.asyncProperty(
          resourceActionArb,
          clientInfoArb,
          fc.string({ minLength: 1, maxLength: 50 }),
          async (resourceAction, clientInfo, userId) => {
            // Arrange - Create admin user and token
            const adminRole: Role = {
              name: 'administrator',
              permissions: [{ resource: '*', actions: ['*'] }]
            };
            
            const adminUser: User = {
              id: userId,
              email: 'admin@example.com',
              name: 'Admin User',
              roles: [adminRole],
              preferences: {
                theme: 'light',
                notifications: { email: true, inApp: true, webhooks: false },
                analysisSettings: { enabledRules: [], qualityThresholds: [], preferredAIModel: 'gpt-4' }
              },
              lastLogin: new Date()
            };

            const adminToken: AuthToken = {
              userId: userId,
              roles: ['administrator'],
              permissions: ['*:*'],
              expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
              refreshToken: 'admin_refresh_token'
            };

            mockJWTService.isTokenExpired.mockReturnValue(false);
            mockUserService.getUserById.mockResolvedValue(adminUser);
            mockPermissionService.hasPermission.mockReturnValue(true); // Admin always has permission

            // Act
            const result = await authService.authorize(
              adminToken,
              resourceAction.resource,
              resourceAction.action,
              clientInfo.ipAddress,
              clientInfo.userAgent
            );

            // Assert - Admin always authorized
            expect(result).toBe(true);

            // Assert - No authorization failure logged for admin
            expect(mockAuditService.logAuthorizationFailure).not.toHaveBeenCalled();
          }
        ),
        { numRuns: 100 }
      );
    });

    it('Property 4.6: Failed authentication attempts are always logged with appropriate details', async () => {
      await fc.assert(
        fc.asyncProperty(
          credentialsArb,
          clientInfoArb,
          async (credentials, clientInfo) => {
            // Arrange - Force authentication failure
            mockUserService.verifyCredentials.mockResolvedValue(null);

            // Act & Assert
            await expect(
              authService.authenticate(credentials, clientInfo.ipAddress, clientInfo.userAgent)
            ).rejects.toThrow('Invalid credentials');

            // Assert - Failed login logged with correct details
            expect(mockAuditService.logFailedLogin).toHaveBeenCalledWith(
              credentials.email,
              'Invalid credentials',
              clientInfo.ipAddress,
              clientInfo.userAgent
            );

            // Assert - No successful login logged
            expect(mockAuditService.logSuccessfulLogin).not.toHaveBeenCalled();
          }
        ),
        { numRuns: 100 }
      );
    });

    it('Property 4.7: Role-based access control is consistently enforced across all resources', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.constantFrom('programmer', 'visitor') as fc.Arbitrary<'programmer' | 'visitor'>,
          resourceActionArb,
          clientInfoArb,
          fc.string({ minLength: 1, maxLength: 50 }),
          async (roleName, resourceAction, clientInfo, userId) => {
            // Arrange - Create user with specific role
            const role = PermissionService.createRole(roleName);
            const user: User = {
              id: userId,
              email: `${roleName}@example.com`,
              name: `${roleName} User`,
              roles: [role],
              preferences: {
                theme: 'light',
                notifications: { email: true, inApp: true, webhooks: false },
                analysisSettings: { enabledRules: [], qualityThresholds: [], preferredAIModel: 'gpt-4' }
              },
              lastLogin: new Date()
            };

            const token: AuthToken = {
              userId: userId,
              roles: [roleName],
              permissions: [`${resourceAction.resource}:${resourceAction.action}`],
              expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
              refreshToken: 'test_refresh_token'
            };

            mockJWTService.isTokenExpired.mockReturnValue(false);
            mockUserService.getUserById.mockResolvedValue(user);
            
            // Use actual permission service logic for consistency
            const hasPermission = PermissionService.hasPermission([role], resourceAction.resource, resourceAction.action);
            mockPermissionService.hasPermission.mockReturnValue(hasPermission);

            // Act
            const result = await authService.authorize(
              token,
              resourceAction.resource,
              resourceAction.action,
              clientInfo.ipAddress,
              clientInfo.userAgent
            );

            // Assert - Result matches role permissions
            expect(result).toBe(hasPermission);

            // Assert - Visitor role should never have write access
            if (roleName === 'visitor' && ['create', 'update', 'delete', 'admin'].includes(resourceAction.action)) {
              expect(result).toBe(false);
              expect(mockAuditService.logAuthorizationFailure).toHaveBeenCalled();
            }

            // Assert - Programmer should have access to development resources
            if (roleName === 'programmer' && 
                ['projects', 'analysis', 'reviews'].includes(resourceAction.resource) && 
                ['read', 'create', 'update', 'trigger'].includes(resourceAction.action)) {
              expect(result).toBe(true);
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('Property 4.8: Session management maintains consistency between Redis and token state', async () => {
      await fc.assert(
        fc.asyncProperty(
          authTokenArb,
          userArb,
          async (token, user) => {
            // Arrange
            mockUserService.verifyCredentials.mockResolvedValue(user);
            mockPermissionService.getAllPermissions.mockReturnValue(token.permissions);
            mockJWTService.generateToken.mockReturnValue(token);

            // Act - Authenticate to create session
            await authService.authenticate({ email: user.email, password: 'password' });

            // Assert - Session stored in Redis
            expect(mockRedisClient.setEx).toHaveBeenCalledWith(
              `session:${token.userId}`,
              expect.any(Number),
              expect.stringContaining(token.userId)
            );

            // Assert - Refresh token mapping stored
            expect(mockRedisClient.setEx).toHaveBeenCalledWith(
              `refresh:${token.refreshToken}`,
              7 * 24 * 60 * 60, // 7 days
              token.userId
            );
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});