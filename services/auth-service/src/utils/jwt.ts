import jwt from 'jsonwebtoken';
import { AuthToken } from '@shared/types';
import { config } from '../config';
import { logger } from './logger';

export interface JWTPayload {
  userId: string;
  roles: string[];
  permissions: string[];
  iat?: number;
  exp?: number;
}

export class JWTService {
  /**
   * Generate a JWT token for a user
   */
  static generateToken(userId: string, roles: string[], permissions: string[]): AuthToken {
    const payload: JWTPayload = {
      userId,
      roles,
      permissions,
    };

    const accessToken = jwt.sign(payload, config.jwt.secret, {
      expiresIn: config.jwt.expiresIn,
    } as jwt.SignOptions);

    // Generate refresh token with longer expiration and unique identifier
    const refreshToken = jwt.sign(
      { userId, type: 'refresh', nonce: Math.random().toString(36) },
      config.jwt.secret,
      { expiresIn: '7d' } as jwt.SignOptions
    );

    // Calculate expiration date
    const decoded = jwt.decode(accessToken) as jwt.JwtPayload;
    const expiresAt = new Date(decoded.exp! * 1000);

    logger.info('JWT token generated for user:', userId);

    return {
      userId,
      roles,
      permissions,
      expiresAt,
      refreshToken,
    };
  }

  /**
   * Verify and decode a JWT token
   */
  static verifyToken(token: string): JWTPayload {
    try {
      const decoded = jwt.verify(token, config.jwt.secret) as JWTPayload;
      return decoded;
    } catch (error) {
      logger.warn('JWT token verification failed:', error);
      throw new Error('Invalid or expired token');
    }
  }

  /**
   * Verify a refresh token
   */
  static verifyRefreshToken(refreshToken: string): { userId: string } {
    try {
      const decoded = jwt.verify(refreshToken, config.jwt.secret) as any;
      if (decoded.type !== 'refresh') {
        throw new Error('Invalid refresh token type');
      }
      return { userId: decoded.userId };
    } catch (error) {
      if (error instanceof Error && error.message === 'Invalid refresh token type') {
        throw error;
      }
      logger.warn('Refresh token verification failed:', error);
      throw new Error('Invalid or expired refresh token');
    }
  }

  /**
   * Extract token from Authorization header
   */
  static extractTokenFromHeader(authHeader: string | undefined): string | null {
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return null;
    }
    return authHeader.substring(7);
  }

  /**
   * Check if a token is expired
   */
  static isTokenExpired(token: AuthToken): boolean {
    return new Date() > token.expiresAt;
  }
}