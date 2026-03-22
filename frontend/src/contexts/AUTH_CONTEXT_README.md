# Authentication Context Implementation

## Overview

This authentication context provides a complete JWT-based authentication system for the frontend application, implementing requirements 3.2 and 3.3 from the project specifications.

## Key Features

### 1. JWT Token Storage in httpOnly Cookies (Requirement 3.2)

The authentication system stores JWT tokens securely in httpOnly cookies, which provides several security benefits:

- **XSS Protection**: httpOnly cookies cannot be accessed by JavaScript, preventing XSS attacks from stealing tokens
- **Automatic Cookie Management**: Browsers automatically include cookies in requests
- **Secure Flag**: In production, cookies are marked as secure (HTTPS only)
- **SameSite Protection**: Cookies use SameSite=lax to prevent CSRF attacks

**Implementation Details:**
- Access tokens are stored with 24-hour expiration
- Refresh tokens are stored with 7-day expiration
- Tokens are set via Next.js API routes that proxy to the backend
- All API routes use `credentials: 'include'` to send cookies

### 2. Automatic Token Refresh (Requirement 3.3)

The context implements automatic token refresh to maintain user sessions without requiring re-login:

- **Refresh Interval**: Tokens are refreshed every 20 minutes (well before the 24-hour expiration)
- **Token Rotation**: Each refresh generates a new token pair, invalidating the old refresh token
- **Automatic Cleanup**: Refresh timer is cleared on logout or component unmount
- **Failure Handling**: If refresh fails, user is logged out and redirected to login page

**Implementation Details:**
```typescript
// Token refresh runs every 20 minutes
const TOKEN_REFRESH_INTERVAL = 20 * 60 * 1000;

// Automatic refresh is set up when user is authenticated
useEffect(() => {
  if (user) {
    refreshTimerRef.current = setInterval(() => {
      refreshToken();
    }, TOKEN_REFRESH_INTERVAL);
    
    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }
}, [user, refreshToken]);
```

### 3. React Context for Auth State

The context manages authentication state across the entire application:

```typescript
type AuthContextType = {
  user: User | null;              // Current authenticated user
  loading: boolean;               // Loading state during auth operations
  role: Role | null;              // User's role (ADMIN, USER)
  permissions: Permission[];      // User's permissions based on role
  login: (email, password) => Promise<void>;
  register: (email, password, name) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  isAuthenticated: boolean;       // Convenience flag for auth status
};
```

## Architecture

### API Routes (Next.js Middleware)

The authentication system uses Next.js API routes to handle token management:

1. **POST /api/auth/login**
   - Calls backend login endpoint
   - Stores access_token and refresh_token in httpOnly cookies
   - Returns success/error response

2. **POST /api/auth/logout**
   - Calls backend logout endpoint
   - Clears access_token and refresh_token cookies
   - Returns success response

3. **POST /api/auth/refresh**
   - Calls backend refresh endpoint with refresh_token
   - Updates both access_token and refresh_token cookies (token rotation)
   - Returns success/error response

4. **GET /api/auth/me**
   - Calls backend to get current user info
   - Uses access_token from cookie
   - Returns user data or 401 if not authenticated

5. **POST /api/auth/register**
   - Calls backend register endpoint
   - Returns success/error response
   - User must login separately after registration

### Context Provider Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     AuthProvider                             │
│                                                              │
│  1. On Mount:                                                │
│     - Fetch current user (/api/auth/me)                     │
│     - Set user state if authenticated                        │
│     - Set loading to false                                   │
│                                                              │
│  2. When User Authenticated:                                 │
│     - Set up automatic token refresh timer (20 min)         │
│     - Update role and permissions                            │
│                                                              │
│  3. On Login:                                                │
│     - Call /api/auth/login                                   │
│     - Fetch current user                                     │
│     - Redirect to dashboard                                  │
│                                                              │
│  4. On Logout:                                               │
│     - Clear refresh timer                                    │
│     - Call /api/auth/logout                                  │
│     - Clear user state                                       │
│     - Redirect to home                                       │
│                                                              │
│  5. On Token Refresh:                                        │
│     - Call /api/auth/refresh                                 │
│     - Fetch updated user data                                │
│     - If fails, logout user                                  │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Setup

Wrap your application with the AuthProvider:

```typescript
// app/layout.tsx
import { AuthProvider } from '@/contexts/AuthContext';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

### Using the Auth Context

```typescript
import { useAuth } from '@/contexts/AuthContext';

function MyComponent() {
  const { user, loading, isAuthenticated, login, logout } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <div>Please log in</div>;
  }

  return (
    <div>
      <p>Welcome, {user.name}!</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

### Protected Routes

```typescript
'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function ProtectedPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return <div>Protected content</div>;
}
```

### Role-Based Access Control

```typescript
import { useAuth } from '@/contexts/AuthContext';
import { Role, Permission } from '@/types/rbac';

function AdminPanel() {
  const { role, permissions } = useAuth();

  if (role !== Role.ADMIN) {
    return <div>Access denied</div>;
  }

  return <div>Admin panel content</div>;
}

function CreateProjectButton() {
  const { permissions } = useAuth();

  if (!permissions.includes(Permission.CREATE_PROJECT)) {
    return null;
  }

  return <button>Create Project</button>;
}
```

## Security Considerations

### httpOnly Cookies

- **Pros**: Cannot be accessed by JavaScript, preventing XSS token theft
- **Cons**: Requires server-side API routes to manage cookies
- **Implementation**: Next.js API routes act as a secure proxy to the backend

### Token Rotation

- Each refresh generates a new token pair
- Old refresh tokens are invalidated
- Prevents token replay attacks
- Limits impact of token theft

### Automatic Refresh

- Tokens are refreshed every 20 minutes
- Prevents session expiration during active use
- Fails gracefully if refresh fails (user is logged out)

### CORS and SameSite

- Cookies use SameSite=lax to prevent CSRF
- API routes are on the same domain as the frontend
- Backend CORS is configured to allow credentials

## Environment Variables

Required environment variables:

```env
# Backend API URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# NextAuth secret (if still using NextAuth for other features)
NEXTAUTH_SECRET=your-secret-key
```

## Testing

The authentication context includes comprehensive unit tests:

```bash
npm test -- AuthContext.test.tsx
```

Tests cover:
- Initial loading state
- Fetching current user on mount
- Successful login
- Failed login
- Logout
- Token refresh success
- Token refresh failure
- Role-based permissions

## Migration from NextAuth

This implementation replaces NextAuth with a custom JWT-based authentication system. Key differences:

| Feature | NextAuth | Custom Auth Context |
|---------|----------|---------------------|
| Token Storage | Session cookies | httpOnly cookies (JWT) |
| Token Refresh | Automatic (built-in) | Manual (20-min interval) |
| Session Management | Server-side | Client-side with backend validation |
| Flexibility | Limited | Full control |
| Backend Integration | Requires adapter | Direct API calls |

## Troubleshooting

### Tokens not being sent to backend

- Ensure `credentials: 'include'` is set in all fetch calls
- Check that cookies are being set correctly in API routes
- Verify CORS configuration allows credentials

### Automatic refresh not working

- Check that the refresh timer is being set up correctly
- Verify the refresh endpoint is working
- Check browser console for errors

### User logged out unexpectedly

- Check if refresh token has expired (7 days)
- Verify backend refresh endpoint is working
- Check for network errors during refresh

## Future Enhancements

Potential improvements for future iterations:

1. **Token Expiration Warning**: Show a warning before token expires
2. **Refresh on Activity**: Refresh token on user activity instead of fixed interval
3. **Multiple Tab Support**: Synchronize auth state across browser tabs
4. **Remember Me**: Extend refresh token expiration for "remember me" option
5. **Biometric Auth**: Add support for WebAuthn/FIDO2
