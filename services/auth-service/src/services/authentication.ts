import { AuthenticationService as IAuthenticationService } from '@shared/interfaces';
import { AuthToken, Credentials, Role } from '@shared/types';
import { UserService } from './user';
import { PermissionService } from './permissions';
import { AuditService } from './audit';
import { JWTService } from '../utils/jwt';
import { RedisService } from './redis';
import { logger } from '../utils/logger';

export class AuthenticationService implements IAuthenticationService {
  /**
   * Authenticate user with email and password
   */
  async authenticate(credentials: Credentials, ipAddress?: string, userAgent?: string): Promise<AuthToken> {
    logger.info('Authentication attempt for:', credentials.email);

    try {
      // Verify user credentials
      const user = await UserService.verifyCredentials(credentials.email, credentials.password);
      if (!user) {
        logger.warn('Authentication failed for:', credentials.email);
        await AuditService.logFailedLogin(credentials.email, 'Invalid credentials', ipAddress, userAgent);
        throw new Error('Invalid credentials');
      }

      // Get user permissions
      const permissions = PermissionService.getAllPermissions(user.roles);
      const roleNames = user.roles.map(role => role.name);

      // Generate JWT token
      const authToken = JWTService.generateToken(user.id, roleNames, permissions);

      // Store token in Redis for session management
      await this.storeTokenSession(authToken);

      // Log successful authentication
      await AuditService.logSuccessfulLogin(user.id, ipAddress, userAgent);

      logger.info('Authentication successful for user:', user.id);
      return authToken;
    } catch (error) {
      logger.error('Authentication error:', error);
      throw error;
    }
  }

  /**
   * Authorize user access to a resource with specific action
   */
  async authorize(token: AuthToken, resource: string, action: string, ipAddress?: string, userAgent?: string): Promise<boolean> {
    logger.debug('Authorization check for:', { userId: token.userId, resource, action });

    try {
      // Check if token is expired
      if (JWTService.isTokenExpired(token)) {
        logger.warn('Authorization failed - token expired for user:', token.userId);
        await AuditService.logAuthorizationFailure(token.userId, resource, action, ipAddress, userAgent);
        return false;
      }

      // Check if token session exists in Redis
      const sessionExists = await this.verifyTokenSession(token);
      if (!sessionExists) {
        logger.warn('Authorization failed - invalid session for user:', token.userId);
        await AuditService.logAuthorizationFailure(token.userId, resource, action, ipAddress, userAgent);
        return false;
      }

      // Get user roles
      const userRoles = await this.getUserRoles(token.userId);

      // Check permissions
      const hasPermission = PermissionService.hasPermission(userRoles, resource, action);

      if (hasPermission) {
        logger.debug('Authorization granted for user:', token.userId);
      } else {
        logger.warn('Authorization denied for user:', token.userId);
        await AuditService.logAuthorizationFailure(token.userId, resource, action, ipAddress, userAgent);
      }

      return hasPermission;
    } catch (error) {
      logger.error('Authorization error:', error);
      await AuditService.logAuthorizationFailure(token.userId, resource, action, ipAddress, userAgent);
      return false;
    }
  }

  /**
   * Get user roles by user ID
   */
  async getUserRoles(userId: string): Promise<Role[]> {
    logger.debug('Getting roles for user:', userId);

    try {
      const user = await UserService.getUserById(userId);
      if (!user) {
        logger.warn('User not found:', userId);
        throw new Error('User not found');
      }

      return user.roles;
    } catch (error) {
      logger.error('Error getting user roles:', error);
      throw error;
    }
  }

  /**
   * Refresh an expired token using refresh token
   */
  async refreshToken(refreshToken: string, ipAddress?: string, userAgent?: string): Promise<AuthToken> {
    logger.info('Token refresh requested');

    try {
      // Verify refresh token
      const { userId } = JWTService.verifyRefreshToken(refreshToken);

      // Get user data
      const user = await UserService.getUserById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      // Generate new token
      const permissions = PermissionService.getAllPermissions(user.roles);
      const roleNames = user.roles.map(role => role.name);
      const newToken = JWTService.generateToken(user.id, roleNames, permissions);

      // Store new token session
      await this.storeTokenSession(newToken);

      // Revoke old refresh token (if it exists in our session store)
      await this.revokeRefreshToken(refreshToken);

      // Log token refresh
      await AuditService.logTokenRefresh(userId, ipAddress, userAgent);

      logger.info('Token refreshed successfully for user:', userId);
      return newToken;
    } catch (error) {
      logger.error('Token refresh error:', error);
      throw new Error('Failed to refresh token');
    }
  }

  /**
   * Revoke a token (logout)
   */
  async revokeToken(token: AuthToken, ipAddress?: string, userAgent?: string): Promise<void> {
    logger.info('Token revocation requested for user:', token.userId);

    try {
      // Remove token session from Redis
      await this.removeTokenSession(token);

      // Revoke refresh token
      await this.revokeRefreshToken(token.refreshToken);

      // Log logout
      await AuditService.logLogout(token.userId, ipAddress, userAgent);

      logger.info('Token revoked successfully for user:', token.userId);
    } catch (error) {
      logger.error('Token revocation error:', error);
      throw new Error('Failed to revoke token');
    }
  }

  /**
   * Verify token from Authorization header
   */
  async verifyAuthorizationHeader(authHeader: string | undefined): Promise<AuthToken | null> {
    if (!authHeader) {
      return null;
    }

    const tokenString = JWTService.extractTokenFromHeader(authHeader);
    if (!tokenString) {
      return null;
    }

    try {
      const payload = JWTService.verifyToken(tokenString);
      
      // Reconstruct AuthToken from JWT payload
      const authToken: AuthToken = {
        userId: payload.userId,
        roles: payload.roles,
        permissions: payload.permissions,
        expiresAt: new Date(payload.exp! * 1000),
        refreshToken: '', // We don't store refresh token in JWT
      };

      // Verify session exists
      const sessionExists = await this.verifyTokenSession(authToken);
      if (!sessionExists) {
        return null;
      }

      return authToken;
    } catch (error) {
      logger.debug('Token verification failed:', error);
      return null;
    }
  }

  /**
   * Store token session in Redis
   */
  private async storeTokenSession(token: AuthToken): Promise<void> {
    try {
      const redis = RedisService.getClient();
      const sessionKey = `session:${token.userId}`;
      const sessionData = {
        userId: token.userId,
        roles: token.roles,
        permissions: token.permissions,
        expiresAt: token.expiresAt.toISOString(),
      };

      // Store session with expiration
      const ttl = Math.floor((token.expiresAt.getTime() - Date.now()) / 1000);
      await redis.setEx(sessionKey, ttl, JSON.stringify(sessionData));

      // Store refresh token mapping
      const refreshKey = `refresh:${token.refreshToken}`;
      await redis.setEx(refreshKey, 7 * 24 * 60 * 60, token.userId); // 7 days
    } catch (error) {
      logger.error('Failed to store token session:', error);
      throw new Error('Failed to store session');
    }
  }

  /**
   * Verify token session exists in Redis
   */
  private async verifyTokenSession(token: AuthToken): Promise<boolean> {
    try {
      const redis = RedisService.getClient();
      const sessionKey = `session:${token.userId}`;
      const sessionData = await redis.get(sessionKey);
      return sessionData !== null;
    } catch (error) {
      logger.error('Failed to verify token session:', error);
      return false;
    }
  }

  /**
   * Remove token session from Redis
   */
  private async removeTokenSession(token: AuthToken): Promise<void> {
    try {
      const redis = RedisService.getClient();
      const sessionKey = `session:${token.userId}`;
      await redis.del(sessionKey);
    } catch (error) {
      logger.error('Failed to remove token session:', error);
      throw new Error('Failed to remove session');
    }
  }

  /**
   * Revoke refresh token
   */
  private async revokeRefreshToken(refreshToken: string): Promise<void> {
    try {
      const redis = RedisService.getClient();
      const refreshKey = `refresh:${refreshToken}`;
      await redis.del(refreshKey);
    } catch (error) {
      logger.error('Failed to revoke refresh token:', error);
      // Don't throw error for this non-critical operation
    }
  }
}