import { Request, Response, NextFunction } from 'express';
import { AuthenticationService } from '../services/authentication';
import { logger } from '../utils/logger';

// Extend Express Request to include auth context
declare global {
  namespace Express {
    interface Request {
      auth?: {
        userId: string;
        roles: string[];
        permissions: string[];
      };
    }
  }
}

/**
 * Middleware to authenticate requests using JWT tokens
 */
export const authenticateToken = async (
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    const authService = new AuthenticationService();
    const authHeader = req.headers.authorization;

    const token = await authService.verifyAuthorizationHeader(authHeader);
    if (!token) {
      res.status(401).json({
        error: 'Unauthorized',
        message: 'Valid authentication token required',
      });
      return;
    }

    // Add auth context to request
    req.auth = {
      userId: token.userId,
      roles: token.roles,
      permissions: token.permissions,
    };

    next();
  } catch (error) {
    logger.error('Authentication middleware error:', error);
    res.status(401).json({
      error: 'Unauthorized',
      message: 'Invalid or expired token',
    });
  }
};

/**
 * Middleware to check if user has required role
 */
export const requireRole = (requiredRoles: string[]) => {
  return (req: Request, res: Response, next: NextFunction): void => {
    if (!req.auth) {
      res.status(401).json({
        error: 'Unauthorized',
        message: 'Authentication required',
      });
      return;
    }

    const hasRequiredRole = requiredRoles.some(role => 
      req.auth!.roles.includes(role)
    );

    if (!hasRequiredRole) {
      res.status(403).json({
        error: 'Forbidden',
        message: `Required role: ${requiredRoles.join(' or ')}`,
      });
      return;
    }

    next();
  };
};

/**
 * Middleware to check if user has required permission
 */
export const requirePermission = (resource: string, action: string) => {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    if (!req.auth) {
      res.status(401).json({
        error: 'Unauthorized',
        message: 'Authentication required',
      });
      return;
    }

    try {
      const authService = new AuthenticationService();
      const token = {
        userId: req.auth.userId,
        roles: req.auth.roles,
        permissions: req.auth.permissions,
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // Placeholder
        refreshToken: '', // Placeholder
      };

      const hasPermission = await authService.authorize(
        token,
        resource,
        action,
        req.ip,
        req.get('User-Agent')
      );

      if (!hasPermission) {
        res.status(403).json({
          error: 'Forbidden',
          message: `Insufficient permissions for ${action} on ${resource}`,
        });
        return;
      }

      next();
    } catch (error) {
      logger.error('Permission check error:', error);
      res.status(500).json({
        error: 'Internal Server Error',
        message: 'Failed to check permissions',
      });
    }
  };
};

/**
 * Middleware to check if user is administrator
 */
export const requireAdmin = requireRole(['administrator']);

/**
 * Optional authentication middleware - doesn't fail if no token provided
 */
export const optionalAuth = async (
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    const authService = new AuthenticationService();
    const authHeader = req.headers.authorization;

    if (authHeader) {
      const token = await authService.verifyAuthorizationHeader(authHeader);
      if (token) {
        req.auth = {
          userId: token.userId,
          roles: token.roles,
          permissions: token.permissions,
        };
      }
    }

    next();
  } catch (error) {
    logger.debug('Optional auth failed:', error);
    // Continue without authentication
    next();
  }
};

/**
 * Middleware to extract client information for audit logging
 */
export const extractClientInfo = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  // Add client info to request for audit logging
  (req as any).clientInfo = {
    ipAddress: req.ip,
    userAgent: req.get('User-Agent'),
    timestamp: new Date(),
  };

  next();
};