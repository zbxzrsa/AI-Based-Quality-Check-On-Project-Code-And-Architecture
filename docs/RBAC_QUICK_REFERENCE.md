# RBAC Quick Reference Card

## 5 Roles at a Glance

```
┌─────────────────────────────────────────────────────────────────�?
�?                        ROLE HIERARCHY                          �?
├─────────────────────────────────────────────────────────────────�?
�?                                                                �?
�? ADMIN ──────────────────────────────────────────────────────  �?
�?   �? Full system control �?All permissions                    �?
�?   �?                                                           �?
�?   ├─�?MANAGER ────────────────────────────────────────────    �?
�?   �?    �? Project oversight & ROI �?7 permissions            �?
�?   �?    �?                                                     �?
�?   �?    ├─�?REVIEWER ──────────────────────────────────       �?
�?   �?    �?    �? Read/Write analysis �?4 permissions          �?
�?   �?    �?    �?                                              �?
�?   �?    ├─�?PROGRAMMER ────────────────────────────           �?
�?   �?          �? CRUD own branch �?5 permissions              �?
�?   �?          �?                                              �?
�?   └─────────�?VISITOR ──────────────────────────              �?
�?                 Read-only grants �?1 permission               �?
�?                                                                �?
└─────────────────────────────────────────────────────────────────�?
```

## Permission Matrix

| Permission | 👑 ADMIN | 📊 MANAGER | 🔍 REVIEWER | 💻 PROGRAMMER | 👁�?VISITOR |
|-----------|:--------:|:----------:|:-----------:|:-------------:|:----------:|
| **User Management** |
| CREATE_USER | �?| �?| �?| �?| �?|
| DELETE_USER | �?| �?| �?| �?| �?|
| UPDATE_USER | �?| �?| �?| �?| �?|
| VIEW_USER | �?| �?| �?| �?| �?|
| **Project Management** |
| CREATE_PROJECT | �?| �?| �?| �?| �?|
| DELETE_PROJECT | �?| �?| �?| �?| �?|
| UPDATE_PROJECT | �?| �?| �?| �?| �?|
| VIEW_PROJECT | �?| �?| �?| �?| �?|
| **Configuration** |
| MODIFY_CONFIG | �?| �?| �?| �?| �?|
| VIEW_CONFIG | �?| �?| �?| �?| �?|
| **Reports** |
| EXPORT_REPORT | �?| �?| �?| �?| �?|

## Default Test Accounts

```bash
# All accounts use password: change-me-strong-password

Username: admin      Role: ADMIN       ID: admin-0000-0000-0000-000000000001
Username: manager    Role: MANAGER     ID: mngr-0000-0000-0000-000000000002
Username: reviewer   Role: REVIEWER    ID: revw-0000-0000-0000-000000000003
Username: programmer Role: PROGRAMMER  ID: prog-0000-0000-0000-000000000004
Username: visitor    Role: VISITOR     ID: visit-0000-0000-0000-000000000005
```

## Common Use Cases

### 👑 ADMIN - System Administrator
```
�?Manage all users and roles
�?Configure system settings
�?Access all projects
�?Full CRUD on everything
```

### 📊 MANAGER - Project Manager
```
�?Create and delete projects
�?View team members
�?Export ROI reports
�?Monitor project health
�?Cannot manage users
�?Cannot modify system config
```

### 🔍 REVIEWER - Code Reviewer
```
�?Review code changes
�?Update analysis settings
�?Export quality reports
�?View project details
�?Cannot create/delete projects
�?Cannot manage users
```

### 💻 PROGRAMMER - Developer
```
�?Create own projects
�?Update own projects
�?View granted projects
�?Export analysis reports
�?Cannot delete projects
�?Cannot access others' projects (without grant)
```

### 👁�?VISITOR - Stakeholder
```
�?View granted projects only
�?Cannot modify anything
�?Cannot export reports
�?Cannot create projects
```

## Quick Commands

### Check User Role
```sql
SELECT username, role FROM rbac_users WHERE username = 'john.doe';
```

### Assign Role (Admin Only)
```sql
UPDATE rbac_users 
SET role = 'MANAGER', updated_at = NOW() 
WHERE username = 'john.doe';
```

### List Users by Role
```sql
SELECT role, COUNT(*) as count 
FROM rbac_users 
WHERE is_active = true 
GROUP BY role 
ORDER BY count DESC;
```

### Grant Project Access
```sql
INSERT INTO project_access (project_id, user_id, granted_by, created_at)
VALUES (
  'project-uuid',
  'user-uuid',
  'admin-uuid',
  NOW()
);
```

## API Examples

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "programmer", "password": "change-me-strong-password"}'
```

### Check Permission
```bash
curl -X GET http://localhost:8000/api/auth/permissions \
  -H "Authorization: Bearer {token}"
```

### Assign Role (Admin Only)
```bash
curl -X PUT http://localhost:8000/api/users/{user_id}/role \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"role": "REVIEWER"}'
```

## Frontend Permission Check

```typescript
import { usePermission } from '@/hooks/usePermission';
import { Permission } from '@/types/rbac';

function MyComponent() {
  const { hasPermission } = usePermission();
  
  return (
    <>
      {hasPermission(Permission.CREATE_PROJECT) && (
        <button>Create Project</button>
      )}
      
      {hasPermission(Permission.EXPORT_REPORT) && (
        <button>Export Report</button>
      )}
    </>
  );
}
```

## Troubleshooting

### "Permission Denied" Error
1. Check user's current role: `SELECT role FROM rbac_users WHERE id = 'user-id'`
2. Verify permission mapping in `ROLE_PERMISSIONS`
3. Check if user is active: `SELECT is_active FROM rbac_users WHERE id = 'user-id'`
4. Clear browser cache and re-login

### Role Not Updating
1. Verify database update: `SELECT role, updated_at FROM rbac_users WHERE id = 'user-id'`
2. User must logout and login again for changes to take effect
3. Check JWT token expiration

### Cannot Access Project
1. Check project ownership: `SELECT owner_id FROM projects WHERE id = 'project-id'`
2. Check access grants: `SELECT * FROM project_access WHERE user_id = 'user-id' AND project_id = 'project-id'`
3. Verify user role has VIEW_PROJECT permission

## Best Practices

�?**DO:**
- Use MANAGER for project leads
- Use REVIEWER for QA team
- Use PROGRAMMER for developers
- Use VISITOR for external stakeholders
- Change default passwords immediately
- Regularly audit user roles
- Log role changes

�?**DON'T:**
- Give ADMIN role to regular users
- Share account credentials
- Use default passwords in production
- Assign multiple roles to one user
- Bypass permission checks in code

## Related Documentation

- 📖 [Full RBAC Documentation](RBAC_ROLES.md)
- 🔄 [Migration Guide](RBAC_MIGRATION_GUIDE.md)
- 🏗�?[Architecture Documentation](ARCHITECTURE.md)

---

**Last Updated:** 2026-03-01  
**Version:** 2.0.0
