# RouteGuard Usage Examples

This document provides practical examples of using the `RouteGuard` component to protect routes in the Next.js application.

## Table of Contents

1. [Basic Authentication Protection](#basic-authentication-protection)
2. [Role-Based Protection](#role-based-protection)
3. [Permission-Based Protection](#permission-based-protection)
4. [Layout-Level Protection](#layout-level-protection)
5. [Combining with Conditional Rendering](#combining-with-conditional-rendering)
6. [Custom Redirect Paths](#custom-redirect-paths)

## Basic Authentication Protection

### Example 1: Protected Dashboard

Protect the dashboard page so only authenticated users can access it:

```tsx
// app/dashboard/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { MainLayout } from '@/components/layout/main-layout';

export default function DashboardPage() {
  return (
    <RouteGuard>
      <MainLayout>
        <div>
          <h1>Dashboard</h1>
          <p>Welcome to your dashboard!</p>
        </div>
      </MainLayout>
    </RouteGuard>
  );
}
```

**Behavior:**
- Unauthenticated users → Redirected to `/login?returnUrl=%2Fdashboard`
- Authenticated users → See dashboard content

### Example 2: Protected Profile Page

```tsx
// app/profile/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';

export default function ProfilePage() {
  return (
    <RouteGuard>
      <div>
        <h1>My Profile</h1>
        <p>Edit your profile information</p>
      </div>
    </RouteGuard>
  );
}
```

## Role-Based Protection

### Example 3: Admin-Only Page

Restrict access to administrators only:

```tsx
// app/admin/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { Role } from '@/types/rbac';

export default function AdminPage() {
  return (
    <RouteGuard requiredRole={Role.ADMIN}>
      <div>
        <h1>Admin Panel</h1>
        <p>Manage users and system settings</p>
      </div>
    </RouteGuard>
  );
}
```

**Behavior:**
- Unauthenticated users → Redirected to `/login`
- Authenticated non-admin users → Redirected to `/unauthorized` (403)
- Admin users → See admin panel

### Example 4: Admin-Only Code Review Operations

```tsx
// app/code-review/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { Role } from '@/types/rbac';

export default function CodeReviewPage() {
  return (
    <RouteGuard requiredRole={Role.ADMIN}>
      <div>
        <h1>Code Review</h1>
        <p>Manage privileged code review operations</p>
      </div>
    </RouteGuard>
  );
}
```

## Permission-Based Protection

### Example 5: Project Management Page

Require specific permission to access:

```tsx
// app/projects/manage/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { Permission } from '@/types/rbac';

export default function ProjectManagementPage() {
  return (
    <RouteGuard requiredPermission={Permission.MODIFY_PROJECT}>
      <div>
        <h1>Manage Projects</h1>
        <p>Create, edit, and delete projects</p>
      </div>
    </RouteGuard>
  );
}
```

**Behavior:**
- Users without `MODIFY_PROJECT` permission → Redirected to `/unauthorized`
- Users with permission → See project management interface

### Example 6: User Management

```tsx
// app/users/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { Permission } from '@/types/rbac';

export default function UserManagementPage() {
  return (
    <RouteGuard requiredPermission={Permission.VIEW_USERS}>
      <div>
        <h1>User Management</h1>
        <p>View and manage system users</p>
      </div>
    </RouteGuard>
  );
}
```

## Layout-Level Protection

### Example 7: Protected Section with Shared Layout

Protect an entire section of the app by applying RouteGuard at the layout level:

```tsx
// app/admin/layout.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { Role } from '@/types/rbac';
import { AdminSidebar } from '@/components/admin/AdminSidebar';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RouteGuard requiredRole={Role.ADMIN}>
      <div className="flex">
        <AdminSidebar />
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </RouteGuard>
  );
}
```

**Benefits:**
- All pages under `/admin/*` are automatically protected
- No need to add RouteGuard to each individual page
- Shared layout components (sidebar, header) are also protected

### Example 8: Multi-Level Protection

```tsx
// app/projects/layout.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { Permission } from '@/types/rbac';

export default function ProjectsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RouteGuard requiredPermission={Permission.VIEW_PROJECTS}>
      <div className="projects-layout">
        <nav>Project Navigation</nav>
        {children}
      </div>
    </RouteGuard>
  );
}
```

Then individual pages can add additional restrictions:

```tsx
// app/projects/edit/[id]/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { Permission } from '@/types/rbac';

export default function EditProjectPage() {
  return (
    <RouteGuard requiredPermission={Permission.MODIFY_PROJECT}>
      <div>
        <h1>Edit Project</h1>
        {/* Edit form */}
      </div>
    </RouteGuard>
  );
}
```

## Combining with Conditional Rendering

### Example 9: Page with Mixed Access Levels

Use RouteGuard for page access and PermissionCheck for conditional rendering:

```tsx
// app/projects/[id]/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { PermissionCheck } from '@/components/auth/PermissionCheck';
import { Permission } from '@/types/rbac';

export default function ProjectDetailPage() {
  return (
    <RouteGuard>
      <div>
        <h1>Project Details</h1>
        
        {/* All authenticated users can see this */}
        <section>
          <h2>Overview</h2>
          <p>Project information...</p>
        </section>
        
        {/* Only users with MODIFY_PROJECT can see this */}
        <PermissionCheck permission={Permission.MODIFY_PROJECT}>
          <section>
            <h2>Edit Project</h2>
            <button>Edit</button>
            <button>Delete</button>
          </section>
        </PermissionCheck>
        
        {/* Only users with CREATE_REVIEW can see this */}
        <PermissionCheck permission={Permission.CREATE_REVIEW}>
          <section>
            <h2>Start Review</h2>
            <button>New Review</button>
          </section>
        </PermissionCheck>
      </div>
    </RouteGuard>
  );
}
```

### Example 10: Role-Based UI Variations

```tsx
// app/dashboard/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { useAuth } from '@/contexts/AuthContext';
import { Role } from '@/types/rbac';

export default function DashboardPage() {
  const { role } = useAuth();
  
  return (
    <RouteGuard>
      <div>
        <h1>Dashboard</h1>
        
        {/* Show different content based on role */}
        {role === Role.ADMIN && (
          <section>
            <h2>Admin Dashboard</h2>
            <p>System statistics and user management</p>
          </section>
        )}
        
        {role === Role.USER && (
          <section>
            <h2>User Dashboard</h2>
            <p>Your projects and reviews</p>
          </section>
        )}
      </div>
    </RouteGuard>
  );
}
```

## Custom Redirect Paths

### Example 11: Special Login Page

Redirect to a custom login page for specific sections:

```tsx
// app/api-access/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';

export default function ApiAccessPage() {
  return (
    <RouteGuard redirectTo="/api-login">
      <div>
        <h1>API Access</h1>
        <p>Manage your API keys</p>
      </div>
    </RouteGuard>
  );
}
```

**Behavior:**
- Unauthenticated users → Redirected to `/api-login?returnUrl=%2Fapi-access`
- After login, redirected back to `/api-access`

### Example 12: Beta Features with Special Access

```tsx
// app/beta/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { Permission } from '@/types/rbac';

export default function BetaFeaturesPage() {
  return (
    <RouteGuard 
      requiredPermission={Permission.VIEW_BETA_FEATURES}
      redirectTo="/beta-signup"
    >
      <div>
        <h1>Beta Features</h1>
        <p>Try our latest experimental features</p>
      </div>
    </RouteGuard>
  );
}
```

## Advanced Patterns

### Example 13: Nested Protection

Combine multiple RouteGuards for complex authorization:

```tsx
// app/admin/users/[id]/edit/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { Role, Permission } from '@/types/rbac';

export default function EditUserPage() {
  return (
    <RouteGuard requiredRole={Role.ADMIN}>
      <RouteGuard requiredPermission={Permission.MODIFY_USER}>
        <div>
          <h1>Edit User</h1>
          {/* Edit form */}
        </div>
      </RouteGuard>
    </RouteGuard>
  );
}
```

**Note:** While this works, it's more efficient to use a single RouteGuard with both requirements if the component supports it in the future.

### Example 14: Dynamic Route Protection

Protect dynamic routes with parameter-based logic:

```tsx
// app/projects/[id]/page.tsx
'use client';

import { RouteGuard } from '@/components/auth/RouteGuard';
import { useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Permission } from '@/types/rbac';

export default function ProjectPage() {
  const params = useParams();
  const { user } = useAuth();
  
  return (
    <RouteGuard requiredPermission={Permission.VIEW_PROJECTS}>
      <div>
        <h1>Project {params.id}</h1>
        {/* Project content */}
      </div>
    </RouteGuard>
  );
}
```

## Testing Protected Routes

### Example 15: Testing RouteGuard Integration

```tsx
// __tests__/protected-page.test.tsx
import { render, screen } from '@testing-library/react';
import { AuthContext } from '@/contexts/AuthContext';
import DashboardPage from '@/app/dashboard/page';
import { Role } from '@/types/rbac';

describe('Protected Dashboard Page', () => {
  it('redirects unauthenticated users', () => {
    const mockAuthContext = {
      user: null,
      loading: false,
      isAuthenticated: false,
      permissions: [],
      role: null,
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    };

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <DashboardPage />
      </AuthContext.Provider>
    );

    // Content should not be visible
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
  });

  it('shows content to authenticated users', () => {
    const mockAuthContext = {
      user: {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: Role.USER,
        is_active: true,
      },
      loading: false,
      isAuthenticated: true,
      permissions: [],
      role: Role.USER,
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    };

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <DashboardPage />
      </AuthContext.Provider>
    );

    // Content should be visible
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });
});
```

## Best Practices

1. **Apply at Layout Level**: For sections with multiple protected pages, apply RouteGuard at the layout level
2. **Use Specific Permissions**: Prefer `requiredPermission` over `requiredRole` for more granular control
3. **Combine with Conditional Rendering**: Use RouteGuard for page access and PermissionCheck for UI elements
4. **Handle Loading States**: RouteGuard automatically handles loading states, preventing flash of unauthorized content
5. **Test Protection**: Always test that protected routes properly redirect unauthorized users
6. **Document Requirements**: Comment which requirement each RouteGuard addresses

## Common Pitfalls

1. **Don't protect the login page**: This creates an infinite redirect loop
2. **Don't nest too many guards**: Use a single guard with multiple requirements when possible
3. **Don't forget to wrap the entire page**: Make sure all content is inside the RouteGuard
4. **Don't rely solely on client-side protection**: Always validate on the server as well

## Related Documentation

- [RouteGuard README](./ROUTE_GUARD_README.md) - Complete component documentation
- [AuthContext Documentation](../../contexts/AUTH_CONTEXT_README.md) - Authentication context
- [RBAC Types](../../types/rbac.ts) - Role and permission definitions
