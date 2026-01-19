import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import axios from 'axios';
import { config } from '../config';
import { logger } from '../utils/logger';
import { AuthContext } from '@shared/types';

interface AuthenticatedRequest extends Request {
  auth?: AuthContext;
}

export const authMiddleware = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).json({ error: 'Missing or invalid authorization header' });
      return;
    }

    const token = authHeader.substring(7);
    
    // Verify JWT token
    const decoded = jwt.verify(token, config.jwt.secret) as any;
    
    // Validate token with auth service
    const authResponse = await axios.post(
      `${config.services.authService}/api/auth/validate`,
      { token },
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 5000,
      }
    );

    if (!authResponse.data.valid) {
      res.status(401).json({ error: 'Invalid token' });
      return;
    }

    // Set auth context
    req.auth = {
      userId: decoded.userId,
      roles: decoded.roles || [],
      permissions: decoded.permissions || [],
    };

    next();
  } catch (error) {
    logger.error('Authentication error:', error);
    
    if (error instanceof jwt.JsonWebTokenError) {
      res.status(401).json({ error: 'Invalid token' });
      return;
    }
    
    if (axios.isAxiosError(error)) {
      logger.error('Auth service communication error:', error.message);
      res.status(503).json({ error: 'Authentication service unavailable' });
      return;
    }
    
    res.status(500).json({ error: 'Internal server error' });
  }
};
