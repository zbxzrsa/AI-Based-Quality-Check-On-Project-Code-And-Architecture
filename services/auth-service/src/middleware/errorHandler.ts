import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger';

export interface AuthError extends Error {
  statusCode?: number;
  code?: string;
  retryable?: boolean;
}

export const errorHandler = (
  error: AuthError,
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  logger.error('Auth Service Error:', {
    error: error.message,
    stack: error.stack,
    url: req.url,
    method: req.method,
    ip: req.ip,
  });

  const statusCode = error.statusCode || 500;
  const code = error.code || 'INTERNAL_ERROR';
  const retryable = error.retryable || false;

  res.status(statusCode).json({
    error: {
      code,
      message: error.message,
      retryable,
      timestamp: new Date().toISOString(),
      path: req.path,
    },
  });
};