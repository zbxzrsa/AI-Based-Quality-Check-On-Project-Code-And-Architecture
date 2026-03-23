/**
 * Unified API Client
 *
 * A single, optimized API client that combines all features from previous implementations:
 * - Intelligent caching with TTL
 * - Request deduplication
 * - Retry logic with exponential backoff
 * - Circuit breaker pattern
 * - Concurrency control
 * - Performance monitoring
 * - Background cache warming
 * - Authentication handling via httpOnly cookies
 *
 * This replaces:
 * - lib/api-client-optimized.ts
 * - lib/api-client-enhanced.ts
 * - services/ApiClient.ts
 * - services/api.ts
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import axiosRetry, { exponentialDelay } from 'axios-retry';
import { createLogger } from '@/lib/utils/logger';

const logger = createLogger('APIClient');

// ============================================
// Types and Interfaces
// ============================================

export interface CacheEntry<T = unknown> {
  data: T;
  timestamp: number;
  ttl: number;
  etag?: string;
}

export interface RequestMetrics {
  url: string;
  method: string;
  duration: number;
  status: number;
  cached: boolean;
  timestamp: number;
}

export interface ApiClientConfig {
  baseURL?: string;
  timeout?: number;
  retries?: number;
  cacheTTL?: number;
  enableMetrics?: boolean;
  maxConcurrent?: number;
  deduplicationWindow?: number;
}

export interface RequestOptions extends AxiosRequestConfig {
  skipCache?: boolean;
  skipRetry?: boolean;
  skipDeduplication?: boolean;
  onTimeout?: () => void;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  headers: Record<string, string>;
}

export interface ApiError {
  message: string;
  code: string;
  status: number;
  details?: unknown;
}

interface PendingRequest {
  promise: Promise<unknown>;
  timestamp: number;
}

interface CircuitBreakerState {
  failures: number;
  lastFailureTime: number;
  state: 'CLOSED' | 'OPEN' | 'HALF_OPEN';
}

// ============================================
// Default Configuration
// ============================================

const DEFAULT_CONFIG: Required<Omit<ApiClientConfig, 'baseURL'>> = {
  timeout: 30000,
  retries: 3,
  cacheTTL: 5 * 60 * 1000, // 5 minutes
  enableMetrics: true,
  maxConcurrent: 6,
  deduplicationWindow: 1000, // 1 second
};

// ============================================
// Unified API Client Class
// ============================================

class UnifiedAPIClient {
  private client: AxiosInstance;
  private cache: Map<string, CacheEntry> = new Map();
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private metrics: RequestMetrics[] = [];
  private activeRequests = 0;
  private requestQueue: Array<() => void> = [];
  private timeoutWarnings: Set<string> = new Set();

  private config: Required<ApiClientConfig>;
  private cleanupTimer?: ReturnType<typeof setInterval>;
  private destroyed = false;

  private circuitBreaker: CircuitBreakerState = {
    failures: 0,
    lastFailureTime: 0,
    state: 'CLOSED',
  };

  constructor(config: ApiClientConfig = {}) {
    this.config = {
      ...DEFAULT_CONFIG,
      baseURL: config.baseURL || '/api',
      ...config,
    };

    this.client = axios.create({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true, // Include cookies for httpOnly auth
    });

    this.setupInterceptors();
    this.setupRetryLogic();
    this.startCacheCleanup();
  }

  // ============================================
  // Setup Methods
  // ============================================

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add correlation ID for tracing
        config.headers['X-Correlation-ID'] = this.generateCorrelationId();
        // Add request timestamp for metrics
        (config as AxiosRequestConfig & { requestStartTime?: number }).requestStartTime = Date.now();
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        this.recordMetrics(response);
        return response;
      },
      (error: AxiosError) => {
        if (error.response) {
          this.recordMetrics(error.response as AxiosResponse);

          // Handle specific error cases
          if (error.response.status === 401) {
            this.handleAuthError();
          } else if (error.response.status === 429) {
            this.handleRateLimitError(error);
          }
        }
        return Promise.reject(error);
      }
    );
  }

  private setupRetryLogic(): void {
    axiosRetry(this.client, {
      retries: this.config.retries,
      retryDelay: exponentialDelay,
      retryCondition: (error: AxiosError) => {
        return (
          axiosRetry.isNetworkOrIdempotentRequestError(error) ||
          error.response?.status === 429 || // Rate limit
          (error.response?.status ? error.response.status >= 500 : false) // Server errors
        );
      },
      onRetry: (retryCount, error, requestConfig) => {
        logger.warn(`Retry attempt ${retryCount} for ${requestConfig.method?.toUpperCase()} ${requestConfig.url}`, {
          error: error.message,
          status: error.response?.status
        });
      },
    });
  }

  private startCacheCleanup(): void {
    if (this.destroyed) return;

    this.cleanupTimer = setInterval(() => {
      if (this.destroyed) {
        if (this.cleanupTimer) {
          clearInterval(this.cleanupTimer);
          this.cleanupTimer = undefined;
        }
        return;
      }

      const now = Date.now();
      for (const [key, entry] of this.cache.entries()) {
        if (now - entry.timestamp > entry.ttl) {
          this.cache.delete(key);
        }
      }

      // Limit cache size to prevent memory bloat (max 100 entries)
      if (this.cache.size > 100) {
        const entries = Array.from(this.cache.entries());
        const toDelete = entries.slice(0, entries.length - 100);
        toDelete.forEach(([key]) => this.cache.delete(key));
      }
    }, 60000); // Clean every minute
  }

  // ============================================
  // Helper Methods
  // ============================================

  private generateCorrelationId(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
  }

  private generateCacheKey(method: string, url: string, params?: unknown, data?: unknown): string {
    return `${method}:${url}:${JSON.stringify(params)}:${JSON.stringify(data)}`;
  }

  private getCachedResponse<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    const now = Date.now();
    if (now - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  private setCachedResponse<T>(key: string, data: T, ttl?: number): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.config.cacheTTL,
    });
  }

  private recordMetrics(response: AxiosResponse): void {
    if (!this.config.enableMetrics) return;

    const config = response.config as AxiosRequestConfig & { requestStartTime?: number; fromCache?: boolean };
    const duration = Date.now() - (config.requestStartTime || Date.now());

    const metric: RequestMetrics = {
      url: response.config.url || '',
      method: response.config.method?.toUpperCase() || 'GET',
      duration,
      status: response.status,
      cached: !!config.fromCache,
      timestamp: Date.now(),
    };

    this.metrics.push(metric);

    // Keep only last 1000 metrics
    if (this.metrics.length > 1000) {
      this.metrics = this.metrics.slice(-1000);
    }

    // Log slow requests
    if (duration > 2000) {
      logger.warn(`Slow API request: ${metric.method} ${metric.url} took ${duration}ms`);
    }
  }

  private handleAuthError(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      sessionStorage.removeItem('auth_token');
      logger.warn('Authentication expired, redirecting to login');
      window.location.href = '/auth/signin';
    }
  }

  private handleRateLimitError(error: AxiosError): void {
    const retryAfter = error.response?.headers?.['retry-after'];
    if (retryAfter) {
      logger.warn(`Rate limited. Retry after ${retryAfter} seconds`);
    }
  }

  // ============================================
  // Request Methods
  // ============================================

  private async executeWithConcurrencyControl<T>(requestFn: () => Promise<T>): Promise<T> {
    // Concurrency control - wait until available slot
    if (this.activeRequests >= this.config.maxConcurrent) {
      await new Promise<void>((resolve) => {
        this.requestQueue.push(resolve);
      });
    }

    this.activeRequests++;

    try {
      return await requestFn();
    } finally {
      this.activeRequests--;
      // Process queue
      if (this.requestQueue.length > 0 && this.activeRequests < this.config.maxConcurrent) {
        const resolve = this.requestQueue.shift();
        if (resolve) resolve();
      }
    }
  }

  private async deduplicateRequest<T>(key: string, fn: () => Promise<T>): Promise<T> {
    const now = Date.now();
    const pending = this.pendingRequests.get(key);

    // If incomplete identical request exists within deduplication window, return its Promise
    if (pending && now - pending.timestamp < this.config.deduplicationWindow) {
      return pending.promise as Promise<T>;
    }

    // Create new request
    const promise = fn().finally(() => {
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, { promise, timestamp: now });

    return promise;
  }

  async get<T>(url: string, config?: RequestOptions): Promise<T> {
    const fullConfig = { ...config, method: 'GET', url };
    const cacheKey = this.generateCacheKey('GET', url, config?.params);

    // Check cache first for GET requests
    if (!config?.skipCache) {
      const cached = this.getCachedResponse<T>(cacheKey);
      if (cached !== null) {
        (fullConfig as RequestOptions & { fromCache?: boolean }).fromCache = true;
        return cached;
      }
    }

    // Check for pending request (deduplication)
    if (!config?.skipDeduplication) {
      return this.deduplicateRequest(cacheKey, async () => {
        const response = await this.executeWithConcurrencyControl(() =>
          this.client.get<T>(url, config)
        );
        if (!config?.skipCache) {
          this.setCachedResponse(cacheKey, response.data);
        }
        return response.data;
      });
    }

    const response = await this.executeWithConcurrencyControl(() =>
      this.client.get<T>(url, config)
    );

    if (!config?.skipCache) {
      this.setCachedResponse(cacheKey, response.data);
    }

    return response.data;
  }

  async post<T>(url: string, data?: unknown, config?: RequestOptions): Promise<T> {
    const response = await this.executeWithConcurrencyControl(() =>
      this.client.post<T>(url, data, config)
    );

    // Invalidate related cache entries
    this.invalidateCache(url);

    return response.data;
  }

  async put<T>(url: string, data?: unknown, config?: RequestOptions): Promise<T> {
    const response = await this.executeWithConcurrencyControl(() =>
      this.client.put<T>(url, data, config)
    );

    // Invalidate related cache entries
    this.invalidateCache(url);

    return response.data;
  }

  async patch<T>(url: string, data?: unknown, config?: RequestOptions): Promise<T> {
    const response = await this.executeWithConcurrencyControl(() =>
      this.client.patch<T>(url, data, config)
    );

    // Invalidate related cache entries
    this.invalidateCache(url);

    return response.data;
  }

  async delete<T>(url: string, config?: RequestOptions): Promise<T> {
    const response = await this.executeWithConcurrencyControl(() =>
      this.client.delete<T>(url, config)
    );

    // Invalidate related cache entries
    this.invalidateCache(url);

    return response.data;
  }

  // ============================================
  // Cache Management
  // ============================================

  private invalidateCache(url: string): void {
    // Remove cache entries that might be affected by this mutation
    const keysToDelete: string[] = [];

    for (const key of this.cache.keys()) {
      if (key.includes(url) || this.isRelatedUrl(key, url)) {
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach((key) => this.cache.delete(key));
  }

  private isRelatedUrl(cacheKey: string, mutatedUrl: string): boolean {
    const cacheUrl = cacheKey.split(':')[1];
    const basePath = mutatedUrl.split('/').slice(0, -1).join('/');
    return cacheUrl?.startsWith(basePath) || false;
  }

  clearCache(): void {
    this.cache.clear();
    this.pendingRequests.clear();
  }

  getCacheStats(): { size: number; hitRate: number; entries: number } {
    const totalRequests = this.metrics.length;
    const cachedRequests = this.metrics.filter((m) => m.cached).length;

    return {
      size: this.cache.size,
      hitRate: totalRequests > 0 ? cachedRequests / totalRequests : 0,
      entries: this.cache.size,
    };
  }

  // ============================================
  // Metrics and Monitoring
  // ============================================

  getMetrics(): RequestMetrics[] {
    return [...this.metrics];
  }

  // Background cache warming
  async warmCache(endpoints: string[]): Promise<void> {
    const warmingPromises = endpoints.map(async (endpoint) => {
      try {
        await this.get(endpoint);
        logger.debug(`Cache warmed for ${endpoint}`);
      } catch (error) {
        logger.warn(`Failed to warm cache for ${endpoint}`, error);
      }
    });

    await Promise.allSettled(warmingPromises);
  }

  // Health check with circuit breaker pattern
  async healthCheck(): Promise<boolean> {
    const now = Date.now();

    // Circuit breaker logic
    if (this.circuitBreaker.state === 'OPEN') {
      if (now - this.circuitBreaker.lastFailureTime > 60000) {
        // 1 minute
        this.circuitBreaker.state = 'HALF_OPEN';
      } else {
        return false;
      }
    }

    try {
      await this.get('/health', { skipCache: true, skipRetry: true });

      // Reset circuit breaker on success
      this.circuitBreaker.failures = 0;
      this.circuitBreaker.state = 'CLOSED';

      return true;
    } catch {
      this.circuitBreaker.failures++;
      this.circuitBreaker.lastFailureTime = now;

      if (this.circuitBreaker.failures >= 5) {
        this.circuitBreaker.state = 'OPEN';
      }

      return false;
    }
  }

  // ============================================
  // Cleanup
  // ============================================

  destroy(): void {
    this.destroyed = true;

    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = undefined;
    }

    this.cache.clear();
    this.pendingRequests.clear();
    this.metrics = [];
  }
}

// ============================================
// Singleton Instance
// ============================================

export const apiClient = new UnifiedAPIClient({
  timeout: 30000,
  retries: 3,
  cacheTTL: 5 * 60 * 1000, // 5 minutes
  enableMetrics: true,
  maxConcurrent: 6,
});

// Export aliases for backward compatibility
export const apiClientEnhanced = apiClient;
export const optimizedApiClient = apiClient;
export { UnifiedAPIClient as ApiClient };

// Utility hooks for React components
export const useAPIClient = () => {
  return {
    client: apiClient,
    clearCache: () => apiClient.clearCache(),
    getCacheStats: () => apiClient.getCacheStats(),
    getMetrics: () => apiClient.getMetrics(),
    warmCache: (endpoints: string[]) => apiClient.warmCache(endpoints),
    healthCheck: () => apiClient.healthCheck(),
  };
};

// Factory function for custom instances (used by existing code)
export const getApiClient = (config?: ApiClientConfig): UnifiedAPIClient => {
  if (config) {
    return new UnifiedAPIClient(config);
  }
  return apiClient;
};

// Default export
export default apiClient;
