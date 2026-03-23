/**
 * retryWithBackoff - 指数退避retry工具function
 * 
 * 实现指数退避算法，用于在failure时自动retry操作。
 * support可config的retrytimes数、延迟时间and退避因子。
 * 
 * use场景:
 * - APIrequestfailureretry
 * - 网络操作retry
 * - 任何need容错的异步操作
 * 
 * @example
 * ```typescript
 * const result = await retryWithBackoff(
 *   () => fetch('/api/data'),
 *   {
 *     maxRetries: 3,
 *     initialDelay: 1000,
 *     maxDelay: 10000,
 *     factor: 2,
 *     shouldRetry: (error) => error.status >= 500
 *   }
 * );
 * ```
 */

/**
 * retry选项config
 */
export interface RetryOptions {
  /** 最大retrytimes数 */
  maxRetries: number;
  /** 初始延迟时间（ms） */
  initialDelay: number;
  /** 最大延迟时间（ms） */
  maxDelay: number;
  /** 退避因子（每timesretry延迟时间的倍数） */
  factor: number;
  /** 自定义判断是否shouldretry的function */
  shouldRetry?: (error: Error) => boolean;
}

/**
 * 默认的retry判断function
 * 对于网络errorand5xxservice器error进行retry
 */
function defaultShouldRetry(error: any): boolean {
  // 网络error
  if (error.code === 'ECONNABORTED' || error.code === 'ENOTFOUND' || error.code === 'ETIMEDOUT') {
    return true;
  }

  // 5xxservice器error
  if (error.response?.status >= 500 && error.response?.status < 600) {
    return true;
  }

  // 429 Too Many Requests
  if (error.response?.status === 429) {
    return true;
  }

  // 不retry客户端error (4xx) andautherror
  if (error.response?.status >= 400 && error.response?.status < 500) {
    return false;
  }

  // 默认retry未知error
  return true;
}

/**
 * use指数退避策略retry异步操作
 * 
 * @param fn - 要execute的异步function
 * @param options - retryconfig选项
 * @returns Promise<T> - functionexecuteresult
 * @throws 如果所有retry都failure，抛出最后一times的error
 * 
 * @example
 * ```typescript
 * // 基本use
 * const data = await retryWithBackoff(
 *   () => apiClient.get('/data'),
 *   { maxRetries: 3, initialDelay: 1000, maxDelay: 10000, factor: 2 }
 * );
 * 
 * // 自定义retry条件
 * const data = await retryWithBackoff(
 *   () => apiClient.get('/data'),
 *   {
 *     maxRetries: 3,
 *     initialDelay: 1000,
 *     maxDelay: 10000,
 *     factor: 2,
 *     shouldRetry: (error) => error.message.includes('timeout')
 *   }
 * );
 * ```
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryOptions
): Promise<T> {
  const { maxRetries, initialDelay, maxDelay, factor, shouldRetry = defaultShouldRetry } = options;

  let lastError: Error;
  let attempt = 0;

  while (attempt <= maxRetries) {
    try {
      // 尝试executefunction
      return await fn();
    } catch (error: any) {
      lastError = error;

      // check是否shouldretry
      if (!shouldRetry(error)) {
        throw error;
      }

      // 如果已达到最大retrytimes数，抛出error
      if (attempt >= maxRetries) {
        throw error;
      }

      // 计算延迟时间: initialDelay * (factor ^ attempt)
      const delay = Math.min(initialDelay * Math.pow(factor, attempt), maxDelay);

      // add随机抖动 (±10%) 以避免retry风暴
      const jitter = delay * 0.1 * (Math.random() * 2 - 1);
      const actualDelay = Math.max(0, delay + jitter);

      // wait后retry
      await sleep(actualDelay);

      attempt++;
    }
  }

  // 理论上不会到达这里，但为了type安全
  throw lastError!;
}

/**
 * 睡眠function
 * @param ms - 睡眠时间（ms）
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * create预config的retryfunction
 * 
 * @param options - retryconfig选项
 * @returns return一item已config好的retryfunction
 * 
 * @example
 * ```typescript
 * const retryApi = createRetryFunction({
 *   maxRetries: 3,
 *   initialDelay: 1000,
 *   maxDelay: 10000,
 *   factor: 2
 * });
 * 
 * const data = await retryApi(() => apiClient.get('/data'));
 * ```
 */
export function createRetryFunction(options: RetryOptions) {
  return <T>(fn: () => Promise<T>): Promise<T> => {
    return retryWithBackoff(fn, options);
  };
}

/**
 * 默认的APIretryconfig
 * 符合requirement 10.3: 最多retry3times，use指数退避策略
 */
export const DEFAULT_API_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 3,
  initialDelay: 1000, // 1sec
  maxDelay: 10000, // 10sec
  factor: 2, // 每times延迟翻倍: 1s, 2s, 4s
};

/**
 * taskqueueretryconfig
 * 符合requirement 5.2: 在5min、15min、30min后retry
 */
export const TASK_QUEUE_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 3,
  initialDelay: 5 * 60 * 1000, // 5min
  maxDelay: 30 * 60 * 1000, // 30min
  factor: 3, // 5min, 15min, 30min (实际: 5min, 15min, 45min，need调整)
};

// 调整taskqueueconfig以精确匹配requirement
export const TASK_QUEUE_RETRY_OPTIONS_EXACT: RetryOptions = {
  maxRetries: 3,
  initialDelay: 5 * 60 * 1000, // 5min
  maxDelay: 30 * 60 * 1000, // 30min
  factor: 3, // use自定义延迟计算
  shouldRetry: (error: any) => {
    // taskfailure总是retry
    return true;
  },
};

/**
 * 为taskqueuecreate精确延迟的retryfunction
 * 延迟时间: 5min、15min、30min
 */
export async function retryTaskWithExactDelays<T>(
  fn: () => Promise<T>,
  delays: number[] = [5 * 60 * 1000, 15 * 60 * 1000, 30 * 60 * 1000]
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt <= delays.length; attempt++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;

      // 如果是最后一times尝试，抛出error
      if (attempt >= delays.length) {
        throw error;
      }

      // use精确的延迟时间
      await sleep(delays[attempt]);
    }
  }

  throw lastError!;
}
