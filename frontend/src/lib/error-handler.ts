/**
 * Unified Error Handler for Frontend Application
 * 
 * Provides centralized error handling with:
 * - Error type identification
 * - User-friendly error messages
 * - Retry logic determination
 * - Error logging
 * - Backend error reporting
 * 
 * Requirements: 4.2, 4.3, 4.5, 7.4
 */

import { AxiosError } from 'axios';
import { ApiError } from './api-client';
export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  AUTH_ERROR = 'AUTH_ERROR',
  PERMISSION_ERROR = 'PERMISSION_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  RATE_LIMIT_ERROR = 'RATE_LIMIT_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}

/**
 * Error information structure
 */
export interface ErrorInfo {
  type: ErrorType;
  message: string;
  userMessage: string;
  details?: unknown;
  retryable: boolean;
  statusCode?: number;
  timestamp: string;
}

/**
 * Error Handler class
 * 
 * Provides unified error handling across the application
 */
export class ErrorHandler {
  /**
   * Handle an error and return structured error information
   */
  static handleError(error: unknown): ErrorInfo {
    const timestamp = new Date().toISOString();

    // Handle ApiError (from our API client)
    if (this.isApiError(error)) {
      return this.handleApiError(error, timestamp);
    }

    // Handle AxiosError
    if (this.isAxiosError(error)) {
      return this.handleAxiosError(error, timestamp);
    }

    // Handle standard Error
    if (error instanceof Error) {
      return {
        type: ErrorType.UNKNOWN_ERROR,
        message: error.message,
        userMessage: 'An unexpected error occurred. Please try again.',
        details: { stack: error.stack },
        retryable: false,
        timestamp,
      };
    }

    // Handle unknown error types
    return {
      type: ErrorType.UNKNOWN_ERROR,
      message: String(error),
      userMessage: 'An unexpected error occurred. Please try again.',
      details: error,
      retryable: false,
      timestamp,
    };
  }

  /**
   * Handle ApiError from our API client
   */
  private static handleApiError(error: ApiError, timestamp: string): ErrorInfo {
    const type = this.identifyErrorType(error.status, error.code);

    return {
      type,
      message: error.message,
      userMessage: this.getUserMessage({ type } as ErrorInfo),
      details: error.details,
      retryable: this.shouldRetry({ type } as ErrorInfo),
      statusCode: error.status,
      timestamp,
    };
  }

  /**
   * Handle AxiosError
   */
  private static handleAxiosError(error: AxiosError, timestamp: string): ErrorInfo {
    const statusCode = error.response?.status;
    const errorCode = error.code;
    const type = this.identifyErrorType(statusCode, errorCode);

    return {
      type,
      message: error.message,
      userMessage: this.getUserMessage({ type } as ErrorInfo),
      details: {
        response: error.response?.data,
        config: {
          url: error.config?.url,
          method: error.config?.method,
        },
      },
      retryable: this.shouldRetry({ type } as ErrorInfo),
      statusCode,
      timestamp,
    };
  }

  /**
   * Identify error type based on status code and error code
   */
  private static identifyErrorType(
    statusCode?: number,
    errorCode?: string
  ): ErrorType {
    // Network errors (no status code)
    if (!statusCode) {
      if (errorCode === 'ECONNABORTED' || errorCode === 'ETIMEDOUT') {
        return ErrorType.TIMEOUT_ERROR;
      }
      return ErrorType.NETWORK_ERROR;
    }

    // HTTP status code based classification
    switch (statusCode) {
      case 401:
        return ErrorType.AUTH_ERROR;
      case 403:
        return ErrorType.PERMISSION_ERROR;
      case 422:
        return ErrorType.VALIDATION_ERROR;
      case 429:
        return ErrorType.RATE_LIMIT_ERROR;
      case 500:
      case 502:
      case 503:
      case 504:
        return ErrorType.SERVER_ERROR;
      default:
        if (statusCode >= 400 && statusCode < 500) {
          return ErrorType.VALIDATION_ERROR;
        }
        if (statusCode >= 500) {
          return ErrorType.SERVER_ERROR;
        }
        return ErrorType.UNKNOWN_ERROR;
    }
  }

  /**
   * Get user-friendly error message based on error type
   */
  static getUserMessage(errorInfo: ErrorInfo): string {
    switch (errorInfo.type) {
      case ErrorType.NETWORK_ERROR:
        return 'Unable to connect to the server. Please check your internet connection and try again.';

      case ErrorType.TIMEOUT_ERROR:
        return 'The request took too long to complete. Please try again.';

      case ErrorType.AUTH_ERROR:
        return 'Your session has expired. Please log in again to continue.';

      case ErrorType.PERMISSION_ERROR:
        return 'You do not have permission to perform this action. Please contact your administrator if you believe this is an error.';

      case ErrorType.VALIDATION_ERROR:
        return 'The information provided is invalid. Please check your input and try again.';

      case ErrorType.SERVER_ERROR:
        return 'The server encountered an error. Our team has been notified. Please try again later.';

      case ErrorType.RATE_LIMIT_ERROR:
        return 'Too many requests. Please wait a moment before trying again.';

      case ErrorType.UNKNOWN_ERROR:
      default:
        return 'An unexpected error occurred. Please try again or contact support if the problem persists.';
    }
  }

  /**
   * Determine if an error is retryable
   */
  static shouldRetry(errorInfo: ErrorInfo): boolean {
    switch (errorInfo.type) {
      case ErrorType.NETWORK_ERROR:
      case ErrorType.TIMEOUT_ERROR:
      case ErrorType.SERVER_ERROR:
      case ErrorType.RATE_LIMIT_ERROR:
        return true;

      case ErrorType.AUTH_ERROR:
      case ErrorType.PERMISSION_ERROR:
      case ErrorType.VALIDATION_ERROR:
      case ErrorType.UNKNOWN_ERROR:
      default:
        return false;
    }
  }

  /**
   * Log error details for debugging
   */
  static logError(errorInfo: ErrorInfo): void {
    const logData = {
      type: errorInfo.type,
      message: errorInfo.message,
      statusCode: errorInfo.statusCode,
      timestamp: errorInfo.timestamp,
      details: errorInfo.details,
      retryable: errorInfo.retryable,
    };

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('[Error Handler]', logData);
    }

    // Log to monitoring service in production
    if (process.env.NODE_ENV === 'production') {
      // Send to monitoring service (e.g., Sentry, DataDog)
      this.sendToMonitoring(logData);
    }

    // Always log to structured logging
    this.logStructured(logData);
  }

  /**
   * Send error to monitoring service
   */
  private static sendToMonitoring(logData: Record<string, unknown>): void {
    // TODO: Integrate with monitoring service (Sentry, DataDog, etc.)
    // Example: Sentry.captureException(logData);
    console.log('[Monitoring] Error logged:', logData);
  }

  /**
   * Log error in structured format
   */
  private static logStructured(logData: Record<string, unknown>): void {
    // Structured logging for aggregation
    const structuredLog = {
      level: 'error',
      timestamp: new Date().toISOString(),
      service: 'frontend',
      ...logData,
    };

    console.error(JSON.stringify(structuredLog));
  }

  /**
   * Report error to backend logging system
   * Requirement 7.4: Client-side error reporting
   */
  static async reportToBackend(errorInfo: ErrorInfo): Promise<void> {
    try {
      // Get API base URL
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

      // Prepare error report payload
      const payload = {
        type: errorInfo.type,
        message: errorInfo.message,
        statusCode: errorInfo.statusCode,
        timestamp: errorInfo.timestamp,
        details: errorInfo.details,
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
        url: typeof window !== 'undefined' ? window.location.href : 'unknown',
      };

      // Send to backend error reporting endpoint
      await fetch(`${apiUrl}/errors/client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
    } catch (error) {
      // Graceful degradation - don't fail if error reporting fails
      console.warn('[Error Handler] Failed to report error to backend:', error);
    }
  }

  /**
   * Type guard for ApiError
   */
  private static isApiError(error: unknown): error is ApiError {
    return (
      typeof error === 'object' &&
      error !== null &&
      'message' in error &&
      'code' in error &&
      'status' in error
    );
  }

  /**
   * Type guard for AxiosError
   */
  private static isAxiosError(error: unknown): error is AxiosError {
    return (
      typeof error === 'object' &&
      error !== null &&
      'isAxiosError' in error &&
      (error as AxiosError).isAxiosError === true
    );
  }

  /**
   * Handle error with full workflow (handle, log, report)
   */
  static async handleErrorComplete(error: unknown): Promise<ErrorInfo> {
    const errorInfo = this.handleError(error);
    this.logError(errorInfo);

    // Report to backend in production
    if (process.env.NODE_ENV === 'production') {
      await this.reportToBackend(errorInfo);
    }

    return errorInfo;
  }

  /**
   * Create a retry function for retryable errors
   */
  static createRetryHandler<T>(
    fn: () => Promise<T>,
    maxRetries: number = 3,
    delayMs: number = 1000
  ): () => Promise<T> {
    return async () => {
      let lastError: unknown;

      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
          return await fn();
        } catch (error) {
          lastError = error;
          const errorInfo = this.handleError(error);

          // Don't retry if error is not retryable
          if (!errorInfo.retryable) {
            throw error;
          }

          // Don't retry on last attempt
          if (attempt === maxRetries) {
            throw error;
          }

          // Wait before retrying (exponential backoff)
          const delay = delayMs * Math.pow(2, attempt);
          console.log(`[Error Handler] Retrying in ${delay}ms (attempt ${attempt + 1}/${maxRetries})`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }

      throw lastError;
    };
  }
}

/**
 * Convenience function to handle errors
 */
export function handleError(error: unknown): ErrorInfo {
  return ErrorHandler.handleError(error);
}

/**
 * Convenience function to get user message
 */
export function getUserMessage(errorInfo: ErrorInfo): string {
  return ErrorHandler.getUserMessage(errorInfo);
}

/**
 * Convenience function to check if error is retryable
 */
export function shouldRetry(errorInfo: ErrorInfo): boolean {
  return ErrorHandler.shouldRetry(errorInfo);
}

/**
 * Convenience function to log error
 */
export function logError(errorInfo: ErrorInfo): void {
  ErrorHandler.logError(errorInfo);
}

/**
 * Convenience function to report error to backend
 */
export async function reportToBackend(errorInfo: ErrorInfo): Promise<void> {
  return ErrorHandler.reportToBackend(errorInfo);
}

/**
 * Convenience function for complete error handling
 */
export async function handleErrorComplete(error: unknown): Promise<ErrorInfo> {
  return ErrorHandler.handleErrorComplete(error);
}

// Export default
export default ErrorHandler;
