/**
 * Frontend Hooks - Central Export
 * 
 * This file provides centralized exports for all custom hooks.
 * Import from here instead of individual files.
 */

// Authentication
export { useLogin, useLogout, useRegister, useCurrentUser, useAuth } from './useAuth';

// Projects
export { useProjects, useProject, useCreateProject, useUpdateProject, useDeleteProject } from './useProjects';

// Permissions
export { usePermission, useHasPermission, PermissionCheck } from './usePermission';

// Roles
export { useRole, useIsAdmin, useIsManager } from './useRole';

// API calls
export { useApiCall } from './useApiCall';

// Async actions
export { useAsyncAction } from './useAsyncAction';

// Backend status
export { useBackendStatus } from './useBackendStatus';

// Debounce
export { useDebounce } from './useDebounce';

// Toast notifications
export { useToast, toast } from './use-toast';
