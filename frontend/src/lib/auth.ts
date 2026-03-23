/**
 * Authentication Service Utility
 * 
 * Provides utilities for authentication operations including:
 * - URL construction from environment variables
 * - Authentication request handling
 * - Error handling and validation
 * - Development logging
 */

// ============================================================================
// Types and Interfaces
// ============================================================================

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface User {
  id: string;
  username: string;
  email?: string;
  name?: string;
  role?: string;
  is_active?: boolean;
  accessToken?: string;
  refreshToken?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
}

export interface UserResponse {
  id: string;
  username: string;
  role?: string;
  is_active?: boolean;
  created_at?: string;
  last_login?: string;
}

export type AuthErrorType = 'configuration' | 'network' | 'credentials' | 'server' | 'validation';

export interface AuthError {
  type: AuthErrorType;
  message: string;
  details?: string;
  statusCode?: number;
}

// ============================================================================
// Configuration
// ============================================================================

/**
 * Get the backend API URL from environment variables with fallback
 */
export function getBackendUrl(): string {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || 'http://localhost:8000';
  
  if (process.env.NODE_ENV === 'development') {
    console.log('[Auth] Using backend URL:', backendUrl);
  }
  
  return backendUrl;
}

/**
 * Validate environment configuration
 */
export function validateEnvironmentConfig(): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  if (!process.env.NEXTAUTH_SECRET) {
    errors.push('NEXTAUTH_SECRET is not configured');
  } else if (process.env.NEXTAUTH_SECRET.length < 32) {
    errors.push('NEXTAUTH_SECRET must be at least 32 characters long');
  }
  
  if (!process.env.NEXTAUTH_URL) {
    errors.push('NEXTAUTH_URL is not configured');
  }
  
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL;
  if (!backendUrl) {
    console.warn('[Auth] No backend URL configured, using default: http://localhost:8000');
  }
  
  return {
    valid: errors.length === 0,
    errors,
  };
}

// ============================================================================
// URL Construction
// ============================================================================

/**
 * Construct authentication endpoint URL
 */
export function getAuthUrl(endpoint: string): string {
  const backendUrl = getBackendUrl();
  // Remove all trailing slashes from backend URL
  let cleanBackendUrl = backendUrl.replace(/\/+$/, '');
  // Normalize any double slashes in the path (but not in protocol)
  const protocolMatch = cleanBackendUrl.match(/^(https?:\/\/)/);
  if (protocolMatch) {
    const protocol = protocolMatch[1];
    const rest = cleanBackendUrl.substring(protocol.length);
    cleanBackendUrl = protocol + rest.replace(/\/+/g, '/');
  }
  
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  return `${cleanBackendUrl}${cleanEndpoint}`;
}

/**
 * Get login endpoint URL
 */
export function getLoginUrl(): string {
  return getAuthUrl('/api/v1/auth/login');
}

/**
 * Get user details endpoint URL
 */
export function getUserDetailsUrl(): string {
  return getAuthUrl('/api/v1/auth/me');
}

// ============================================================================
// Authentication Operations
// ============================================================================

/**
 * Authenticate user with credentials
 */
export async function authenticateUser(credentials: LoginCredentials): Promise<User> {
  if (process.env.NODE_ENV === 'development') {
    console.log('[Auth] Authenticating user:', credentials.username);
  }
  
  // Validate credentials
  if (!credentials.username || !credentials.password) {
    throw createAuthError('validation', 'Username and password are required');
  }
  
  try {
    // Step 1: Login and get tokens
    const loginUrl = getLoginUrl();
    
    if (process.env.NODE_ENV === 'development') {
      console.log('[Auth] Sending login request to:', loginUrl);
    }
    
    const loginRes = await fetch(loginUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: credentials.username,
        password: credentials.password,
      }),
    });
    
    if (!loginRes.ok) {
      const error = await loginRes.json().catch(() => ({}));
      
      if (process.env.NODE_ENV === 'development') {
        console.error('[Auth] Login failed:', error);
      }
      
      if (loginRes.status === 401) {
        throw createAuthError('credentials', error.detail || 'Invalid username or password', loginRes.status);
      } else if (loginRes.status >= 500) {
        throw createAuthError('server', error.detail || 'Server error occurred', loginRes.status);
      } else {
        throw createAuthError('network', error.detail || 'Authentication failed', loginRes.status);
      }
    }
    
    const authData: AuthResponse = await loginRes.json();
    
    if (!authData.access_token) {
      throw createAuthError('server', 'Invalid response from authentication server');
    }
    
    if (process.env.NODE_ENV === 'development') {
      console.log('[Auth] Login successful, fetching user details');
    }
    
    // Step 2: Get user details
    const userDetailsUrl = getUserDetailsUrl();
    const meRes = await fetch(userDetailsUrl, {
      headers: {
        'Authorization': `Bearer ${authData.access_token}`,
      },
    });
    
    if (!meRes.ok) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[Auth] Failed to fetch user details');
      }
      throw createAuthError('server', 'Failed to fetch user details', meRes.status);
    }
    
    const userData: UserResponse = await meRes.json();
    
    if (process.env.NODE_ENV === 'development') {
      console.log('[Auth] User details fetched successfully:', userData.username);
    }
    
    // Combine auth data and user data
    return {
      id: userData.id,
      username: userData.username,
      email: userData.username, // Use username as email for compatibility
      name: userData.username,
      role: userData.role,
      is_active: userData.is_active,
      accessToken: authData.access_token,
      refreshToken: authData.refresh_token,
    };
  } catch (error) {
    if (error instanceof Error && 'type' in error) {
      // Already an AuthError
      throw error;
    }
    
    // Network or unexpected error
    if (process.env.NODE_ENV === 'development') {
      console.error('[Auth] Unexpected error:', error);
    }
    
    throw createAuthError(
      'network',
      error instanceof Error ? error.message : 'An unexpected error occurred'
    );
  }
}

// ============================================================================
// Error Handling
// ============================================================================

/**
 * Create a structured authentication error
 */
export function createAuthError(
  type: AuthErrorType,
  message: string,
  statusCode?: number,
  details?: string
): AuthError & Error {
  const error = new Error(message) as AuthError & Error;
  error.type = type;
  error.message = message;
  error.statusCode = statusCode;
  error.details = details;
  
  return error;
}

/**
 * Get user-friendly error message
 */
export function getUserFriendlyErrorMessage(error: AuthError): string {
  switch (error.type) {
    case 'configuration':
      return 'Authentication is not properly configured. Please contact support.';
    case 'network':
      return 'Unable to connect to the authentication server. Please check your connection and try again.';
    case 'credentials':
      return 'Invalid username or password. Please try again.';
    case 'server':
      return 'The authentication server encountered an error. Please try again later.';
    case 'validation':
      return error.message;
    default:
      return 'An unexpected error occurred. Please try again.';
  }
}

/**
 * Handle authentication error with logging
 */
export function handleAuthError(error: unknown): AuthError {
  if (error instanceof Error && 'type' in error) {
    const authError = error as AuthError;
    
    if (process.env.NODE_ENV === 'development') {
      console.error('[Auth] Authentication error:', {
        type: authError.type,
        message: authError.message,
        statusCode: authError.statusCode,
        details: authError.details,
      });
    }
    
    return authError;
  }
  
  // Unknown error type
  const message = error instanceof Error ? error.message : 'An unexpected error occurred';
  
  if (process.env.NODE_ENV === 'development') {
    console.error('[Auth] Unknown error:', error);
  }
  
  return createAuthError('network', message);
}

// ============================================================================
// Validation
// ============================================================================

/**
 * Validate username format
 */
export function isValidUsername(username: string): boolean {
  // Username should be alphanumeric with optional underscores/hyphens, 3-50 chars
  const usernameRegex = /^[a-zA-Z0-9_-]{3,50}$/;
  return usernameRegex.test(username);
}

/**
 * Validate password strength
 */
export function isValidPassword(password: string): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long');
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }
  
  if (!/[0-9]/.test(password)) {
    errors.push('Password must contain at least one number');
  }
  
  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Validate login credentials
 */
export function validateCredentials(credentials: LoginCredentials): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  if (!credentials.username) {
    errors.push('Username is required');
  } else if (!isValidUsername(credentials.username)) {
    errors.push('Invalid username format (3-50 alphanumeric characters, underscores, or hyphens)');
  }
  
  if (!credentials.password) {
    errors.push('Password is required');
  }
  
  return {
    valid: errors.length === 0,
    errors,
  };
}
