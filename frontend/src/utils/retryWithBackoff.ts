/**
 * Retry utilities with exponential backoff.
 */

export interface RetryOptions {
  maxRetries: number;
  initialDelay: number;
  maxDelay: number;
  factor: number;
  shouldRetry?: (error: ErrorLike) => boolean;
}

type ErrorLike = {
  code?: string;
  response?: {
    status?: number;
  };
  message?: string;
};

function defaultShouldRetry(error: ErrorLike): boolean {
  if (error.code === 'ECONNABORTED' || error.code === 'ENOTFOUND' || error.code === 'ETIMEDOUT') {
    return true;
  }

  if (error.response?.status === 429) {
    return true;
  }

  if (error.response?.status !== undefined) {
    if (error.response.status >= 500 && error.response.status < 600) {
      return true;
    }

    if (error.response.status >= 400 && error.response.status < 500) {
      return false;
    }
  }

  return true;
}

export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryOptions
): Promise<T> {
  const { maxRetries, initialDelay, maxDelay, factor, shouldRetry = defaultShouldRetry } = options;

  let lastError: unknown;
  let attempt = 0;

  while (attempt <= maxRetries) {
    try {
      return await fn();
    } catch (error: unknown) {
      lastError = error;

      if (!shouldRetry(asErrorLike(error))) {
        throw error;
      }

      if (attempt >= maxRetries) {
        throw error;
      }

      const delay = Math.min(initialDelay * Math.pow(factor, attempt), maxDelay);
      const jitter = delay * 0.1 * (Math.random() * 2 - 1);
      const actualDelay = Math.max(0, delay + jitter);

      await sleep(actualDelay);
      attempt++;
    }
  }

  throw lastError;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function asErrorLike(error: unknown): ErrorLike {
  if (typeof error === 'object' && error !== null) {
    return error as ErrorLike;
  }

  return {
    message: typeof error === 'string' ? error : 'Unknown error',
  };
}

export function createRetryFunction(options: RetryOptions) {
  return <T>(fn: () => Promise<T>): Promise<T> => retryWithBackoff(fn, options);
}

export const DEFAULT_API_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  factor: 2,
};

export const TASK_QUEUE_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 3,
  initialDelay: 5 * 60 * 1000,
  maxDelay: 30 * 60 * 1000,
  factor: 3,
};

export const TASK_QUEUE_RETRY_OPTIONS_EXACT: RetryOptions = {
  maxRetries: 3,
  initialDelay: 5 * 60 * 1000,
  maxDelay: 30 * 60 * 1000,
  factor: 3,
  shouldRetry: () => true,
};

export async function retryTaskWithExactDelays<T>(
  fn: () => Promise<T>,
  delays: number[] = [5 * 60 * 1000, 15 * 60 * 1000, 30 * 60 * 1000]
): Promise<T> {
  let lastError: unknown;

  for (let attempt = 0; attempt <= delays.length; attempt++) {
    try {
      return await fn();
    } catch (error: unknown) {
      lastError = error;

      if (attempt >= delays.length) {
        throw error;
      }

      await sleep(delays[attempt]);
    }
  }

  throw lastError;
}
