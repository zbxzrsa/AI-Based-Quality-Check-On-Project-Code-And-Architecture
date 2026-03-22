# RBAC Role Definitions

This document describes the 5 role types implemented in the system and their respective permissions.

## Role Hierarchy

```
ADMIN (Full Control)
  ‚Ü?
MANAGER (Project Oversight & ROI)
  ‚Ü?
REVIEWER (Read/Write Analysis)
  ‚Ü?
PROGRAMMER (CRUD Own Branch)
  ‚Ü?
VISITOR (Read-Only)
```

## Role Details

### 1. ADMIN - Full System Control
**Description:** System administrators with complete access to all features and data.

**Permissions:**
- ‚ú?CREATE_USER - Create new user accounts
- ‚ú?DELETE_USER - Delete user accounts
- ‚ú?UPDATE_USER - Modify user information
- ‚ú?VIEW_USER - View user details
- ‚ú?CREATE_PROJECT - Create new projects
- ‚ú?DELETE_PROJECT - Delete projects
- ‚ú?UPDATE_PROJECT - Modify project settings
- ‚ú?VIEW_PROJECT - View project details
- ‚ú?MODIFY_CONFIG - Modify system configuration
- ‚ú?VIEW_CONFIG - View system configuration
- ‚ú?EXPORT_REPORT - Export analysis reports

**Use Cases:**
- System administration and maintenance
- User management and role assignment
- Global configuration management
- Full project lifecycle management

---

### 2. MANAGER - Project Oversight & ROI
**Description:** Project managers who oversee projects and track ROI metrics.

**Permissions:**
- ‚ú?VIEW_USER - View user details
- ‚ú?CREATE_PROJECT - Create new projects
- ‚ú?DELETE_PROJECT - Delete projects
- ‚ú?UPDATE_PROJECT - Modify project settings
- ‚ú?VIEW_PROJECT - View project details
- ‚ú?VIEW_CONFIG - View system configuration
- ‚ú?EXPORT_REPORT - Export analysis reports

**Use Cases:**
- Project portfolio management
- ROI tracking and reporting
- Team oversight
- Resource allocation decisions

---

### 3. REVIEWER - Read/Write Analysis
**Description:** Code reviewers who can analyze code and provide feedback.

**Permissions:**
- ‚ú?UPDATE_PROJECT - Modify project analysis settings
- ‚ú?VIEW_PROJECT - View project details
- ‚ú?VIEW_CONFIG - View system configuration
- ‚ú?EXPORT_REPORT - Export analysis reports

**Use Cases:**
- Code quality review
- Analysis report generation
- Providing feedback on code changes
- Quality assurance activities

---

### 4. PROGRAMMER - CRUD Own Branch
**Description:** Developers who can create and manage their own projects/branches.

**Permissions:**
- ‚ú?CREATE_PROJECT - Create new projects
- ‚ú?UPDATE_PROJECT - Modify own project settings
- ‚ú?VIEW_PROJECT - View project details
- ‚ú?VIEW_CONFIG - View system configuration
- ‚ú?EXPORT_REPORT - Export analysis reports

**Use Cases:**
- Creating personal or team projects
- Managing own code branches
- Running code analysis
- Viewing analysis results

**Note:** Programmers can only modify projects they own. Access to other projects requires explicit grants.

---

### 5. VISITOR - Read-Only Grants
**Description:** External stakeholders with read-only access to specific projects.

**Permissions:**
- ‚ú?VIEW_PROJECT - View project details (only for granted projects)

**Use Cases:**
- Viewing project status
- Monitoring code quality metrics
- Stakeholder visibility
- Audit and compliance review

**Note:** Visitors can only view projects they have been explicitly granted access to.

---

## Permission Matrix

| Permission | ADMIN | MANAGER | REVIEWER | PROGRAMMER | VISITOR |
|-----------|-------|---------|----------|------------|---------|
| CREATE_USER | ‚ú?| ‚ù?| ‚ù?| ‚ù?| ‚ù?|
| DELETE_USER | ‚ú?| ‚ù?| ‚ù?| ‚ù?| ‚ù?|
| UPDATE_USER | ‚ú?| ‚ù?| ‚ù?| ‚ù?| ‚ù?|
| VIEW_USER | ‚ú?| ‚ú?| ‚ù?| ‚ù?| ‚ù?|
| CREATE_PROJECT | ‚ú?| ‚ú?| ‚ù?| ‚ú?| ‚ù?|
| DELETE_PROJECT | ‚ú?| ‚ú?| ‚ù?| ‚ù?| ‚ù?|
| UPDATE_PROJECT | ‚ú?| ‚ú?| ‚ú?| ‚ú?| ‚ù?|
| VIEW_PROJECT | ‚ú?| ‚ú?| ‚ú?| ‚ú?| ‚ú?|
| MODIFY_CONFIG | ‚ú?| ‚ù?| ‚ù?| ‚ù?| ‚ù?|
| VIEW_CONFIG | ‚ú?| ‚ú?| ‚ú?| ‚ú?| ‚ù?|
| EXPORT_REPORT | ‚ú?| ‚ú?| ‚ú?| ‚ú?| ‚ù?|

## Default Test Accounts

The system includes 5 default test accounts (one for each role):

| Username | Password | Role | User ID |
|----------|----------|------|---------|
| admin | change-me-strong-password | ADMIN | admin-0000-0000-0000-000000000001 |
| manager | change-me-strong-password | MANAGER | mngr-0000-0000-0000-000000000002 |
| reviewer | change-me-strong-password | REVIEWER | revw-0000-0000-0000-000000000003 |
| programmer | change-me-strong-password | PROGRAMMER | prog-0000-0000-0000-000000000004 |
| visitor | change-me-strong-password | VISITOR | visit-0000-0000-0000-000000000005 |

‚ö†Ô∏è **Security Warning:** Change these default passwords immediately in production environments!

## Project Access Control

### Admin Access
- Admins can access ALL projects regardless of ownership
- Bypass all project-level access controls

### Manager Access
- Can create and manage projects
- Can delete any project
- Full project oversight capabilities

### Reviewer Access
- Can update project analysis settings
- Cannot create or delete projects
- Requires explicit project access grants

### Programmer Access
- Can create new projects (becomes owner)
- Can update own projects
- Can view projects with explicit grants
- Cannot delete projects

### Visitor Access
- Read-only access
- Requires explicit project access grants
- Cannot modify any data

## Implementation Files

### Backend
- `enterprise_rbac_auth/models/enums.py` - Role and Permission enums
- `backend/app/auth/services/rbac_service.py` - RBAC service logic
- `backend/database/init_scripts/03_rbac_seed_data.sql` - Default users

### Frontend
- `frontend/src/types/rbac.ts` - TypeScript type definitions
- `frontend/src/hooks/usePermission.ts` - Permission checking hook
- `shared/types/index.ts` - Shared type definitions

## Migration Notes

If upgrading from the previous 3-role system:
1. Existing ADMIN users remain unchanged
2. Existing PROGRAMMER users remain unchanged
3. Existing VISITOR users remain unchanged
4. New MANAGER and REVIEWER roles are available for assignment
5. Update any hardcoded role checks in custom code
