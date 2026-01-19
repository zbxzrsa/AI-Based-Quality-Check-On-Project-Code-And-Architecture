import { AuthenticationService } from '../services/authentication';
import { UserService } from '../services/user';
import { PermissionService } from '../services/permissions';
import { JWTService } from '../utils/jwt';
import { RedisService } from '../services/redis';
import { AuditService } from '../services/audit';
import { User, AuthToken, Credentials } from '@shared/types';

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

describe('AuthenticationService', () => {
  let authService: AuthenticationService;
  let mockUser: User;
  let mockToken: AuthToken;
  let mockCredentials: Credentials;

  beforeEach(() => {
    authService = new AuthenticationService();
    
    // Reset all mocks
    jest.clearAllMocks();

    // Mock user data
    mockUser = {
      id: 'user_123',
      email: 'test@example.com',
      name: 'Test User',
      roles: [
        {
          name: 'programmer',
          permissions: [
            { resource: 'projects', actions: ['read', 'create'] },
          ],
        },
      ],
      preferences: {
        theme: 'light',
        notifications: { email: true, inApp: true, webhooks: false },
        analysisSettings: { enabledRules: [], qualityThresholds: [], preferredAIModel: 'gpt-4' },
      },
      lastLogin: new Date(),
    };

    // Mock token data
    mockToken = {
      userId: 'user_123',
      roles: ['programmer'],
      permissions: ['projects:read', 'projects:create'],
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
      refreshToken: 'refresh_token_123',
    };

    // Mock credentials
    mockCredentials = {
      email: 'test@example.com',
      password: 'password123',
    };

    // Mock Redis client
    const mockRedisClient = {
      setEx: jest.fn().mockResolvedValue('OK'),
      get: jest.fn().mockResolvedValue('{"userId":"user_123"}'),
      del: jest.fn().mockResolvedValue(1),
    };
    mockRedisService.getClient.mockReturnValue(mockRedisClient as any);
  });

  describe('authenticate', () => {
    it('should successfully authenticate valid credentials', async () => {
      // Arrange
      mockUserService.verifyCredentials.mockResolvedValue(mockUser);
      mockPermissionService.getAllPermissions.mockReturnValue(['projects:read', 'projects:create']);
      mockJWTService.generateToken.mockReturnValue(mockToken);
      mockAuditService.logSuccessfulLogin.mockResolvedValue();

      // Act
      const result = await authService.authenticate(mockCredentials);

      // Assert
      expect(result).toEqual(mockToken);
      expect(mockUserService.verifyCredentials).toHaveBeenCalledWith(
        mockCredentials.email,
        mockCredentials.password
      );
      expect(mockJWTService.generateToken).toHaveBeenCalledWith(
        mockUser.id,
        ['programmer'],
        ['projects:read', 'projects:create']
      );
      expect(mockAuditService.logSuccessfulLogin).toHaveBeenCalledWith(
        mockUser.id,
        undefined,
        undefined
      );
    });

    it('should fail authentication with invalid credentials', async () => {
      // Arrange
      mockUserService.verifyCredentials.mockResolvedValue(null);
      mockAuditService.logFailedLogin.mockResolvedValue();

      // Act & Assert
      await expect(authService.authenticate(mockCredentials)).rejects.toThrow('Invalid credentials');
      expect(mockAuditService.logFailedLogin).toHaveBeenCalledWith(
        mockCredentials.email,
        'Invalid credentials',
        undefined,
        undefined
      );
    });

    it('should include client info in audit logs when provided', async () => {
      // Arrange
      mockUserService.verifyCredentials.mockResolvedValue(mockUser);
      mockPermissionService.getAllPermissions.mockReturnValue(['projects:read']);
      mockJWTService.generateToken.mockReturnValue(mockToken);
      mockAuditService.logSuccessfulLogin.mockResolvedValue();

      const ipAddress = '192.168.1.1';
      const userAgent = 'Mozilla/5.0';

      // Act
      await authService.authenticate(mockCredentials, ipAddress, userAgent);

      // Assert
      expect(mockAuditService.logSuccessfulLogin).toHaveBeenCalledWith(
        mockUser.id,
        ipAddress,
        userAgent
      );
    });
  });

  describe('authorize', () => {
    beforeEach(() => {
      mockJWTService.isTokenExpired.mockReturnValue(false);
      mockUserService.getUserById.mockResolvedValue(mockUser);
    });

    it('should authorize user with valid permissions', async () => {
      // Arrange
      mockPermissionService.hasPermission.mockReturnValue(true);

      // Act
      const result = await authService.authorize(mockToken, 'projects', 'read');

      // Assert
      expect(result).toBe(true);
      expect(mockPermissionService.hasPermission).toHaveBeenCalledWith(
        mockUser.roles,
        'projects',
        'read'
      );
    });

    it('should deny authorization for insufficient permissions', async () => {
      // Arrange
      mockPermissionService.hasPermission.mockReturnValue(false);
      mockAuditService.logAuthorizationFailure.mockResolvedValue();

      // Act
      const result = await authService.authorize(mockToken, 'admin', 'delete');

      // Assert
      expect(result).toBe(false);
      expect(mockAuditService.logAuthorizationFailure).toHaveBeenCalledWith(
        mockToken.userId,
        'admin',
        'delete',
        undefined,
        undefined
      );
    });

    it('should deny authorization for expired tokens', async () => {
      // Arrange
      mockJWTService.isTokenExpired.mockReturnValue(true);
      mockAuditService.logAuthorizationFailure.mockResolvedValue();

      // Act
      const result = await authService.authorize(mockToken, 'projects', 'read');

      // Assert
      expect(result).toBe(false);
      expect(mockAuditService.logAuthorizationFailure).toHaveBeenCalledWith(
        mockToken.userId,
        'projects',
        'read',
        undefined,
        undefined
      );
    });

    it('should deny authorization for invalid sessions', async () => {
      // Arrange
      const mockRedisClient = {
        get: jest.fn().mockResolvedValue(null), // No session found
      };
      mockRedisService.getClient.mockReturnValue(mockRedisClient as any);
      mockAuditService.logAuthorizationFailure.mockResolvedValue();

      // Act
      const result = await authService.authorize(mockToken, 'projects', 'read');

      // Assert
      expect(result).toBe(false);
      expect(mockAuditService.logAuthorizationFailure).toHaveBeenCalled();
    });
  });

  describe('getUserRoles', () => {
    it('should return user roles successfully', async () => {
      // Arrange
      mockUserService.getUserById.mockResolvedValue(mockUser);

      // Act
      const result = await authService.getUserRoles('user_123');

      // Assert
      expect(result).toEqual(mockUser.roles);
      expect(mockUserService.getUserById).toHaveBeenCalledWith('user_123');
    });

    it('should throw error for non-existent user', async () => {
      // Arrange
      mockUserService.getUserById.mockResolvedValue(null);

      // Act & Assert
      await expect(authService.getUserRoles('nonexistent')).rejects.toThrow('User not found');
    });
  });

  describe('refreshToken', () => {
    it('should successfully refresh valid token', async () => {
      // Arrange
      mockJWTService.verifyRefreshToken.mockReturnValue({ userId: 'user_123' });
      mockUserService.getUserById.mockResolvedValue(mockUser);
      mockPermissionService.getAllPermissions.mockReturnValue(['projects:read']);
      mockJWTService.generateToken.mockReturnValue(mockToken);
      mockAuditService.logTokenRefresh.mockResolvedValue();

      // Act
      const result = await authService.refreshToken('refresh_token_123');

      // Assert
      expect(result).toEqual(mockToken);
      expect(mockJWTService.verifyRefreshToken).toHaveBeenCalledWith('refresh_token_123');
      expect(mockAuditService.logTokenRefresh).toHaveBeenCalledWith(
        'user_123',
        undefined,
        undefined
      );
    });

    it('should fail to refresh invalid token', async () => {
      // Arrange
      mockJWTService.verifyRefreshToken.mockImplementation(() => {
        throw new Error('Invalid refresh token');
      });

      // Act & Assert
      await expect(authService.refreshToken('invalid_token')).rejects.toThrow('Failed to refresh token');
    });
  });

  describe('revokeToken', () => {
    it('should successfully revoke token', async () => {
      // Arrange
      mockAuditService.logLogout.mockResolvedValue();

      // Act
      await authService.revokeToken(mockToken);

      // Assert
      expect(mockAuditService.logLogout).toHaveBeenCalledWith(
        mockToken.userId,
        undefined,
        undefined
      );
    });
  });

  describe('verifyAuthorizationHeader', () => {
    it('should verify valid authorization header', async () => {
      // Arrange
      const authHeader = 'Bearer valid_token';
      const mockPayload = {
        userId: 'user_123',
        roles: ['programmer'],
        permissions: ['projects:read'],
        exp: Math.floor(Date.now() / 1000) + 3600,
      };

      mockJWTService.extractTokenFromHeader.mockReturnValue('valid_token');
      mockJWTService.verifyToken.mockReturnValue(mockPayload);

      // Act
      const result = await authService.verifyAuthorizationHeader(authHeader);

      // Assert
      expect(result).toBeTruthy();
      expect(result?.userId).toBe('user_123');
      expect(result?.roles).toEqual(['programmer']);
    });

    it('should return null for invalid authorization header', async () => {
      // Arrange
      mockJWTService.extractTokenFromHeader.mockReturnValue(null);

      // Act
      const result = await authService.verifyAuthorizationHeader('invalid');

      // Assert
      expect(result).toBeNull();
    });

    it('should return null for expired token', async () => {
      // Arrange
      const authHeader = 'Bearer expired_token';
      mockJWTService.extractTokenFromHeader.mockReturnValue('expired_token');
      mockJWTService.verifyToken.mockImplementation(() => {
        throw new Error('Token expired');
      });

      // Act
      const result = await authService.verifyAuthorizationHeader(authHeader);

      // Assert
      expect(result).toBeNull();
    });
  });
});