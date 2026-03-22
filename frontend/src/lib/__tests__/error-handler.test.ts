/**
 * Unit tests for Error Handler
 * 
 * Tests error type identification, user messages, retry logic, and error reporting
 * Requirements: 4.2, 4.3, 4.5, 7.4
 */

import { AxiosError } from 'axios';
import {
  ErrorHandler,
  ErrorType,
  ErrorInfo,
  handleError,
  getUserMessage,
  shouldRetry,
  logError,
  reportToBackend,
} from '../error-handler';
import { ApiError } from '../api-client';

// Mock fetch for backend reporting tests
global.fetch = jest.fn();

describe('ErrorHandler', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('handleError', () => {
    it('should handle network errors', () => {
      const axiosError: Partial<AxiosError> = {
        message: 'Network Error',
        code: 'ECONNREFUSED',
        isAxiosError: true,
        config: {} as any,
        toJSON: () => ({}),
        name: 'AxiosError',
      };

      const errorInfo = ErrorHandler.handleError(axiosError);

      expect(errorInfo.type).toBe(ErrorType.NETWORK_ERROR);
      expect(errorInfo.retryable).toBe(true);
      expect(errorInfo.userMessage).toContain('connect to the server');
    });

    it('should handle timeout errors', () => {
      const axiosError: Partial<AxiosError> = {
        message: 'Timeout',
        code: 'ECONNABORTED',
        isAxiosError: true,
        config: {} as any,
        toJSON: () => ({}),
        name: 'AxiosError',
      };

      const errorInfo = ErrorHandler.handleError(axiosError);

      expect(errorInfo.type).toBe(ErrorType.TIMEOUT_ERROR);
      expect(errorInfo.retryable).toBe(true);
      expect(errorInfo.userMessage).toContain('took too long');
    });

    it('should handle authentication errors (401)', () => {
      const axiosError: Partial<AxiosError> = {
        message: 'Unauthorized',
        response: {
          status: 401,
          data: { detail: 'Invalid token' },
        } as any,
        isAxiosError: true,
        config: {} as any,
        toJSON: () => ({}),
        name: 'AxiosError',
      };

      const errorInfo = ErrorHandler.handleError(axiosError);

      expect(errorInfo.type).toBe(ErrorType.AUTH_ERROR);
      expect(errorInfo.retryable).toBe(false);
      expect(errorInfo.statusCode).toBe(401);
      expect(errorInfo.userMessage).toContain('session has expired');
    });

    it('should handle authorization errors (403)', () => {
      const axiosError: Partial<AxiosError> = {
        message: 'Forbidden',
        response: {
          status: 403,
          data: { detail: 'Insufficient permissions' },
        } as any,
        isAxiosError: true,
        config: {} as any,
        toJSON: () => ({}),
        name: 'AxiosError',
      };

      const errorInfo = ErrorHandler.handleError(axiosError);

      expect(errorInfo.type).toBe(ErrorType.PERMISSION_ERROR);
      expect(errorInfo.retryable).toBe(false);
      expect(errorInfo.statusCode).toBe(403);
      expect(errorInfo.userMessage).toContain('do not have permission');
    });

    it('should handle validation errors (422)', () => {
      const axiosError: Partial<AxiosError> = {
        message: 'Validation Error',
        response: {
          status: 422,
          data: { detail: 'Invalid input' },
        } as any,
        isAxiosError: true,
        config: {} as any,
        toJSON: () => ({}),
        name: 'AxiosError',
      };

      const errorInfo = ErrorHandler.handleError(axiosError);

      expect(errorInfo.type).toBe(ErrorType.VALIDATION_ERROR);
      expect(errorInfo.retryable).toBe(false);
      expect(errorInfo.statusCode).toBe(422);
      expect(errorInfo.userMessage).toContain('invalid');
    });

    it('should handle server errors (500)', () => {
      const axiosError: Partial<AxiosError> = {
        message: 'Internal Server Error',
        response: {
          status: 500,
          data: { detail: 'Server error' },
        } as any,
        isAxiosError: true,
        config: {} as any,
        toJSON: () => ({}),
        name: 'AxiosError',
      };

      const errorInfo = ErrorHandler.handleError(axiosError);

      expect(errorInfo.type).toBe(ErrorType.SERVER_ERROR);
      expect(errorInfo.retryable).toBe(true);
      expect(errorInfo.statusCode).toBe(500);
      expect(errorInfo.userMessage).toContain('server encountered an error');
    });

    it('should handle rate limit errors (429)', () => {
      const axiosError: Partial<AxiosError> = {
        message: 'Too Many Requests',
        response: {
          status: 429,
          data: { detail: 'Rate limit exceeded' },
        } as any,
        isAxiosError: true,
        config: {} as any,
        toJSON: () => ({}),
        name: 'AxiosError',
      };

      const errorInfo = ErrorHandler.handleError(axiosError);

      expect(errorInfo.type).toBe(ErrorType.RATE_LIMIT_ERROR);
      expect(errorInfo.retryable).toBe(true);
      expect(errorInfo.statusCode).toBe(429);
      expect(errorInfo.userMessage).toContain('Too many requests');
    });

    it('should handle ApiError from API client', () => {
      const apiError: ApiError = {
        message: 'API Error',
        code: 'API_ERROR',
        status: 500,
        details: { error: 'Something went wrong' },
      };

      const errorInfo = ErrorHandler.handleError(apiError);

      expect(errorInfo.type).toBe(ErrorType.SERVER_ERROR);
      expect(errorInfo.statusCode).toBe(500);
      expect(errorInfo.details).toEqual(apiError.details);
    });

    it('should handle standard Error objects', () => {
      const error = new Error('Standard error');

      const errorInfo = ErrorHandler.handleError(error);

      expect(errorInfo.type).toBe(ErrorType.UNKNOWN_ERROR);
      expect(errorInfo.message).toBe('Standard error');
      expect(errorInfo.retryable).toBe(false);
    });

    it('should handle unknown error types', () => {
      const error = 'String error';

      const errorInfo = ErrorHandler.handleError(error);

      expect(errorInfo.type).toBe(ErrorType.UNKNOWN_ERROR);
      expect(errorInfo.message).toBe('String error');
      expect(errorInfo.retryable).toBe(false);
    });

    it('should include timestamp in error info', () => {
      const error = new Error('Test error');
      const beforeTime = new Date().toISOString();

      const errorInfo = ErrorHandler.handleError(error);

      const afterTime = new Date().toISOString();
      expect(errorInfo.timestamp).toBeDefined();
      expect(errorInfo.timestamp >= beforeTime).toBe(true);
      expect(errorInfo.timestamp <= afterTime).toBe(true);
    });
  });

  describe('getUserMessage', () => {
    it('should return appropriate message for each error type', () => {
      const errorTypes = [
        { type: ErrorType.NETWORK_ERROR, keyword: 'connect' },
        { type: ErrorType.TIMEOUT_ERROR, keyword: 'too long' },
        { type: ErrorType.AUTH_ERROR, keyword: 'session' },
        { type: ErrorType.PERMISSION_ERROR, keyword: 'permission' },
        { type: ErrorType.VALIDATION_ERROR, keyword: 'invalid' },
        { type: ErrorType.SERVER_ERROR, keyword: 'server' },
        { type: ErrorType.RATE_LIMIT_ERROR, keyword: 'many requests' },
        { type: ErrorType.UNKNOWN_ERROR, keyword: 'unexpected' },
      ];

      errorTypes.forEach(({ type, keyword }) => {
        const errorInfo: ErrorInfo = {
          type,
          message: 'Test',
          userMessage: '',
          retryable: false,
          timestamp: new Date().toISOString(),
        };

        const message = ErrorHandler.getUserMessage(errorInfo);
        expect(message.toLowerCase()).toContain(keyword.toLowerCase());
      });
    });
  });

  describe('shouldRetry', () => {
    it('should return true for retryable errors', () => {
      const retryableTypes = [
        ErrorType.NETWORK_ERROR,
        ErrorType.TIMEOUT_ERROR,
        ErrorType.SERVER_ERROR,
        ErrorType.RATE_LIMIT_ERROR,
      ];

      retryableTypes.forEach((type) => {
        const errorInfo: ErrorInfo = {
          type,
          message: 'Test',
          userMessage: '',
          retryable: false,
          timestamp: new Date().toISOString(),
        };

        expect(ErrorHandler.shouldRetry(errorInfo)).toBe(true);
      });
    });

    it('should return false for non-retryable errors', () => {
      const nonRetryableTypes = [
        ErrorType.AUTH_ERROR,
        ErrorType.PERMISSION_ERROR,
        ErrorType.VALIDATION_ERROR,
        ErrorType.UNKNOWN_ERROR,
      ];

      nonRetryableTypes.forEach((type) => {
        const errorInfo: ErrorInfo = {
          type,
          message: 'Test',
          userMessage: '',
          retryable: false,
          timestamp: new Date().toISOString(),
        };

        expect(ErrorHandler.shouldRetry(errorInfo)).toBe(false);
      });
    });
  });

  describe('logError', () => {
    it('should log error to console in development', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const errorInfo: ErrorInfo = {
        type: ErrorType.NETWORK_ERROR,
        message: 'Test error',
        userMessage: 'User message',
        retryable: true,
        timestamp: new Date().toISOString(),
      };

      ErrorHandler.logError(errorInfo);

      expect(console.error).toHaveBeenCalled();

      process.env.NODE_ENV = originalEnv;
    });

    it('should log structured JSON in production', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      const errorInfo: ErrorInfo = {
        type: ErrorType.SERVER_ERROR,
        message: 'Server error',
        userMessage: 'User message',
        retryable: true,
        statusCode: 500,
        timestamp: new Date().toISOString(),
      };

      ErrorHandler.logError(errorInfo);

      expect(console.error).toHaveBeenCalled();
      const logCall = (console.error as jest.Mock).mock.calls[0][0];
      
      // Should be valid JSON
      expect(() => JSON.parse(logCall)).not.toThrow();

      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('reportToBackend', () => {
    beforeEach(() => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 200,
      });
    });

    it('should send error report to backend', async () => {
      const errorInfo: ErrorInfo = {
        type: ErrorType.NETWORK_ERROR,
        message: 'Network error',
        userMessage: 'User message',
        retryable: true,
        statusCode: undefined,
        timestamp: new Date().toISOString(),
        details: { test: 'data' },
      };

      await ErrorHandler.reportToBackend(errorInfo);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/errors/client'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: expect.any(String),
        })
      );

      const callArgs = (global.fetch as jest.Mock).mock.calls[0];
      const payload = JSON.parse(callArgs[1].body);

      expect(payload.type).toBe(ErrorType.NETWORK_ERROR);
      expect(payload.message).toBe('Network error');
      expect(payload.timestamp).toBe(errorInfo.timestamp);
    });

    it('should handle backend reporting failure gracefully', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const errorInfo: ErrorInfo = {
        type: ErrorType.SERVER_ERROR,
        message: 'Server error',
        userMessage: 'User message',
        retryable: true,
        timestamp: new Date().toISOString(),
      };

      // Should not throw
      await expect(ErrorHandler.reportToBackend(errorInfo)).resolves.not.toThrow();

      expect(console.warn).toHaveBeenCalledWith(
        expect.stringContaining('Failed to report error to backend'),
        expect.any(Error)
      );
    });
  });

  describe('handleErrorComplete', () => {
    it('should handle, log, and report error in production', async () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      (global.fetch as jest.Mock).mockResolvedValue({ ok: true });

      const error = new Error('Test error');
      const errorInfo = await ErrorHandler.handleErrorComplete(error);

      expect(errorInfo.type).toBe(ErrorType.UNKNOWN_ERROR);
      expect(console.error).toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalled();

      process.env.NODE_ENV = originalEnv;
    });

    it('should not report to backend in development', async () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const error = new Error('Test error');
      await ErrorHandler.handleErrorComplete(error);

      expect(global.fetch).not.toHaveBeenCalled();

      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('createRetryHandler', () => {
    it('should retry retryable errors', async () => {
      let attempts = 0;
      const fn = jest.fn(async () => {
        attempts++;
        if (attempts < 3) {
          const error: Partial<AxiosError> = {
            message: 'Network Error',
            code: 'ECONNREFUSED',
            isAxiosError: true,
            config: {} as any,
            toJSON: () => ({}),
            name: 'AxiosError',
          };
          throw error;
        }
        return 'success';
      });

      const retryHandler = ErrorHandler.createRetryHandler(fn, 3, 100);
      const result = await retryHandler();

      expect(result).toBe('success');
      expect(fn).toHaveBeenCalledTimes(3);
    });

    it('should not retry non-retryable errors', async () => {
      const fn = jest.fn(async () => {
        const error: Partial<AxiosError> = {
          message: 'Unauthorized',
          response: { status: 401 } as any,
          isAxiosError: true,
          config: {} as any,
          toJSON: () => ({}),
          name: 'AxiosError',
        };
        throw error;
      });

      const retryHandler = ErrorHandler.createRetryHandler(fn, 3, 100);

      try {
        await retryHandler();
        fail('Should have thrown an error');
      } catch (error) {
        // Expected to throw
        expect(error).toBeDefined();
      }
      
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should throw after max retries', async () => {
      const fn = jest.fn(async () => {
        const error: Partial<AxiosError> = {
          message: 'Network Error',
          code: 'ECONNREFUSED',
          isAxiosError: true,
          config: {} as any,
          toJSON: () => ({}),
          name: 'AxiosError',
        };
        throw error;
      });

      const retryHandler = ErrorHandler.createRetryHandler(fn, 2, 50);

      try {
        await retryHandler();
        fail('Should have thrown an error');
      } catch (error) {
        // Expected to throw after retries
        expect(error).toBeDefined();
      }
      
      expect(fn).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });

    it('should use exponential backoff', async () => {
      const fn = jest.fn(async () => {
        const error: Partial<AxiosError> = {
          message: 'Network Error',
          code: 'ECONNREFUSED',
          isAxiosError: true,
          config: {} as any,
          toJSON: () => ({}),
          name: 'AxiosError',
        };
        throw error;
      });

      const startTime = Date.now();
      const retryHandler = ErrorHandler.createRetryHandler(fn, 2, 100);

      try {
        await retryHandler();
      } catch (error) {
        // Expected to fail
      }

      const duration = Date.now() - startTime;
      
      // Should wait at least 100ms + 200ms = 300ms
      expect(duration).toBeGreaterThanOrEqual(300);
    });
  });

  describe('Convenience functions', () => {
    it('should export convenience function for handleError', () => {
      const error = new Error('Test');
      const result = handleError(error);
      expect(result.type).toBe(ErrorType.UNKNOWN_ERROR);
    });

    it('should export convenience function for getUserMessage', () => {
      const errorInfo: ErrorInfo = {
        type: ErrorType.NETWORK_ERROR,
        message: 'Test',
        userMessage: '',
        retryable: true,
        timestamp: new Date().toISOString(),
      };
      const message = getUserMessage(errorInfo);
      expect(message).toContain('connect');
    });

    it('should export convenience function for shouldRetry', () => {
      const errorInfo: ErrorInfo = {
        type: ErrorType.NETWORK_ERROR,
        message: 'Test',
        userMessage: '',
        retryable: true,
        timestamp: new Date().toISOString(),
      };
      expect(shouldRetry(errorInfo)).toBe(true);
    });

    it('should export convenience function for logError', () => {
      const errorInfo: ErrorInfo = {
        type: ErrorType.NETWORK_ERROR,
        message: 'Test',
        userMessage: '',
        retryable: true,
        timestamp: new Date().toISOString(),
      };
      logError(errorInfo);
      expect(console.error).toHaveBeenCalled();
    });

    it('should export convenience function for reportToBackend', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({ ok: true });
      
      const errorInfo: ErrorInfo = {
        type: ErrorType.NETWORK_ERROR,
        message: 'Test',
        userMessage: '',
        retryable: true,
        timestamp: new Date().toISOString(),
      };
      
      await reportToBackend(errorInfo);
      expect(global.fetch).toHaveBeenCalled();
    });
  });
});
