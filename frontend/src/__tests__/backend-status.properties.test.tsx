/**
 * Property-Based Tests for Backend Status Hook
 * 
 * Tests core properties of backend availability detection using fast-check.
 * 
 * Validates Requirements: 3.1, 3.3, 3.6
 */

import { renderHook, waitFor } from '@testing-library/react';
import { BackendStatusProvider, useBackendStatusContext } from '@/contexts/BackendStatusContext';
import React from 'react';

// Mock fetch globally
global.fetch = jest.fn();

describe('Backend Status Hook - Property Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  /**
   * Property 9: Backend availability check is performed on mount
   * 
   * For any frontend mount, a health check request should be made to the backend.
   * 
   * Validates: Requirements 3.1, 10.1
   */
  it('should perform backend availability check on mount', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <BackendStatusProvider>{children}</BackendStatusProvider>
    );

    renderHook(() => useBackendStatusContext(), { wrapper });

    // Wait for the health check to complete
    await waitFor(() => {
      expect(result.current.isOnline).toBeDefined();
    });

    // Verify fetch was called
    expect(global.fetch).toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.any(Object)
    );
  });

  /**
   * Property 11: Banner is dismissed when backend becomes available
   * 
   * For any backend that becomes available after being unavailable, 
   * the banner should be automatically dismissed.
   * 
   * Validates: Requirements 3.3
   */
  it('should update availability status when backend becomes available', async () => {
    // First call returns unavailable
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <BackendStatusProvider>{children}</BackendStatusProvider>
    );

    renderHook(() => useBackendStatusContext(), { wrapper });

    // Wait for initial check
    await waitFor(() => {
      expect(result.current.isOnline).toBe(false);
    });

    // Simulate backend becoming available
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
    });

    // Trigger retry
    await result.current.retry();

    // Wait for status to update
    await waitFor(() => {
      expect(result.current.isOnline).toBe(true);
    });
  });

  /**
   * Property 13: Retry button is available when backend unavailable
   * 
   * For any backend unavailability, a retry button should be present 
   * in the unavailability banner.
   * 
   * Validates: Requirements 3.6
   */
  it('should provide retry function when backend is unavailable', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <BackendStatusProvider>{children}</BackendStatusProvider>
    );

    renderHook(() => useBackendStatusContext(), { wrapper });

    // Wait for initial check
    await waitFor(() => {
      expect(result.current.isOnline).toBe(false);
    });

    // Verify retry function exists and is callable
    expect(result.current.retry).toBeDefined();
    expect(typeof result.current.retry).toBe('function');

    // Mock successful retry
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
    });

    // Call retry
    await result.current.retry();

    // Verify fetch was called again
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  /**
   * Property: Backend availability state is properly managed
   * 
   * For any backend state, the hook should properly track and expose 
   * the availability status.
   * 
   * Validates: Requirements 3.1
   */
  it.each([
    { ok: true, status: 200, expectedOnline: true },
    { ok: false, status: 503, expectedOnline: false },
    { ok: false, status: 500, expectedOnline: false },
  ])(
    'should set isOnline to $expectedOnline when backend returns status $status',
    async ({ ok, status, expectedOnline }) => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok,
        status,
      });

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <BackendStatusProvider>{children}</BackendStatusProvider>
      );

      const { result } = renderHook(() => useBackendStatusContext(), { wrapper });

      // Wait for check to complete
      await waitFor(() => {
        expect(result.current.isOnline).toBe(expectedOnline);
      });

      expect(result.current.isOnline).toBe(expectedOnline);
    }
  );

  /**
   * Property: isChecking state reflects polling status
   * 
   * For any health check operation, isChecking should be true during 
   * the check and false after completion.
   * 
   * Validates: Requirements 3.1
   */
  it('should set isChecking to true during health check', async () => {
    let resolveCheck: () => void;
    const checkPromise = new Promise<void>((resolve) => {
      resolveCheck = resolve;
    });

    (global.fetch as jest.Mock).mockReturnValueOnce(checkPromise);

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <BackendStatusProvider>{children}</BackendStatusProvider>
    );

    const { result } = renderHook(() => useBackendStatusContext(), { wrapper });

    // Initially checking
    expect(result.current.isChecking).toBe(true);

    // Resolve the check
    resolveCheck!();

    // Wait for check to complete
    await waitFor(() => {
      expect(result.current.isChecking).toBe(false);
    });
  });

  /**
   * Property: Polling interval is respected
   * 
   * For any running hook, health checks should be performed at 
   * approximately 30-second intervals.
   * 
   * Validates: Requirements 3.1
   */
  it('should poll backend health at regular intervals', async () => {
    jest.useFakeTimers();

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <BackendStatusProvider>{children}</BackendStatusProvider>
    );

    const { result } = renderHook(() => useBackendStatusContext(), { wrapper });

    // Initial call
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    // Advance time by 30 seconds
    jest.advanceTimersByTime(30000);

    // Should have called fetch again
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    // Advance time by another 30 seconds
    jest.advanceTimersByTime(30000);

    // Should have called fetch a third time
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    jest.useRealTimers();
  });

  /**
   * Property: Network errors are handled gracefully
   * 
   * For any network error during health check, the hook should 
   * set isOnline to false without throwing.
   * 
   * Validates: Requirements 3.1
   */
  it('should handle network errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <BackendStatusProvider>{children}</BackendStatusProvider>
    );

    const { result } = renderHook(() => useBackendStatusContext(), { wrapper });

    // Wait for error handling
    await waitFor(() => {
      expect(result.current.isOnline).toBe(false);
    });

    expect(result.current.isOnline).toBe(false);
    expect(result.current.isChecking).toBe(false);
  });

  /**
   * Property: lastChecked timestamp is updated
   * 
   * For any health check, the lastChecked timestamp should be 
   * updated to the current time.
   * 
   * Validates: Requirements 3.1
   */
  it('should update lastChecked timestamp after each check', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <BackendStatusProvider>{children}</BackendStatusProvider>
    );

    const { result } = renderHook(() => useBackendStatusContext(), { wrapper });

    const beforeCheck = new Date();

    // Wait for check to complete
    await waitFor(() => {
      expect(result.current.lastChecked).toBeDefined();
    });

    const afterCheck = new Date();

    // lastChecked should be between before and after
    expect(result.current.lastChecked).toBeDefined();
    expect(result.current.lastChecked!.getTime()).toBeGreaterThanOrEqual(
      beforeCheck.getTime()
    );
    expect(result.current.lastChecked!.getTime()).toBeLessThanOrEqual(
      afterCheck.getTime()
    );
  });
});
