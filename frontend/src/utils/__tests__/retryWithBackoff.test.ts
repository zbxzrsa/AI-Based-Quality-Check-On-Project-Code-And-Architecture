/**
 * Unit tests for retryWithBackoff utility
 */

import { retryWithBackoff, createRetryFunction, DEFAULT_API_RETRY_OPTIONS, retryTaskWithExactDelays } from '../retryWithBackoff';

describe('retryWithBackoff', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('success场景', () => {
    it('should return result on first successful attempt', async () => {
      const mockFn = jest.fn().mockResolvedValue('success');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(1);
    });

    it('should succeed after retries', async () => {
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(new Error('Fail 1'))
        .mockRejectedValueOnce(new Error('Fail 2'))
        .mockResolvedValue('success');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(3);
    });
  });

  describe('failure场景', () => {
    it('should throw error after max retries', async () => {
      const error = new Error('Persistent failure');
      const mockFn = jest.fn().mockRejectedValue(error);

      // Suppress console errors during test
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('Persistent failure');
      expect(mockFn).toHaveBeenCalledTimes(4); // 1 initial + 3 retries

      consoleErrorSpy.mockRestore();
    });

    it('should not retry when shouldRetry returns false', async () => {
      const error = new Error('Do not retry');
      const mockFn = jest.fn().mockRejectedValue(error);

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
        shouldRetry: () => false,
      });

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('Do not retry');
      expect(mockFn).toHaveBeenCalledTimes(1); // No retries

      consoleErrorSpy.mockRestore();
    });

    it('should not retry 4xx client errors', async () => {
      const error: any = new Error('Bad Request');
      error.response = { status: 400 };
      const mockFn = jest.fn().mockRejectedValue(error);

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('Bad Request');
      expect(mockFn).toHaveBeenCalledTimes(1); // No retries for 4xx

      consoleErrorSpy.mockRestore();
    });
  });

  describe('retry策略', () => {
    it('should retry 5xx server errors', async () => {
      const error: any = new Error('Internal Server Error');
      error.response = { status: 500 };
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(error)
        .mockResolvedValue('success');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(2);
    });

    it('should retry 429 Too Many Requests', async () => {
      const error: any = new Error('Too Many Requests');
      error.response = { status: 429 };
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(error)
        .mockResolvedValue('success');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(2);
    });

    it('should retry network errors', async () => {
      const error: any = new Error('Network Error');
      error.code = 'ECONNABORTED';
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(error)
        .mockResolvedValue('success');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(2);
    });
  });

  describe('延迟计算', () => {
    it('should use exponential backoff delays', async () => {
      const error = new Error('Retry me');
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(error)
        .mockRejectedValueOnce(error)
        .mockRejectedValueOnce(error)
        .mockResolvedValue('success');

      const setTimeoutSpy = jest.spyOn(global, 'setTimeout');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();
      await promise;

      // verify延迟时间呈指数增长
      // 第1timesretry: ~1000ms (1000 * 2^0)
      // 第2timesretry: ~2000ms (1000 * 2^1)
      // 第3timesretry: ~4000ms (1000 * 2^2)
      const delays = setTimeoutSpy.mock.calls
        .map(call => call[1] as number)
        .filter(delay => delay > 0);

      expect(delays.length).toBeGreaterThanOrEqual(3);
      // 由于有随机抖动，check延迟在合理范围内
      expect(delays[0]).toBeGreaterThan(800);
      expect(delays[0]).toBeLessThan(1200);

      setTimeoutSpy.mockRestore();
    });

    it('should respect maxDelay', async () => {
      const error = new Error('Retry me');
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(error)
        .mockRejectedValueOnce(error)
        .mockResolvedValue('success');

      const setTimeoutSpy = jest.spyOn(global, 'setTimeout');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 5000,
        maxDelay: 6000, // 限制最大延迟
        factor: 2,
      });

      await jest.runAllTimersAsync();
      await promise;

      const delays = setTimeoutSpy.mock.calls
        .map(call => call[1] as number)
        .filter(delay => delay > 0);

      // 所有延迟都不应超过 maxDelay + jitter
      delays.forEach(delay => {
        expect(delay).toBeLessThanOrEqual(6600); // maxDelay + 10% jitter
      });

      setTimeoutSpy.mockRestore();
    });
  });

  describe('createRetryFunction', () => {
    it('should create a pre-configured retry function', async () => {
      const retryFn = createRetryFunction({
        maxRetries: 2,
        initialDelay: 500,
        maxDelay: 5000,
        factor: 2,
      });

      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(new Error('Fail'))
        .mockResolvedValue('success');

      const promise = retryFn(mockFn);

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(2);
    });
  });

  describe('DEFAULT_API_RETRY_OPTIONS', () => {
    it('should have correct default values', () => {
      expect(DEFAULT_API_RETRY_OPTIONS).toEqual({
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });
    });
  });

  describe('retryTaskWithExactDelays', () => {
    it('should use exact delays for task retries', async () => {
      const error = new Error('Task failed');
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(error)
        .mockRejectedValueOnce(error)
        .mockResolvedValue('success');

      const setTimeoutSpy = jest.spyOn(global, 'setTimeout');

      const promise = retryTaskWithExactDelays(mockFn, [1000, 2000, 3000]);

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(3);

      // verifyuse了精确的延迟时间
      const delays = setTimeoutSpy.mock.calls
        .map(call => call[1] as number)
        .filter(delay => delay > 0);

      expect(delays).toContain(1000);
      expect(delays).toContain(2000);

      setTimeoutSpy.mockRestore();
    });

    it('should throw after all delays exhausted', async () => {
      const error = new Error('Persistent task failure');
      const mockFn = jest.fn().mockRejectedValue(error);

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const promise = retryTaskWithExactDelays(mockFn, [100, 200]);

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('Persistent task failure');
      expect(mockFn).toHaveBeenCalledTimes(3); // 1 initial + 2 retries

      consoleErrorSpy.mockRestore();
    });
  });

  describe('边缘情况', () => {
    it('should handle maxRetries = 0', async () => {
      const error = new Error('No retries');
      const mockFn = jest.fn().mockRejectedValue(error);

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 0,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('No retries');
      expect(mockFn).toHaveBeenCalledTimes(1); // Only initial attempt

      consoleErrorSpy.mockRestore();
    });

    it('should handle very large factor', async () => {
      const error = new Error('Retry me');
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(error)
        .mockResolvedValue('success');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 5000,
        factor: 100, // Very large factor
      });

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      // Should still respect maxDelay
    });

    it('should handle zero initialDelay', async () => {
      const error = new Error('Retry me');
      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(error)
        .mockResolvedValue('success');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 0,
        maxDelay: 10000,
        factor: 2,
      });

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(2);
    });
  });

  describe('自定义shouldRetry', () => {
    it('should use custom retry logic', async () => {
      const error: any = new Error('Custom error');
      error.code = 'CUSTOM_ERROR';

      const mockFn = jest
        .fn()
        .mockRejectedValueOnce(error)
        .mockResolvedValue('success');

      const shouldRetry = jest.fn((err: any) => err.code === 'CUSTOM_ERROR');

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
        shouldRetry,
      });

      await jest.runAllTimersAsync();
      const result = await promise;

      expect(result).toBe('success');
      expect(shouldRetry).toHaveBeenCalledWith(error);
      expect(mockFn).toHaveBeenCalledTimes(2);
    });

    it('should not retry when custom shouldRetry returns false', async () => {
      const error: any = new Error('Do not retry this');
      error.code = 'NO_RETRY';

      const mockFn = jest.fn().mockRejectedValue(error);

      const shouldRetry = jest.fn((err: any) => err.code !== 'NO_RETRY');

      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const promise = retryWithBackoff(mockFn, {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        factor: 2,
        shouldRetry,
      });

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('Do not retry this');
      expect(shouldRetry).toHaveBeenCalledWith(error);
      expect(mockFn).toHaveBeenCalledTimes(1);

      consoleErrorSpy.mockRestore();
    });
  });
});
