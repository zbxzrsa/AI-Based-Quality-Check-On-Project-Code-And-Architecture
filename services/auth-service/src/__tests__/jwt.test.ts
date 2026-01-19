import jwt from 'jsonwebtoken';
import { JWTService } from '../utils/jwt';
import { config } from '../config';

// Mock the config
jest.mock('../config', () => ({
  config: {
    jwt: {
      secret: 'test-secret',
      expiresIn: '1h',
    },
  },
}));

describe('JWTService', () => {
  const mockUserId = 'user_123';
  const mockRoles = ['programmer'];
  const mockPermissions = ['projects:read', 'projects:create'];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('generateToken', () => {
    it('should generate a valid JWT token', () => {
      // Act
      const result = JWTService.generateToken(mockUserId, mockRoles, mockPermissions);

      // Assert
      expect(result.userId).toBe(mockUserId);
      expect(result.roles).toEqual(mockRoles);
      expect(result.permissions).toEqual(mockPermissions);
      expect(result.refreshToken).toBeTruthy();
      expect(result.expiresAt).toBeInstanceOf(Date);
      expect(result.expiresAt.getTime()).toBeGreaterThan(Date.now());
    });

    it('should create tokens with different refresh tokens', () => {
      // Act
      const token1 = JWTService.generateToken(mockUserId, mockRoles, mockPermissions);
      const token2 = JWTService.generateToken(mockUserId, mockRoles, mockPermissions);

      // Assert
      expect(token1.refreshToken).not.toBe(token2.refreshToken);
    });

    it('should set expiration time correctly', () => {
      // Act
      const result = JWTService.generateToken(mockUserId, mockRoles, mockPermissions);

      // Assert
      const expectedExpiration = Date.now() + (60 * 60 * 1000); // 1 hour
      const actualExpiration = result.expiresAt.getTime();
      const timeDifference = Math.abs(actualExpiration - expectedExpiration);
      
      // Allow 5 second tolerance for test execution time
      expect(timeDifference).toBeLessThan(5000);
    });
  });

  describe('verifyToken', () => {
    it('should verify a valid token', () => {
      // Arrange
      const token = jwt.sign(
        {
          userId: mockUserId,
          roles: mockRoles,
          permissions: mockPermissions,
        },
        config.jwt.secret,
        { expiresIn: '1h' }
      );

      // Act
      const result = JWTService.verifyToken(token);

      // Assert
      expect(result.userId).toBe(mockUserId);
      expect(result.roles).toEqual(mockRoles);
      expect(result.permissions).toEqual(mockPermissions);
      expect(result.exp).toBeTruthy();
      expect(result.iat).toBeTruthy();
    });

    it('should throw error for invalid token', () => {
      // Act & Assert
      expect(() => JWTService.verifyToken('invalid_token')).toThrow('Invalid or expired token');
    });

    it('should throw error for expired token', () => {
      // Arrange
      const expiredToken = jwt.sign(
        { userId: mockUserId },
        config.jwt.secret,
        { expiresIn: '-1h' } // Expired 1 hour ago
      );

      // Act & Assert
      expect(() => JWTService.verifyToken(expiredToken)).toThrow('Invalid or expired token');
    });

    it('should throw error for token with wrong secret', () => {
      // Arrange
      const tokenWithWrongSecret = jwt.sign(
        { userId: mockUserId },
        'wrong-secret',
        { expiresIn: '1h' }
      );

      // Act & Assert
      expect(() => JWTService.verifyToken(tokenWithWrongSecret)).toThrow('Invalid or expired token');
    });
  });

  describe('verifyRefreshToken', () => {
    it('should verify a valid refresh token', () => {
      // Arrange
      const refreshToken = jwt.sign(
        { userId: mockUserId, type: 'refresh' },
        config.jwt.secret,
        { expiresIn: '7d' }
      );

      // Act
      const result = JWTService.verifyRefreshToken(refreshToken);

      // Assert
      expect(result.userId).toBe(mockUserId);
    });

    it('should throw error for non-refresh token', () => {
      // Arrange
      const regularToken = jwt.sign(
        { userId: mockUserId, type: 'access' },
        config.jwt.secret,
        { expiresIn: '1h' }
      );

      // Act & Assert
      expect(() => JWTService.verifyRefreshToken(regularToken)).toThrow('Invalid refresh token type');
    });

    it('should throw error for invalid refresh token', () => {
      // Act & Assert
      expect(() => JWTService.verifyRefreshToken('invalid_refresh_token')).toThrow('Invalid or expired refresh token');
    });
  });

  describe('extractTokenFromHeader', () => {
    it('should extract token from valid Bearer header', () => {
      // Arrange
      const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9';
      const authHeader = `Bearer ${token}`;

      // Act
      const result = JWTService.extractTokenFromHeader(authHeader);

      // Assert
      expect(result).toBe(token);
    });

    it('should return null for missing header', () => {
      // Act
      const result = JWTService.extractTokenFromHeader(undefined);

      // Assert
      expect(result).toBeNull();
    });

    it('should return null for invalid header format', () => {
      // Act
      const result = JWTService.extractTokenFromHeader('Invalid header');

      // Assert
      expect(result).toBeNull();
    });

    it('should return null for header without Bearer prefix', () => {
      // Act
      const result = JWTService.extractTokenFromHeader('token123');

      // Assert
      expect(result).toBeNull();
    });
  });

  describe('isTokenExpired', () => {
    it('should return false for non-expired token', () => {
      // Arrange
      const futureDate = new Date(Date.now() + 60 * 60 * 1000); // 1 hour from now
      const token = JWTService.generateToken(mockUserId, mockRoles, mockPermissions);
      token.expiresAt = futureDate;

      // Act
      const result = JWTService.isTokenExpired(token);

      // Assert
      expect(result).toBe(false);
    });

    it('should return true for expired token', () => {
      // Arrange
      const pastDate = new Date(Date.now() - 60 * 60 * 1000); // 1 hour ago
      const token = JWTService.generateToken(mockUserId, mockRoles, mockPermissions);
      token.expiresAt = pastDate;

      // Act
      const result = JWTService.isTokenExpired(token);

      // Assert
      expect(result).toBe(true);
    });

    it('should return true for token expiring exactly now', () => {
      // Arrange
      const now = new Date();
      const token = JWTService.generateToken(mockUserId, mockRoles, mockPermissions);
      token.expiresAt = new Date(now.getTime() - 1); // 1ms in the past

      // Act
      const result = JWTService.isTokenExpired(token);

      // Assert
      expect(result).toBe(true);
    });
  });
});