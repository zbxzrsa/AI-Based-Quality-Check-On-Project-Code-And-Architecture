# RBAC Authentication Components

This directory contains the frontend RBAC (Role-Based Access Control) integration components for the enterprise authentication system.

## Components

### RBACGuard

Route protection component based on roles and permissions.

**Props:**
- `requiredRole?: Role` - Required user role to access the route
- `requiredPermission?: Permission` - Required permission to access the route
- `fallback?: React.ReactNode` - Optional fallback content when unauthorized

**Features:**
- Redirects to `/login` when session is expired
- Redirects to `/unauthorized` when role/permission requirements are not met
- Shows loading state while checking authentication
- Supports both role-based and permission-based protection

**Example Usage:**

```tsx
import { RBACGuard } from '@/components/auth/RBACGuard';
import { Role, Permission } from '@/types/rbac';

// Protect route with role requirement
export default function AdminPage() {
  return (
    <RBACGuard requiredRole={Role.ADMIN}>
      <div>Admin Content</div>
    </RBACGuard>
  );
}

// Protect route with permission requirement
export default function SettingsPage() {
  return (
    <RBACGuard requiredPermission={Permission.MODIFY_CONFIG}>
      <div>Settings Content</div>
    </RBACGuard>
  );
}

// With custom fallback
export default function ProjectPage() {
  return (
    <RBACGuard 
      requiredPermission={Permission.VIEW_PROJECTS}
      fallback={<div>You don't have access to projects</div>}
    >
      <div>Project Content</div>
    </RBACGuard>
  );
}
```

### PermissionCheck

Conditional rendering component based on permissions and roles.

**Props:**
- `permission?: Permission` - Required permission to render children
- `role?: Role` - Required role to render children
- `fallback?: React.ReactNode` - Optional fallback content when unauthorized (default: null)

**Features:**
- Conditionally renders UI elements based on permissions
- Hides elements from DOM when user lacks permission
- Supports both role-based and permission-based checks
- Lightweight component for inline permission checks

**Example Usage:**

```tsx
import { PermissionCheck } from '@/components/auth/PermissionCheck';
import { Permission, Role } from '@/types/rbac';

// Hide delete button for users without permission
<PermissionCheck permission={Permission.DELETE_PROJECT}>
  <Button variant="destructive">Delete Project</Button>
</PermissionCheck>

// Show admin panel only for admins
<PermissionCheck role={Role.ADMIN}>
  <AdminPanel />
</PermissionCheck>

// With fallback content
<PermissionCheck 
  permission={Permission.MODIFY_CONFIG}
  fallback={<span>Read-only mode</span>}
>
  <Button>Edit Settings</Button>
</PermissionCheck>

// Multiple permission checks
<div className="flex gap-2">
  <PermissionCheck permission={Permission.VIEW_PROJECTS}>
    <Button>View</Button>
  </PermissionCheck>
  
  <PermissionCheck permission={Permission.MODIFY_PROJECT}>
    <Button>Edit</Button>
  </PermissionCheck>
  
  <PermissionCheck permission={Permission.DELETE_PROJECT}>
    <Button variant="destructive">Delete</Button>
  </PermissionCheck>
</div>
```

## Hooks

### useRole

Hook for checking user roles.

**Returns:**
- `hasRole: (requiredRole: Role) => boolean` - Function to check if user has a specific role
- `currentRole: Role | null` - Current user's role
- `loading: boolean` - Loading state

**Example Usage:**

```tsx
import { useRole } from '@/hooks/useRole';
import { Role } from '@/types/rbac';

function MyComponent() {
  const { hasRole, currentRole, loading } = useRole();
  
  if (loading) return <div>Loading...</div>;
  
  if (hasRole(Role.ADMIN)) {
    return <AdminDashboard />;
  }
  
  return <UserDashboard role={currentRole} />;
}
```

### usePermission

Hook for checking user permissions.

**Returns:**
- `hasPermission: (permission: Permission) => boolean` - Function to check if user has a specific permission
- `loading: boolean` - Loading state

**Example Usage:**

```tsx
import { usePermission } from '@/hooks/usePermission';
import { Permission } from '@/types/rbac';

function ProjectActions({ projectId }: { projectId: string }) {
  const { hasPermission, loading } = usePermission();
  
  if (loading) return <div>Loading...</div>;
  
  return (
    <div className="flex gap-2">
      {hasPermission(Permission.MODIFY_PROJECT) && (
        <Button onClick={() => editProject(projectId)}>Edit</Button>
      )}
      
      {hasPermission(Permission.DELETE_PROJECT) && (
        <Button variant="destructive" onClick={() => deleteProject(projectId)}>
          Delete
        </Button>
      )}
    </div>
  );
}
```

## Types

### Role Enum

```typescript
enum Role {
  ADMIN = 'admin',
  USER = 'user',
}
```

### Permission Enum

```typescript
enum Permission {
  VIEW_PROJECTS = 'VIEW_PROJECTS',
  CREATE_PROJECT = 'CREATE_PROJECT',
  MODIFY_PROJECT = 'MODIFY_PROJECT',
  DELETE_PROJECT = 'DELETE_PROJECT',
  VIEW_USERS = 'VIEW_USERS',
  CREATE_USER = 'CREATE_USER',
  MODIFY_USER = 'MODIFY_USER',
  DELETE_USER = 'DELETE_USER',
  VIEW_REVIEWS = 'VIEW_REVIEWS',
  CREATE_REVIEW = 'CREATE_REVIEW',
  MODIFY_REVIEW = 'MODIFY_REVIEW',
  MODIFY_CONFIG = 'MODIFY_CONFIG',
}
```

## Role-Permission Mapping

The system uses the following role-permission mapping:

**ADMIN:**
- All permissions (full access)

**USER:**
- VIEW_PROJECTS (read-only)
- VIEW_REVIEWS (read-only)

## AuthContext Updates

The AuthContext has been updated to include RBAC support:

```typescript
type AuthContextType = {
  user: User | null;
  session: Session | null;
  loading: boolean;
  role: Role | null;                    // NEW: Current user role
  permissions: Permission[];            // NEW: User permissions
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;    // NEW: Token refresh
};
```

## Best Practices

1. **Use RBACGuard for entire pages/routes:**
   ```tsx
   // Wrap entire page component
   export default function AdminPage() {
     return (
       <RBACGuard requiredRole={Role.ADMIN}>
         <PageContent />
       </RBACGuard>
     );
   }
   ```

2. **Use PermissionCheck for UI elements:**
   ```tsx
   // Hide/show specific buttons or sections
   <PermissionCheck permission={Permission.DELETE_PROJECT}>
     <DeleteButton />
   </PermissionCheck>
   ```

3. **Use hooks for complex logic:**
   ```tsx
   // When you need to perform actions based on permissions
   const { hasPermission } = usePermission();
   
   const handleAction = () => {
     if (hasPermission(Permission.MODIFY_PROJECT)) {
       // Perform action
     } else {
       // Show error
     }
   };
   ```

4. **Combine role and permission checks:**
   ```tsx
  // For fine-grained control
  <RBACGuard 
     requiredRole={Role.ADMIN}
     requiredPermission={Permission.MODIFY_PROJECT}
   >
     <ProjectEditor />
   </RBACGuard>
   ```

## Testing

The components include comprehensive test coverage:

- **Unit tests:** Test specific scenarios and edge cases
- **Property-based tests:** Test universal properties across all inputs using fast-check

Run tests:
```bash
npm test -- --testPathPattern="RBACGuard|PermissionCheck"
```

## Security Considerations

1. **Client-side checks are not sufficient:** Always validate permissions on the backend
2. **Session expiration:** The system automatically redirects to login when sessions expire
3. **Token refresh:** Tokens are refreshed automatically by NextAuth
4. **Unauthorized access:** Users are redirected to `/unauthorized` when they lack permissions

## Integration with Backend

The frontend RBAC system is designed to work with the backend RBAC API:

- **Login endpoint:** `/api/v1/auth/login`
- **User details:** `/api/v1/auth/me`
- **Token refresh:** Handled by NextAuth automatically

Ensure the backend returns user role information in the authentication response.
