# RouteGuard Component

## Overview

The `RouteGuard` component provides route protection for the Next.js application by checking authentication and authorization before rendering protected content.

## Requirements Addressed

- **Requirement 3.4**: WHEN a user navigates to a protected route without authentication, THE Frontend_Application SHALL redirect to the login page
- **Requirement 3.5**: WHEN a user lacks permission for an action, THE Frontend_Application SHALL display a 403 Forbidden message

## Features

### 1. Authentication Check
- Verifies user is authenticated before rendering protected content
- Redirects unauthenticated users to login page
- Preserves intended destination URL for post-login redirect

### 2. Role-Based Access Control
- Checks if user has required role
- Redirects unauthorized users to `/unauthorized` page (403 Forbidden)

### 3. Permission-Based Access Control
- Checks if user has required permission
- Redirects unauthorized users to `/unauthorized` page (403 Forbidden)

### 4. Loading State
- Shows loading spinner while authentication state is being determined
- Prevents flash of unauthorized content

## Usage

### Basic Authentication Protection

Protect a route requiring only authentication:

```tsx
import { RouteGuard } from '@/components/auth/RouteGuard';

export default function ProtectedPage() {
  return (
    <RouteGuard>
      <div>This content is only visible to authenticated users</div>
    </RouteGuard>
  );
}
```

### Role-Based Protection

Protect a route requiring a specific role:

```tsx
import { RouteGuard } from '@/components/auth/RouteGuard';
import { Role } from '@/types/rbac';

export default function AdminPage() {
  return (
    <RouteGuard requiredRole={Role.ADMIN}>
      <div>This content is only visible to administrators</div>
    </RouteGuard>
  );
}
```

### Permission-Based Protection

Protect a route requiring a specific permission:

```tsx
import { RouteGuard } from '@/components/auth/RouteGuard';
import { Permission } from '@/types/rbac';

export default function ProjectManagementPage() {
  return (
    <RouteGuard requiredPermission={Permission.MODIFY_PROJECT}>
      <div>This content is only visible to users who can modify projects</div>
    </RouteGuard>
  );
}
```

### Custom Redirect Path

Specify a custom redirect path for unauthenticated users:

```tsx
import { RouteGuard } from '@/components/auth/RouteGuard';

export default function SpecialPage() {
  return (
    <RouteGuard redirectTo="/special-login">
      <div>Protected content</div>
    </RouteGuard>
  );
}
```

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `React.ReactNode` | Yes | - | Content to render if authorized |
| `requiredRole` | `Role` | No | - | Role required to access the route |
| `requiredPermission` | `Permission` | No | - | Permission required to access the route |
| `redirectTo` | `string` | No | `/login` | Path to redirect unauthenticated users |

## Behavior

### Authentication Flow

1. **Loading State**: While authentication state is loading, displays a loading spinner
2. **Unauthenticated**: Redirects to login page with `returnUrl` query parameter
3. **Authenticated**: Proceeds to authorization checks

### Authorization Flow

1. **Role Check**: If `requiredRole` is specified, verifies user has that role
2. **Permission Check**: If `requiredPermission` is specified, verifies user has that permission
3. **Unauthorized**: Redirects to `/unauthorized` page (403 Forbidden)
4. **Authorized**: Renders protected content

### Return URL Handling

When redirecting unauthenticated users to login:
- Current path is stored as `returnUrl` query parameter
- After successful login, user is redirected back to intended destination
- Example: `/login?returnUrl=%2Fprojects%2F123`

## Integration with AuthContext

The RouteGuard component integrates with the `AuthContext` to access:
- `user`: Current user object with role information
- `loading`: Authentication loading state
- `isAuthenticated`: Boolean indicating if user is authenticated
- `permissions`: Array of user's permissions based on their role

## Examples

### Protecting Multiple Routes in a Layout

```tsx
// app/admin/layout.tsx
import { RouteGuard } from '@/components/auth/RouteGuard';
import { Role } from '@/types/rbac';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RouteGuard requiredRole={Role.ADMIN}>
      <div className="admin-layout">
        <AdminSidebar />
        <main>{children}</main>
      </div>
    </RouteGuard>
  );
}
```

### Combining with Other Guards

```tsx
import { RouteGuard } from '@/components/auth/RouteGuard';
import { PermissionCheck } from '@/components/auth/PermissionCheck';
import { Permission } from '@/types/rbac';

export default function ProjectPage() {
  return (
    <RouteGuard>
      <div>
        <h1>Project Details</h1>
        
        {/* All authenticated users can see this */}
        <ProjectInfo />
        
        {/* Only users with MODIFY_PROJECT permission can see this */}
        <PermissionCheck permission={Permission.MODIFY_PROJECT}>
          <ProjectEditButton />
        </PermissionCheck>
      </div>
    </RouteGuard>
  );
}
```

## Testing

### Unit Tests

Test the RouteGuard component with different authentication states:

```tsx
import { render, screen } from '@testing-library/react';
import { RouteGuard } from './RouteGuard';
import { AuthContext } from '@/contexts/AuthContext';
import { Role } from '@/types/rbac';

describe('RouteGuard', () => {
  it('shows loading state while checking authentication', () => {
    const mockAuthContext = {
      user: null,
      loading: true,
      isAuthenticated: false,
      permissions: [],
    };

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('redirects unauthenticated users to login', () => {
    const mockAuthContext = {
      user: null,
      loading: false,
      isAuthenticated: false,
      permissions: [],
    };

    const mockPush = jest.fn();
    jest.mock('next/navigation', () => ({
      useRouter: () => ({ push: mockPush }),
      usePathname: () => '/protected',
    }));

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      </AuthContext.Provider>
    );

    expect(mockPush).toHaveBeenCalledWith('/login?returnUrl=%2Fprotected');
  });

  it('renders content for authenticated users', () => {
    const mockAuthContext = {
      user: { id: '1', email: 'test@example.com', role: Role.USER },
      loading: false,
      isAuthenticated: true,
      permissions: [],
    };

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('redirects users without required role to unauthorized', () => {
    const mockAuthContext = {
      user: { id: '1', email: 'test@example.com', role: Role.USER },
      loading: false,
      isAuthenticated: true,
      permissions: [],
    };

    const mockPush = jest.fn();
    jest.mock('next/navigation', () => ({
      useRouter: () => ({ push: mockPush }),
      usePathname: () => '/admin',
    }));

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <RouteGuard requiredRole={Role.ADMIN}>
          <div>Admin Content</div>
        </RouteGuard>
      </AuthContext.Provider>
    );

    expect(mockPush).toHaveBeenCalledWith('/unauthorized');
  });
});
```

## Related Components

- **PermissionCheck**: Conditional rendering based on permissions (doesn't redirect)
- **RBACGuard**: Alternative guard component with different API
- **AuthContext**: Provides authentication state and methods

## Best Practices

1. **Use at Layout Level**: Apply RouteGuard at the layout level to protect entire sections
2. **Combine with PermissionCheck**: Use RouteGuard for page-level protection and PermissionCheck for component-level conditional rendering
3. **Specific Permissions**: Prefer `requiredPermission` over `requiredRole` for more granular control
4. **Loading States**: Always handle loading states to prevent flash of unauthorized content
5. **Error Boundaries**: Wrap protected routes in error boundaries to handle unexpected errors

## Troubleshooting

### Issue: Infinite redirect loop
**Solution**: Ensure the redirect path (e.g., `/login`) is not itself protected by a RouteGuard

### Issue: Flash of unauthorized content
**Solution**: The RouteGuard returns `null` during loading and unauthorized states to prevent this

### Issue: User redirected to login after successful authentication
**Solution**: Check that the AuthContext is properly initialized and `isAuthenticated` is correctly set

## Future Enhancements

- [ ] Support for multiple required permissions (AND/OR logic)
- [ ] Support for custom fallback components instead of redirects
- [ ] Integration with server-side authentication checks
- [ ] Audit logging for unauthorized access attempts
