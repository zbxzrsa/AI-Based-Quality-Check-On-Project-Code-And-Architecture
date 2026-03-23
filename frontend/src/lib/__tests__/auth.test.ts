/**
 * Unit Tests for Authentication Service
 * 
 * Tests URL construction, error handling, validation, and authentication operations
 */

import {
  getBackendUrl,
  validateEnvironmentConfig,
  getAuthUrl,
  getLoginUrl,
  getUserDetailsUrl,
  authenticateUser,
  createAuthError,
  getUserFriendlyErrorMessage,
  handleAuthError,
  isValidEmail,
  isValidPassword,
  validateCredentials,
  type LoginCredentials,
  type AuthError,
} from '../auth';

// Mock fetch globally
global.fetch = jest.fn();

describe('Authentication Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset environment variables
    process.env.NEXT_PUBLIC_API_URL = '';
    process.env.BACKEND_URL = '';
    process.env.NEXTAUTH_SECRET = '';
    process.env.NEXTAUTH_URL = '';
    process.env.NODE_ENV = 'test';
  });

  describe('Configuration', () => {
    describe('getBackendUrl', () => {
      it('should return NEXT_PUBLIC_API_URL when set', () => {
        process.env.NEXT_PUBLIC_API_URL = 'http://api.example.com';
        expect(getBackendUrl()).toBe('http://api.example.com');
      });

      it('should return BACKEND_URL when NEXT_PUBLIC_API_URL is not set', () => {
        process.env.BACKEND_URL = 'http://backend.example.com';
        expect(getBackendUrl()).toBe('http://backend.example.com');
      });

      it('should return default localhost URL when no env vars are set', () => {
        expect(getBackendUrl()).toBe('http://localhost:8000');
      });

      it('should prefer NEXT_PUBLIC_API_URL over BACKEND_URL', () => {
        process.env.NEXT_PUBLIC_API_URL = 'http://api.example.com';
        process.env.BACKEND_URL = 'http://backend.example.com';
        expect(getBackendUrl()).toBe('http://api.example.com');
      });
    });

    describe('validateEnvironmentConfig', () => {
      it('should return valid when all required env vars are set', () => {
        process.env.NEXTAUTH_SECRET = 'a'.repeat(32);
        process.env.NEXTAUTH_URL = 'http://localhost:3000';
        
        const result = validateEnvironmentConfig();
        expect(result.valid).toBe(true);
        expect(result.errors).toHaveLength(0);
      });

      it('should return error when NEXTAUTH_SECRET is missing', () => {
        process.env.NEXTAUTH_URL = 'http://localhost:3000';
        
        const result = validateEnvironmentConfig();
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('NEXTAUTH_SECRET is not configured');
      });

      it('should return error when NEXTAUTH_SECRET is too short', () => {
        process.env.NEXTAUTH_SECRET = 'short';
        process.env.NEXTAUTH_URL = 'http://localhost:3000';
        
        const result = validateEnvironmentConfig();
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('NEXTAUTH_SECRET must be at least 32 characters long');
      });

      it('should return error when NEXTAUTH_URL is missing', () => {
        process.env.NEXTAUTH_SECRET = 'a'.repeat(32);
        
        const result = validateEnvironmentConfig();
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('NEXTAUTH_URL is not configured');
      });

      it('should return multiple errors when multiple configs are invalid', () => {
        const result = validateEnvironmentConfig();
        expect(result.valid).toBe(false);
        expect(result.errors.length).toBeGreaterThan(1);
      });
    });
  });

  describe('URL Construction', () => {
    describe('getAuthUrl', () => {
      it('should construct URL with backend URL and endpoint', () => {
        process.env.NEXT_PUBLIC_API_URL = 'http://api.example.com';
        expect(getAuthUrl('/api/v1/auth/login')).toBe('http://api.example.com/api/v1/auth/login');
      });

      it('should handle backend URL with trailing slash', () => {
        process.env.NEXT_PUBLIC_API_URL = 'http://api.example.com/';
        expect(getAuthUrl('/api/v1/auth/login')).toBe('http://api.example.com/api/v1/auth/login');
      });

      it('should handle endpoint without leading slash', () => {
        process.env.NEXT_PUBLIC_API_URL = 'http://api.example.com';
        expect(getAuthUrl('api/v1/auth/login')).toBe('http://api.example.com/api/v1/auth/login');
      });

      it('should use default backend URL when not configured', () => {
        expect(getAuthUrl('/api/v1/auth/login')).toBe('http://localhost:8000/api/v1/auth/login');
      });
    });

    describe('getLoginUrl', () => {
      it('should return correct login endpoint URL', () => {
        process.env.NEXT_PUBLIC_API_URL = 'http://api.example.com';
        expect(getLoginUrl()).toBe('http://api.example.com/api/v1/auth/login');
      });
    });

    describe('getUserDetailsUrl', () => {
      it('should return correct user details endpoint URL', () => {
        process.env.NEXT_PUBLIC_API_URL = 'http://api.example.com';
        expect(getUserDetailsUrl()).toBe('http://api.example.com/api/v1/auth/me');
      });
    });
  });

  describe('Authentication Operations', () => {
    const mockCredentials: LoginCredentials = {
      email: 'test@example.com',
      password: 'Password123',
    };

    const mockAuthResponse = {
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
    };

    const mockUserResponse = {
      id: '123',
      email: 'test@example.com',
      full_name: 'Test User',
      role: 'user',
      is_active: true,
    };

    describe('authenticateUser', () => {
      it('should successfully authenticate user with valid credentials', async () => {
        (global.fetch as jest.Mock)
          .mockResolvedValueOnce({
            ok: true,
            json: async () => mockAuthResponse,
          })
          .mockResolvedValueOnce({
            ok: true,
            json: async () => mockUserResponse,
          });

        const user = await authenticateUser(mockCredentials);

        expect(user).toEqual({
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
          full_name: 'Test User',
          role: 'user',
          is_active: true,
          accessToken: 'mock-access-token',
          refreshToken: 'mock-refresh-token',
        });

        expect(global.fetch).toHaveBeenCalledTimes(2);
      });

      it('should throw validation error when email is missing', async () => {
        await expect(
          authenticateUser({ email: '', password: 'password' })
        ).rejects.toMatchObject({
          type: 'validation',
          message: 'Email and password are required',
        });
      });

      it('should throw validation error when password is missing', async () => {
        await expect(
          authenticateUser({ email: 'test@example.com', password: '' })
        ).rejects.toMatchObject({
          type: 'validation',
          message: 'Email and password are required',
        });
      });

      it('should throw credentials error on 401 response', async () => {
        (global.fetch as jest.Mock).mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Invalid credentials' }),
        });

        await expect(authenticateUser(mockCredentials)).rejects.toMatchObject({
          type: 'credentials',
          message: 'Invalid credentials',
          statusCode: 401,
        });
      });

      it('should throw server error on 500 response', async () => {
        (global.fetch as jest.Mock).mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => ({ detail: 'Internal server error' }),
        });

        await expect(authenticateUser(mockCredentials)).rejects.toMatchObject({
          type: 'server',
          message: 'Internal server error',
          statusCode: 500,
        });
      });

      it('should throw server error when access_token is missing', async () => {
        (global.fetch as jest.Mock).mockResolvedValueOnce({
          ok: true,
          json: async () => ({ refresh_token: 'token' }), // Missing access_token
        });

        await expect(authenticateUser(mockCredentials)).rejects.toMatchObject({
          type: 'server',
          message: 'Invalid response from authentication server',
        });
      });

      it('should throw server error when user details fetch fails', async () => {
        (global.fetch as jest.Mock)
          .mockResolvedValueOnce({
            ok: true,
            json: async () => mockAuthResponse,
          })
          .mockResolvedValueOnce({
            ok: false,
            status: 500,
          });

        await expect(authenticateUser(mockCredentials)).rejects.toMatchObject({
          type: 'server',
          message: 'Failed to fetch user details',
          statusCode: 500,
        });
      });

      it('should throw network error on fetch failure', async () => {
        (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

        await expect(authenticateUser(mockCredentials)).rejects.toMatchObject({
          type: 'network',
          message: 'Network error',
        });
      });

      it('should use correct authorization header for user details request', async () => {
        (global.fetch as jest.Mock)
          .mockResolvedValueOnce({
            ok: true,
            json: async () => mockAuthResponse,
          })
          .mockResolvedValueOnce({
            ok: true,
            json: async () => mockUserResponse,
          });

        await authenticateUser(mockCredentials);

        const secondCall = (global.fetch as jest.Mock).mock.calls[1];
        expect(secondCall[1].headers.Authorization).toBe('Bearer mock-access-token');
      });
    });
  });

  describe('Error Handling', () => {
    describe('createAuthError', () => {
      it('should create error with all properties', () => {
        const error = createAuthError('credentials', 'Invalid password', 401, 'Additional details');
        
        expect(error.type).toBe('credentials');
        expect(error.message).toBe('Invalid password');
        expect(error.statusCode).toBe(401);
        expect(error.details).toBe('Additional details');
        expect(error instanceof Error).toBe(true);
      });

      it('should create error without optional properties', () => {
        const error = createAuthError('network', 'Connection failed');
        
        expect(error.type).toBe('network');
        expect(error.message).toBe('Connection failed');
        expect(error.statusCode).toBeUndefined();
        expect(error.details).toBeUndefined();
      });
    });

    describe('getUserFriendlyErrorMessage', () => {
      it('should return friendly message for configuration error', () => {
        const error = createAuthError('configuration', 'Config missing');
        expect(getUserFriendlyErrorMessage(error)).toBe(
          'Authentication is not properly configured. Please contact support.'
        );
      });

      it('should return friendly message for network error', () => {
        const error = createAuthError('network', 'Connection failed');
        expect(getUserFriendlyErrorMessage(error)).toBe(
          'Unable to connect to the authentication server. Please check your connection and try again.'
        );
      });

      it('should return friendly message for credentials error', () => {
        const error = createAuthError('credentials', 'Invalid password');
        expect(getUserFriendlyErrorMessage(error)).toBe(
          'Invalid email or password. Please try again.'
        );
      });

      it('should return friendly message for server error', () => {
        const error = createAuthError('server', 'Internal error');
        expect(getUserFriendlyErrorMessage(error)).toBe(
          'The authentication server encountered an error. Please try again later.'
        );
      });

      it('should return original message for validation error', () => {
        const error = createAuthError('validation', 'Email is required');
        expect(getUserFriendlyErrorMessage(error)).toBe('Email is required');
      });
    });

    describe('handleAuthError', () => {
      it('should handle AuthError correctly', () => {
        const originalError = createAuthError('credentials', 'Invalid password', 401);
        const handled = handleAuthError(originalError);
        
        expect(handled).toEqual(originalError);
      });

      it('should convert regular Error to AuthError', () => {
        const originalError = new Error('Something went wrong');
        const handled = handleAuthError(originalError);
        
        expect(handled.type).toBe('network');
        expect(handled.message).toBe('Something went wrong');
      });

      it('should handle unknown error types', () => {
        const handled = handleAuthError('string error');
        
        expect(handled.type).toBe('network');
        expect(handled.message).toBe('An unexpected error occurred');
      });
    });
  });

  describe('Validation', () => {
    describe('isValidEmail', () => {
      it('should validate correct email addresses', () => {
        expect(isValidEmail('test@example.com')).toBe(true);
        expect(isValidEmail('user.name@example.co.uk')).toBe(true);
        expect(isValidEmail('user+tag@example.com')).toBe(true);
      });

      it('should reject invalid email addresses', () => {
        expect(isValidEmail('invalid')).toBe(false);
        expect(isValidEmail('invalid@')).toBe(false);
        expect(isValidEmail('@example.com')).toBe(false);
        expect(isValidEmail('invalid@example')).toBe(false);
        expect(isValidEmail('')).toBe(false);
      });
    });

    describe('isValidPassword', () => {
      it('should validate strong passwords', () => {
        const result = isValidPassword('Password123');
        expect(result.valid).toBe(true);
        expect(result.errors).toHaveLength(0);
      });

      it('should reject password that is too short', () => {
        const result = isValidPassword('Pass1');
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('Password must be at least 8 characters long');
      });

      it('should reject password without uppercase letter', () => {
        const result = isValidPassword('password123');
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('Password must contain at least one uppercase letter');
      });

      it('should reject password without lowercase letter', () => {
        const result = isValidPassword('PASSWORD123');
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('Password must contain at least one lowercase letter');
      });

      it('should reject password without number', () => {
        const result = isValidPassword('PasswordABC');
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('Password must contain at least one number');
      });

      it('should return multiple errors for weak password', () => {
        const result = isValidPassword('pass');
        expect(result.valid).toBe(false);
        expect(result.errors.length).toBeGreaterThan(1);
      });
    });

    describe('validateCredentials', () => {
      it('should validate correct credentials', () => {
        const result = validateCredentials({
          email: 'test@example.com',
          password: 'password',
        });
        expect(result.valid).toBe(true);
        expect(result.errors).toHaveLength(0);
      });

      it('should reject missing email', () => {
        const result = validateCredentials({
          email: '',
          password: 'password',
        });
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('Email is required');
      });

      it('should reject invalid email format', () => {
        const result = validateCredentials({
          email: 'invalid-email',
          password: 'password',
        });
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('Invalid email format');
      });

      it('should reject missing password', () => {
        const result = validateCredentials({
          email: 'test@example.com',
          password: '',
        });
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('Password is required');
      });

      it('should return multiple errors for invalid credentials', () => {
        const result = validateCredentials({
          email: '',
          password: '',
        });
        expect(result.valid).toBe(false);
        expect(result.errors.length).toBeGreaterThan(1);
      });
    });
  });
});
