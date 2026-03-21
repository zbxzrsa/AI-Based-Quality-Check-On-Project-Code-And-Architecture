/**
 * Stable route tests for unified authentication endpoints.
 */

const mockCookieStore = {
  get: jest.fn(),
  set: jest.fn(),
  delete: jest.fn(),
};

const mockFetchBackendWithFallback = jest.fn();

jest.mock('next/headers', () => ({
  cookies: jest.fn(async () => mockCookieStore),
}));

jest.mock('@/lib/server/backend', () => ({
  fetchBackendWithFallback: (...args: unknown[]) => mockFetchBackendWithFallback(...args),
}));

import { NextRequest } from 'next/server';
import { POST as loginPost } from '../login/route';
import { GET as meGet } from '../me/route';

describe('Unified Authentication API Routes', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.BACKEND_URL = 'http://localhost:8000';
    mockCookieStore.get.mockReset();
    mockCookieStore.set.mockReset();
    mockCookieStore.delete.mockReset();
    mockFetchBackendWithFallback.mockReset();
  });

  describe('Login Route', () => {
    it('calls the standard backend login endpoint', async () => {
      mockFetchBackendWithFallback.mockResolvedValue({
        response: {
          ok: true,
          json: async () => ({
            access_token: 'test-token',
            refresh_token: 'refresh-token',
          }),
        },
      });

      const request = new NextRequest('http://localhost:6066/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'password123',
        }),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const response = await loginPost(request);

      expect(response.status).toBe(200);
      expect(mockFetchBackendWithFallback).toHaveBeenCalledWith(
        '/api/v1/auth/login',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            email: 'test@example.com',
            password: 'password123',
          }),
        })
      );
      expect(mockCookieStore.set).toHaveBeenCalledWith(
        'access_token',
        'test-token',
        expect.objectContaining({ httpOnly: true })
      );
      expect(mockCookieStore.set).toHaveBeenCalledWith(
        'refresh_token',
        'refresh-token',
        expect.objectContaining({ httpOnly: true })
      );
    });

    it('returns 400 when email or password is missing', async () => {
      const request = new NextRequest('http://localhost:6066/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: '', password: '' }),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const response = await loginPost(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.detail).toBe('Email and password are required');
      expect(mockFetchBackendWithFallback).not.toHaveBeenCalled();
    });

    it('passes backend authentication errors through', async () => {
      mockFetchBackendWithFallback.mockResolvedValue({
        response: {
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Invalid credentials' }),
          text: async () => '',
        },
      });

      const request = new NextRequest('http://localhost:6066/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'wrongpassword',
        }),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const response = await loginPost(request);
      const data = await response.json();

      expect(response.status).toBe(401);
      expect(data.detail).toBe('Invalid credentials');
    });
  });

  describe('Me Route', () => {
    it('returns 401 when no access token is present', async () => {
      mockCookieStore.get.mockReturnValue(undefined);

      const response = await meGet(new NextRequest('http://localhost:6066/api/auth/me'));
      const data = await response.json();

      expect(response.status).toBe(401);
      expect(data.detail).toBe('Not authenticated');
    });

    it('calls the standard backend me endpoint', async () => {
      mockCookieStore.get.mockReturnValue({ value: 'test-access-token' });
      mockFetchBackendWithFallback.mockResolvedValue({
        response: {
          ok: true,
          json: async () => ({
            id: 'user-123',
            email: 'test@example.com',
            full_name: 'Test User',
            role: 'developer',
            is_active: true,
          }),
        },
      });

      const response = await meGet(new NextRequest('http://localhost:6066/api/auth/me'));
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.email).toBe('test@example.com');
      expect(mockFetchBackendWithFallback).toHaveBeenCalledWith(
        '/api/v1/auth/me',
        expect.objectContaining({
          method: 'GET',
          headers: {
            Authorization: 'Bearer test-access-token',
          },
        })
      );
    });

    it('clears cookies when backend returns 401', async () => {
      mockCookieStore.get.mockReturnValue({ value: 'expired-token' });
      mockFetchBackendWithFallback.mockResolvedValue({
        response: {
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Token expired' }),
          text: async () => '',
        },
      });

      const response = await meGet(new NextRequest('http://localhost:6066/api/auth/me'));
      const data = await response.json();

      expect(response.status).toBe(401);
      expect(data.detail).toBe('Token expired');
      expect(mockCookieStore.delete).toHaveBeenCalledWith('access_token');
      expect(mockCookieStore.delete).toHaveBeenCalledWith('refresh_token');
    });
  });
});
