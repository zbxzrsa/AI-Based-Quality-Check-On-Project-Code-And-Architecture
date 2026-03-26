/**
 * Compatibility exports for the historical services API client.
 *
 * The maintained implementation lives in `src/lib/api-client`.
 */
export {
  ApiClient,
  apiClient,
  apiClientEnhanced,
  optimizedApiClient,
  getApiClient,
  useAPIClient,
} from '@/lib/api-client';

export type {
  ApiClientConfig,
  ApiError,
  ApiFetchOptions,
  ApiResponse,
  RequestMetrics,
  RequestOptions,
} from '@/lib/api-client';
