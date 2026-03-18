/**
 * Frontend Lib - Central Export
 * 
 * This file provides centralized exports for all library modules.
 * Import from here instead of individual files.
 */

// API Client
export { apiClient, createAPIClient } from './api-client';

// Authentication
export { auth, LoginCredentials, RegisterData } from './auth';

// Error Handling
export { ErrorHandler, errorHandler } from './error-handler';

// Feature Flags
export {
  FeatureFlags,
  getFeatureFlag,
  isFeatureEnabled,
  setFeatureFlag,
  ABTestVariant,
} from './feature-flags';

// React Query
export { queryClient, queryKeys } from './queryClient';
export { reactQueryConfig } from './react-query';

// WebSocket
export { WebSocketManager } from './websocket-manager';

// Utils
export * from './utils';

// Validations
export * from './validations';
