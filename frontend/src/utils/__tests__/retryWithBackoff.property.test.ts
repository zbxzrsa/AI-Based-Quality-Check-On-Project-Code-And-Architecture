/**
 * Property-based tests for retryWithBackoff utility
 * 
 * **Feature: frontend-production-optimization, Property 9: APIrequestretry机制**
 * **Validates: Requirements 5.2, 10.3**
 * 
 * property 9: APIrequestretry机制 - 对于任何failure的APIrequest，shoulduse指数退避策略retry，最多retry3times。
 */

import fc from 'fast-check';
import { retryWithBackoff, RetryOptions } from '../retryWithBackoff';

describe('Property 9: APIrequestretry机制', () => {
  it('should retry up to maxRetries times for any failing operation', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 0, max: 3 }),
        async (maxRetries: number) => {
          const error = new Error('Test failure');
          const mockFn = jest.fn().mockRejectedValue(error);
          const options: RetryOptions = {
            maxRetries,
            initialDelay: 10,
            maxDelay: 100,
            factor: 2,
          };
          try {
            await retryWithBackoff(mockFn, options);
          } catch (e) {
            // Expected to fail
          }
          expect(mockFn).toHaveBeenCalledTimes(maxRetries + 1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should throw immediately for errors that should not be retried', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.oneof(fc.integer({ min: 400, max: 428 }), fc.integer({ min: 430, max: 499 })),
        fc.integer({ min: 1, max: 3 }),
        async (statusCode: number, maxRetries: number) => {
          const error: any = new Error('Client error');
          error.response = { status: statusCode };
          const mockFn = jest.fn().mockRejectedValue(error);
          const options: RetryOptions = {
            maxRetries,
            initialDelay: 10,
            maxDelay: 100,
            factor: 2,
          };
          try {
            await retryWithBackoff(mockFn, options);
            expect(true).toBe(false);
          } catch (e) {
            // Expected to throw immediately
          }
          expect(mockFn).toHaveBeenCalledTimes(1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should eventually succeed if any retry succeeds', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 0, max: 3 }),
        fc.integer({ min: 1, max: 5 }),
        fc.string(),
        async (failuresBeforeSuccess: number, maxRetries: number, successValue: string) => {
          if (failuresBeforeSuccess > maxRetries) {
            return;
          }
          const error = new Error('Temporary failure');
          const mockFn = jest.fn();
          for (let i = 0; i < failuresBeforeSuccess; i++) {
            mockFn.mockRejectedValueOnce(error);
          }
          mockFn.mockResolvedValue(successValue);
          const options: RetryOptions = {
            maxRetries,
            initialDelay: 10,
            maxDelay: 100,
            factor: 2,
          };
          const result = await retryWithBackoff(mockFn, options);
          expect(result).toBe(successValue);
          expect(mockFn).toHaveBeenCalledTimes(failuresBeforeSuccess + 1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should throw the last error if all retries fail', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 0, max: 3 }),
        fc.string({ minLength: 1 }),
        async (maxRetries: number, errorMessage: string) => {
          const error = new Error(errorMessage);
          const mockFn = jest.fn().mockRejectedValue(error);
          const options: RetryOptions = {
            maxRetries,
            initialDelay: 10,
            maxDelay: 100,
            factor: 2,
          };
          try {
            await retryWithBackoff(mockFn, options);
            expect(true).toBe(false);
          } catch (e: any) {
            expect(e.message).toBe(errorMessage);
          }
          expect(mockFn).toHaveBeenCalledTimes(maxRetries + 1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should respect custom shouldRetry function', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.boolean(),
        fc.integer({ min: 1, max: 3 }),
        async (shouldRetryValue: boolean, maxRetries: number) => {
          const error = new Error('Test error');
          const mockFn = jest.fn().mockRejectedValue(error);
          const shouldRetrySpy = jest.fn().mockReturnValue(shouldRetryValue);
          const options: RetryOptions = {
            maxRetries,
            initialDelay: 10,
            maxDelay: 100,
            factor: 2,
            shouldRetry: shouldRetrySpy,
          };
          try {
            await retryWithBackoff(mockFn, options);
          } catch (e) {
            // Expected to fail
          }
          if (shouldRetryValue) {
            expect(mockFn).toHaveBeenCalledTimes(maxRetries + 1);
            expect(shouldRetrySpy).toHaveBeenCalledWith(error);
          } else {
            expect(mockFn).toHaveBeenCalledTimes(1);
            expect(shouldRetrySpy).toHaveBeenCalledWith(error);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should retry 5xx server errors', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 500, max: 599 }),
        fc.integer({ min: 1, max: 3 }),
        async (statusCode: number, maxRetries: number) => {
          const error: any = new Error('Server error');
          error.response = { status: statusCode };
          const mockFn = jest.fn().mockRejectedValue(error);
          const options: RetryOptions = {
            maxRetries,
            initialDelay: 10,
            maxDelay: 100,
            factor: 2,
          };
          try {
            await retryWithBackoff(mockFn, options);
          } catch (e) {
            // Expected to fail after retries
          }
          expect(mockFn).toHaveBeenCalledTimes(maxRetries + 1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should retry network errors', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom('ECONNABORTED', 'ENOTFOUND', 'ETIMEDOUT'),
        fc.integer({ min: 1, max: 3 }),
        async (errorCode: string, maxRetries: number) => {
          const error: any = new Error('Network error');
          error.code = errorCode;
          const mockFn = jest.fn().mockRejectedValue(error);
          const options: RetryOptions = {
            maxRetries,
            initialDelay: 10,
            maxDelay: 100,
            factor: 2,
          };
          try {
            await retryWithBackoff(mockFn, options);
          } catch (e) {
            // Expected to fail after retries
          }
          expect(mockFn).toHaveBeenCalledTimes(maxRetries + 1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should retry 429 Too Many Requests errors', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 1, max: 3 }),
        async (maxRetries: number) => {
          const error: any = new Error('Too Many Requests');
          error.response = { status: 429 };
          const mockFn = jest.fn().mockRejectedValue(error);
          const options: RetryOptions = {
            maxRetries,
            initialDelay: 10,
            maxDelay: 100,
            factor: 2,
          };
          try {
            await retryWithBackoff(mockFn, options);
          } catch (e) {
            // Expected to fail after retries
          }
          expect(mockFn).toHaveBeenCalledTimes(maxRetries + 1);
        }
      ),
      { numRuns: 100 }
    );
  });
});
