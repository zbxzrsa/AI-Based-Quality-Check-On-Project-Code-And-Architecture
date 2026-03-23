/**
 * Integration tests for ApiClient retry mechanism
 * 
 * verifyRequirement:
 * - requirement 10.3: APIrequestfailure时use指数退避策略retry，最多retry3times
 */

import { ApiClient, ApiClientConfig } from '../ApiClient';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('ApiClient Retry Integration', () => {
  let apiClient: ApiClient;
  let mockAxiosInstance: any;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    // createmock axiosinstance
    mockAxiosInstance = {
      request: jest.fn(),
      interceptors: {
        request: { use: jest.fn(), eject: jest.fn() },
        response: { use: jest.fn(), eject: jest.fn() },
      },
    };

    mockedAxios.create.mockReturnValue(mockAxiosInstance);

    const config: ApiClientConfig = {
      baseURL: 'http://localhost:8000/api/v1',
      timeout: 30000,
      maxRetries: 3,
      maxConcurrent: 6,
      cacheTimeout: 5 * 60 * 1000,
    };

    apiClient = new ApiClient(config);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('指数退避retry机制', () => {
    it('shouldBeAt网络error时use指数退避retry', async () => {
      const networkError: any = new Error('Network Error');
      networkError.code = 'ECONNABORTED';

      // 前2timesfailure，第3timessuccess
      mockAxiosInstance.request
        .mockRejectedValueOnce(networkError)
        .mockRejectedValueOnce(networkError)
        .mockResolvedValue({ data: { success: true } });

      const promise = apiClient.get('/test');

      // run所有定时器以completeretry
      await jest.runAllTimersAsync();

      const result = await promise;

      expect(result).toEqual({ success: true });
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(3);
    });

    it('shouldBeAt5xxerror时use指数退避retry', async () => {
      const serverError: any = new Error('Internal Server Error');
      serverError.response = { status: 500 };

      // 前2timesfailure，第3timessuccess
      mockAxiosInstance.request
        .mockRejectedValueOnce(serverError)
        .mockRejectedValueOnce(serverError)
        .mockResolvedValue({ data: { success: true } });

      const promise = apiClient.get('/test');

      await jest.runAllTimersAsync();

      const result = await promise;

      expect(result).toEqual({ success: true });
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(3);
    });

    it('shouldBeAt429error时use指数退避retry', async () => {
      const rateLimitError: any = new Error('Too Many Requests');
      rateLimitError.response = { status: 429 };

      mockAxiosInstance.request
        .mockRejectedValueOnce(rateLimitError)
        .mockResolvedValue({ data: { success: true } });

      const promise = apiClient.get('/test');

      await jest.runAllTimersAsync();

      const result = await promise;

      expect(result).toEqual({ success: true });
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(2);
    });

    it('should throw error after max 3 retries', async () => {
      const networkError: any = new Error('Persistent Network Error');
      networkError.code = 'ETIMEDOUT';

      mockAxiosInstance.request.mockRejectedValue(networkError);

      const promise = apiClient.get('/test');

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('Persistent Network Error');
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(4); // 1 initial + 3 retries
    });

    it('should not retry 4xx client errors', async () => {
      const clientError: any = new Error('Bad Request');
      clientError.response = { status: 400 };

      mockAxiosInstance.request.mockRejectedValue(clientError);

      const promise = apiClient.get('/test');

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('Bad Request');
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(1); // No retries
    });

    it('should support custom retry config', async () => {
      const customConfig: ApiClientConfig = {
        baseURL: 'http://localhost:8000/api/v1',
        timeout: 30000,
        maxRetries: 2, // Only retry 2 times
        maxConcurrent: 6,
        cacheTimeout: 5 * 60 * 1000,
        retryOptions: {
          initialDelay: 500,
          maxDelay: 5000,
          factor: 3,
        },
      };

      const customClient = new ApiClient(customConfig);

      const networkError: any = new Error('Network Error');
      networkError.code = 'ECONNABORTED';

      mockAxiosInstance.request.mockRejectedValue(networkError);

      const promise = customClient.get('/test');

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('Network Error');
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(3); // 1 initial + 2 retries
    });
  });

  describe('retry与cacheintegration', () => {
    it('shouldBeAtretrysuccess后cacheresult', async () => {
      const networkError: any = new Error('Network Error');
      networkError.code = 'ECONNABORTED';

      mockAxiosInstance.request
        .mockRejectedValueOnce(networkError)
        .mockResolvedValue({ data: { cached: true } });

      // 第一timesrequest（会retry）
      const promise1 = apiClient.get('/test');
      await jest.runAllTimersAsync();
      const result1 = await promise1;

      expect(result1).toEqual({ cached: true });
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(2);

      // 第二timesrequestshouldusecache
      const result2 = await apiClient.get('/test');

      expect(result2).toEqual({ cached: true });
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(2); // 没有新request
    });
  });

  describe('retry与并发控制integration', () => {
    it('shouldBeAtretry时遵守并发限制', async () => {
      const networkError: any = new Error('Network Error');
      networkError.code = 'ECONNABORTED';

      // All requests will fail and retry
      mockAxiosInstance.request.mockRejectedValue(networkError);

      // Make multiple requests
      const promises = [
        apiClient.post('/test1', {}),
        apiClient.post('/test2', {}),
        apiClient.post('/test3', {}),
      ];

      await jest.runAllTimersAsync();

      // All requests should fail
      await expect(Promise.all(promises)).rejects.toThrow();

      // Each request should retry 3 times (1 initial + 3 retries = 4 calls per request)
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(12); // 3 requests * 4 calls
    });
  });

  describe('skipRetry option', () => {
    it('should support skip retry', async () => {
      const networkError: any = new Error('Network Error');
      networkError.code = 'ECONNABORTED';

      mockAxiosInstance.request.mockRejectedValue(networkError);

      const promise = apiClient.get('/test', { skipRetry: true });

      await jest.runAllTimersAsync();

      await expect(promise).rejects.toThrow('Network Error');
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(1); // No retries
    });
  });
});
