/**
 * ApiClient - Unified API request client
 *
 * Features:
 * - Supports GET/POST/PUT/DELETE requests
 * - Request deduplication mechanism (merge identical requests within 1s)
 * - Concurrent request limit (max 6 items)
 * - Timeout detection and hint (5s)
 * - Exponential backoff retry (max 3 times)
 * - GET request caching (5min TTL)
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { retryWithBackoff, RetryOptions, DEFAULT_API_RETRY_OPTIONS } from '../utils/retryWithBackoff';

export interface ApiClientConfig {
  baseURL: string;
  timeout: number;
  maxRetries: number;
  maxConcurrent: number;
  cacheTimeout: number; // Cache validity period (ms)
  deduplicationWindow?: number; // Deduplication time window (ms), default 1000ms
  retryOptions?: Partial<RetryOptions>; // Custom retry config
}

export interface RequestOptions extends AxiosRequestConfig {
  skipCache?: boolean;
  skipRetry?: boolean;
  skipDeduplication?: boolean;
  onTimeout?: () => void;
}

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

interface PendingRequest {
  promise: Promise<any>;
  timestamp: number;
}

export class ApiClient {
  private axiosInstance: AxiosInstance;
  private config: ApiClientConfig;
  private cache: Map<string, CacheEntry<any>>;
  private pendingRequests: Map<string, PendingRequest>;
  private activeRequests: number;
  private requestQueue: Array<() => void>;
  private timeoutWarnings: Set<string>;
  private retryOptions: RetryOptions;

  constructor(config: ApiClientConfig) {
    this.config = {
      deduplicationWindow: 1000,
      ...config,
    };

    // Merge default retry config and custom config
    this.retryOptions = {
      ...DEFAULT_API_RETRY_OPTIONS,
      maxRetries: config.maxRetries,
      ...config.retryOptions,
    };

    this.axiosInstance = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.cache = new Map();
    this.pendingRequests = new Map();
    this.activeRequests = 0;
    this.requestQueue = [];
    this.timeoutWarnings = new Set();

    this.setupInterceptors();
  }

  /**
   * Setup request and response interceptors
   */
  private setupInterceptors(): void {
    // Request interceptor - add auth token
    this.axiosInstance.interceptors.request.use(
      (config) => {
        if (typeof window !== 'undefined') {
          const token = localStorage.getItem('token');
          if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle common errors
    this.axiosInstance.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized access
          if (typeof window !== 'undefined') {
            localStorage.removeItem('token');
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * GET request - automatic caching
   */
  async get<T>(url: string, options: RequestOptions = {}): Promise<T> {
    const cacheKey = this.generateCacheKey('GET', url, options.params);

    // Check cache
    if (!options.skipCache) {
      const cached = this.getFromCache<T>(cacheKey);
      if (cached !== null) {
        return cached;
      }
    }

    // Request deduplication
    if (!options.skipDeduplication) {
      const deduplicated = await this.deduplicateRequest(cacheKey, () =>
        this.executeRequest<T>('GET', url, undefined, options)
      );

      // Cache GET request result
      if (!options.skipCache) {
        this.setCache(cacheKey, deduplicated);
      }

      return deduplicated;
    }

    const result = await this.executeRequest<T>('GET', url, undefined, options);

    // Cache GET request result
    if (!options.skipCache) {
      this.setCache(cacheKey, result);
    }

    return result;
  }

  /**
   * POST request - no caching
   */
  async post<T>(url: string, data: any, options: RequestOptions = {}): Promise<T> {
    return this.executeRequest<T>('POST', url, data, options);
  }

  /**
   * PUT request - no caching
   */
  async put<T>(url: string, data: any, options: RequestOptions = {}): Promise<T> {
    return this.executeRequest<T>('PUT', url, data, options);
  }

  /**
   * DELETE request - no caching
   */
  async delete<T>(url: string, options: RequestOptions = {}): Promise<T> {
    return this.executeRequest<T>('DELETE', url, undefined, options);
  }

  /**
   * Execute request - includes concurrency control, retry and timeout handling
   */
  private async executeRequest<T>(
    method: string,
    url: string,
    data?: any,
    options: RequestOptions = {}
  ): Promise<T> {
    // Concurrency control - wait until available slot
    if (this.activeRequests >= this.config.maxConcurrent) {
      await new Promise<void>((resolve) => {
        this.requestQueue.push(resolve);
      });
    }

    // Occupy slot
    this.activeRequests++;

    try {
      const requestFn = async (): Promise<T> => {
        // Setup timeout monitoring
        const timeoutId = this.setupTimeoutWarning(url, options.onTimeout);

        try {
          const response: AxiosResponse<T> = await this.axiosInstance.request({
            method,
            url,
            data,
            ...options,
          });

          // Clear timeout warning
          clearTimeout(timeoutId);
          this.timeoutWarnings.delete(url);

          return response.data;
        } catch (error) {
          // Clear timeout warning
          clearTimeout(timeoutId);
          this.timeoutWarnings.delete(url);
          throw error;
        }
      };

      // Exponential backoff retry - use utility function
      if (!options.skipRetry) {
        return await retryWithBackoff(requestFn, this.retryOptions);
      }

      return await requestFn();
    } finally {
      // Request complete (success or failure), release slot
      this.activeRequests--;
      this.processQueue();
    }
  }

  /**
   * Handle request queue
   */
  private processQueue(): void {
    if (this.requestQueue.length > 0 && this.activeRequests < this.config.maxConcurrent) {
      const resolve = this.requestQueue.shift();
      if (resolve) {
        resolve();
      }
    }
  }

  /**
   * Request deduplication - merge identical requests within 1s into single request
   */
  private async deduplicateRequest<T>(
    key: string,
    fn: () => Promise<T>
  ): Promise<T> {
    const now = Date.now();
    const pending = this.pendingRequests.get(key);

    // If incomplete identical request exists within deduplication window, return its Promise
    if (pending && now - pending.timestamp < this.config.deduplicationWindow!) {
      return pending.promise;
    }

    // Create new request
    const promise = fn().finally(() => {
      // Cleanup after request completes
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, { promise, timestamp: now });

    return promise;
  }

  /**
   * Setup timeout warning - show timeout hint after 5s
   */
  private setupTimeoutWarning(url: string, onTimeout?: () => void): NodeJS.Timeout {
    const timeoutDuration = 5000; // 5 seconds

    return setTimeout(() => {
      if (!this.timeoutWarnings.has(url)) {
        this.timeoutWarnings.add(url);

        // Call custom timeout callback
        if (onTimeout) {
          onTimeout();
        } else {
          // Default timeout hint
          console.warn(`API request timeout: ${url} (exceeded ${timeoutDuration / 1000}s)`);

          // Show hint in browser environment
          if (typeof window !== 'undefined') {
            // Can integrate with notification system
            // Simply use console.warn here, should use UI notification component in production
          }
        }
      }
    }, timeoutDuration);
  }

  /**
   * Generate cache key
   */
  private generateCacheKey(method: string, url: string, params?: any): string {
    const paramsStr = params ? JSON.stringify(params) : '';
    return `${method}:${url}:${paramsStr}`;
  }

  /**
   * Get data from cache
   */
  private getFromCache<T>(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    const now = Date.now();

    // Check if expired
    if (now > entry.expiresAt) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  /**
   * Set cache
   */
  private setCache<T>(key: string, data: T): void {
    const now = Date.now();
    const entry: CacheEntry<T> = {
      data,
      timestamp: now,
      expiresAt: now + this.config.cacheTimeout,
    };

    this.cache.set(key, entry);
  }

  /**
   * Clear cache
   */
  clearCache(pattern?: string): void {
    if (!pattern) {
      this.cache.clear();
      return;
    }

    // Clear cache matching pattern
    const keys = Array.from(this.cache.keys());
    keys.forEach((key) => {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    });
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }

  /**
   * Sleep function
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Get current active request count
   */
  getActiveRequestCount(): number {
    return this.activeRequests;
  }

  /**
   * Get queued request count
   */
  getQueuedRequestCount(): number {
    return this.requestQueue.length;
  }
}

// Factory function to create default instance
export function createDefaultApiClient(): ApiClient {
  const defaultConfig: ApiClientConfig = {
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
    timeout: 30000,
    maxRetries: 3,
    maxConcurrent: 6,
    cacheTimeout: 5 * 60 * 1000, // 5 minutes
    deduplicationWindow: 1000, // 1 second
  };

  return new ApiClient(defaultConfig);
}

// Default instance - lazy initialization
let defaultInstance: ApiClient | null = null;

export function getApiClient(): ApiClient {
  if (!defaultInstance) {
    defaultInstance = createDefaultApiClient();
  }
  return defaultInstance;
}

// Backward compatible export
export const apiClient = new Proxy({} as ApiClient, {
  get(target, prop) {
    return getApiClient()[prop as keyof ApiClient];
  },
});
