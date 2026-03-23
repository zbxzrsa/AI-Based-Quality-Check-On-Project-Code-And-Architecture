/**
 * Unified Logger Utility
 * 
 * Provides structured logging with module prefixes and environment-aware output.
 * Replaces scattered console.log/error/warn calls throughout the codebase.
 * 
 * @example
 * const logger = createLogger('AuthContext');
 * logger.debug('User logged in', { userId: 123 });
 * logger.error('Login failed', error);
 */

export interface Logger {
  debug: (message: string, data?: Record<string, unknown>) => void;
  info: (message: string, data?: Record<string, unknown>) => void;
  warn: (message: string, data?: Record<string, unknown>) => void;
  error: (message: string, error?: Error | unknown) => void;
}

interface LogData {
  module: string;
  message: string;
  data?: Record<string, unknown>;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
}

class LoggerImpl implements Logger {
  private readonly module: string;
  private readonly isDevelopment: boolean;

  constructor(module: string) {
    this.module = module;
    this.isDevelopment = process.env.NODE_ENV === 'development';
  }

  private formatData(data?: Record<string, unknown>): Record<string, unknown> | undefined {
    if (!data) return undefined;
    
    const sanitized: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data)) {
      if (key.toLowerCase().includes('password') || 
          key.toLowerCase().includes('token') ||
          key.toLowerCase().includes('secret')) {
        sanitized[key] = '[REDACTED]';
      } else {
        sanitized[key] = value;
      }
    }
    return sanitized;
  }

  private log(level: LogData['level'], message: string, data?: Record<string, unknown>): void {
    const logData: LogData = {
      module: this.module,
      message,
      data: this.formatData(data),
      timestamp: new Date().toISOString(),
      level,
    };

    const prefix = `[${this.module}]`;
    const formattedMessage = `${prefix} ${message}`;

    switch (level) {
      case 'debug':
        if (this.isDevelopment) {
          console.log(formattedMessage, data || '');
        }
        break;
      case 'info':
        console.log(formattedMessage, data || '');
        break;
      case 'warn':
        console.warn(formattedMessage, data || '');
        break;
      case 'error':
        console.error(formattedMessage, data || '');
        break;
    }
  }

  debug(message: string, data?: Record<string, unknown>): void {
    this.log('debug', message, data);
  }

  info(message: string, data?: Record<string, unknown>): void {
    this.log('info', message, data);
  }

  warn(message: string, data?: Record<string, unknown>): void {
    this.log('warn', message, data);
  }

  error(message: string, error?: Error | unknown): void {
    const errorData: Record<string, unknown> = {};
    
    if (error instanceof Error) {
      errorData.error = error.message;
      errorData.stack = error.stack;
    } else if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, unknown>;
      if ('response' in errorObj) {
        const response = errorObj.response as Record<string, unknown>;
        errorData.status = response?.status;
        errorData.data = response?.data;
      }
      if ('message' in errorObj) {
        errorData.error = errorObj.message;
      }
    }
    
    this.log('error', message, errorData);
  }
}

/**
 * Create a logger instance with a module prefix
 * 
 * @param module - Module name to prefix all log messages
 * @returns Logger instance
 * 
 * @example
 * const logger = createLogger('ApiClient');
 * logger.debug('Request started', { url: '/api/users' });
 * logger.error('Request failed', error);
 */
export function createLogger(module: string): Logger {
  return new LoggerImpl(module);
}

export default createLogger;
