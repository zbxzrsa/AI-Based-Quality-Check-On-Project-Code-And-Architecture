/**
 * Service layer exports
 * Centralized API service modules
 */

// Export specific items to avoid conflicts
export { apiClient } from './api';
export * from './CacheService';
export * from './config';
export * from './ErrorMonitor';

// Re-export unified API client from lib
export { apiClient as optimizedApiClient, ApiClient, apiClientEnhanced } from '@/lib/api-client';
