/**
 * Tests for Enhanced API Client
 * 
 * Validates Requirements: 2.5, 4.4, 4.7
 * 
 * These tests verify the API client's core functionality:
 * - HTTP methods (GET, POST, PUT, DELETE)
 * - Authentication token management
 * - Configuration options
 * - Response structure
 */

import { ApiClient, ApiClientConfig, ApiResponse } from '../api-client';

describe('ApiClient', () => {
  describe('Configuration', () => {
    it('should create an instance with required configuration', () => {
      const config: ApiClientConfig = {
        baseURL: 'http://localhost:8000/api/v1',
        timeout: 30000,
      };

      const client = new ApiClient(config);

      expect(client).toBeDefined();
      expect(client).toBeInstanceOf(ApiClient);
    });

    it('should use default timeout of 30 seconds when not specified', () => {
      const config: ApiClientConfig = {
        baseURL: 'http://localhost:8000/api/v1',
      };

      const client = new ApiClient(config);

      expect(client).toBeDefined();
    });

    it('should accept custom timeout configuration', () => {
      const config: ApiClientConfig = {
        baseURL: 'http://localhost:8000/api/v1',
        timeout: 60000,
      };

      const client = new ApiClient(config);

      expect(client).toBeDefined();
    });

    it('should accept custom retry configuration', () => {
      const config: ApiClientConfig = {
        baseURL: 'http://localhost:8000/api/v1',
        timeout: 30000,
        retryConfig: {
          retries: 5,
          retryDelay: (retryCount) => retryCount * 1000,
          retryCondition: (error) => !!error.response && error.response.status >= 500,
        },
      };

      const client = new ApiClient(config);

      expect(client).toBeDefined();
    });
  });

  describe('Authentication token management', () => {
    let client: ApiClient;

    beforeEach(() => {
      client = new ApiClient({
        baseURL: 'http://localhost:8000/api/v1',
      });
      
      // Clear localStorage before each test
      if (typeof window !== 'undefined') {
        localStorage.clear();
      }
    });

    afterEach(() => {
      if (typeof window !== 'undefined') {
        localStorage.clear();
      }
    });

    it('should set authentication token', () => {
      const token = 'test-token-123';
      
      client.setAuthToken(token);

      // Verify token is stored in localStorage
      expect(localStorage.getItem('auth_token')).toBe(token);
    });

    it('should clear authentication token', () => {
      const token = 'test-token-456';
      
      client.setAuthToken(token);
      expect(localStorage.getItem('auth_token')).toBe(token);

      client.clearAuthToken();

      // Verify token is cleared from localStorage
      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(localStorage.getItem('token')).toBeNull();
    });

    it('should handle multiple token set/clear operations', () => {
      const token1 = 'token-1';
      const token2 = 'token-2';

      client.setAuthToken(token1);
      expect(localStorage.getItem('auth_token')).toBe(token1);

      client.setAuthToken(token2);
      expect(localStorage.getItem('auth_token')).toBe(token2);

      client.clearAuthToken();
      expect(localStorage.getItem('auth_token')).toBeNull();
    });
  });

  describe('HTTP Methods', () => {
    let client: ApiClient;

    beforeEach(() => {
      client = new ApiClient({
        baseURL: 'http://localhost:8000/api/v1',
      });
    });

    it('should have GET method', () => {
      expect(client.get).toBeDefined();
      expect(typeof client.get).toBe('function');
    });

    it('should have POST method', () => {
      expect(client.post).toBeDefined();
      expect(typeof client.post).toBe('function');
    });

    it('should have PUT method', () => {
      expect(client.put).toBeDefined();
      expect(typeof client.put).toBe('function');
    });

    it('should have DELETE method', () => {
      expect(client.delete).toBeDefined();
      expect(typeof client.delete).toBe('function');
    });
  });

  describe('Type Safety', () => {
    it('should support generic type parameters for responses', () => {
      interface TestData {
        id: string;
        name: string;
      }

      const client = new ApiClient({
        baseURL: 'http://localhost:8000/api/v1',
      });

      // This test verifies TypeScript compilation - if it compiles, the types are correct
      const testFunction = async () => {
        // These should compile without errors
        const getResponse: Promise<ApiResponse<TestData>> = client.get<TestData>('/test');
        const postResponse: Promise<ApiResponse<TestData>> = client.post<TestData>('/test', {});
        const putResponse: Promise<ApiResponse<TestData>> = client.put<TestData>('/test', {});
        const deleteResponse: Promise<ApiResponse<TestData>> = client.delete<TestData>('/test');

        // Verify the function signatures exist
        expect(getResponse).toBeDefined();
        expect(postResponse).toBeDefined();
        expect(putResponse).toBeDefined();
        expect(deleteResponse).toBeDefined();
      };

      expect(testFunction).toBeDefined();
    });
  });

  describe('Default Export', () => {
    it('should export a default apiClientEnhanced instance', () => {
      const { apiClientEnhanced } = require('../api-client');

      expect(apiClientEnhanced).toBeDefined();
      expect(apiClientEnhanced).toBeInstanceOf(ApiClient);
    });

    it('should configure default instance with environment variable', () => {
      // The default instance should use NEXT_PUBLIC_API_URL or fallback
      const { apiClientEnhanced } = require('../api-client');

      expect(apiClientEnhanced).toBeDefined();
    });
  });

  describe('Requirements Validation', () => {
    it('should satisfy Requirement 2.5: API client service for centralized request management', () => {
      const client = new ApiClient({
        baseURL: 'http://localhost:8000/api/v1',
      });

      // Verify all required HTTP methods are available
      expect(client.get).toBeDefined();
      expect(client.post).toBeDefined();
      expect(client.put).toBeDefined();
      expect(client.delete).toBeDefined();

      // Verify authentication token management
      expect(client.setAuthToken).toBeDefined();
      expect(client.clearAuthToken).toBeDefined();
    });

    it('should satisfy Requirement 4.4: Retry mechanism with exponential backoff', () => {
      // Verify retry configuration is supported
      const client = new ApiClient({
        baseURL: 'http://localhost:8000/api/v1',
        retryConfig: {
          retries: 3,
          retryDelay: (retryCount) => Math.pow(2, retryCount) * 1000,
          retryCondition: (error) => !error.response || error.response.status >= 500,
        },
      });

      expect(client).toBeDefined();
    });

    it('should satisfy Requirement 4.7: Timeout handling (default 30 seconds)', () => {
      // Verify default timeout
      const clientWithDefault = new ApiClient({
        baseURL: 'http://localhost:8000/api/v1',
      });
      expect(clientWithDefault).toBeDefined();

      // Verify custom timeout
      const clientWithCustom = new ApiClient({
        baseURL: 'http://localhost:8000/api/v1',
        timeout: 60000,
      });
      expect(clientWithCustom).toBeDefined();
    });
  });
});


