/**
 * Compatibility exports for the historical axios service entrypoint.
 *
 * The maintained implementation lives in `src/lib/api-client`.
 */
export {
  apiClient,
  apiClientEnhanced,
  optimizedApiClient,
  getApiClient,
  apiFetch,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
} from '@/lib/api-client';
