/**
 * Property-Based Tests for PermissionCheck Component
 * Tests universal properties across all inputs
 */
import { render } from '@testing-library/react';
import * as fc from 'fast-check';
import { PermissionCheck } from '../PermissionCheck';
import { Role, Permission } from '@/types/rbac';
import { useRole } from '@/hooks/useRole';
import { usePermission } from '@/hooks/usePermission';

// Mock dependencies
jest.mock('@/hooks/useRole');
jest.mock('@/hooks/usePermission');

const mockUseRole = useRole as jest.MockedFunction<typeof useRole>;
const mockUsePermission = usePermission as jest.MockedFunction<typeof usePermission>;

describe('PermissionCheck Property Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * Feature: enterprise-rbac-authentication, Property 21: UI elements hidden without permissions
   * For any UI component with a required permission, if the current user lacks that permission,
   * the component should not be rendered in the DOM.
   * Validates: Requirements 5.3
   */
  it('Property 21: UI elements are hidden when user lacks required permission', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom(Role.PROGRAMMER, Role.VISITOR),
        fc.constantFrom(
          Permission.DELETE_PROJECT,
          Permission.DELETE_USER,
          Permission.MODIFY_CONFIG,
          Permission.CREATE_USER
        ),
        fc.string({ minLength: 1, maxLength: 20 }),
        async (userRole, requiredPermission, buttonText) => {
          // Define permissions for each role
          const rolePermissions: Record<Role, Permission[]> = {
            [Role.ADMIN]: Object.values(Permission),
            [Role.PROGRAMMER]: [
              Permission.VIEW_PROJECTS,
              Permission.CREATE_PROJECT,
              Permission.MODIFY_PROJECT,
              Permission.VIEW_REVIEWS,
              Permission.CREATE_REVIEW,
              Permission.MODIFY_REVIEW,
            ],
            [Role.VISITOR]: [
              Permission.VIEW_PROJECTS,
              Permission.VIEW_REVIEWS,
            ],
          };

          const userPermissions = rolePermissions[userRole];
          const hasRequiredPermission = userPermissions.includes(requiredPermission);

          // Setup: User with specific role and permissions
          mockUseRole.mockReturnValue({
            hasRole: (role: Role) => role === userRole,
            currentRole: userRole,
            loading: false,
          });

          mockUsePermission.mockReturnValue({
            hasPermission: (perm: Permission) => userPermissions.includes(perm),
            loading: false,
          });

          // Render component with permission requirement
          const { container } = render(
            <PermissionCheck permission={requiredPermission}>
              <button data-testid="protected-button">{buttonText}</button>
            </PermissionCheck>
          );

          // Verify: Element should only be in DOM if user has permission
          const button = container.querySelector('[data-testid="protected-button"]');
          
          if (hasRequiredPermission) {
            expect(button).toBeInTheDocument();
            expect(button?.textContent).toBe(buttonText);
          } else {
            expect(button).not.toBeInTheDocument();
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Additional property: Admin users can see all UI elements
   */
  it('Property: Admin users can see all permission-protected UI elements', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom(...Object.values(Permission)),
        fc.string({ minLength: 1, maxLength: 20 }),
        async (permission, elementText) => {
          // Setup: Admin user with all permissions
          mockUseRole.mockReturnValue({
            hasRole: (role: Role) => role === Role.ADMIN,
            currentRole: Role.ADMIN,
            loading: false,
          });

          mockUsePermission.mockReturnValue({
            hasPermission: () => true, // Admin has all permissions
            loading: false,
          });

          // Render component with any permission requirement
          const { container } = render(
            <PermissionCheck permission={permission}>
              <div data-testid="admin-element">{elementText}</div>
            </PermissionCheck>
          );

          // Verify: Element should always be visible for admin
          const element = container.querySelector('[data-testid="admin-element"]');
          expect(element).toBeInTheDocument();
          expect(element?.textContent).toBe(elementText);
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Additional property: Visitor users can only see read-only UI elements
   */
  it('Property: Visitor users can only see view-related UI elements', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom(...Object.values(Permission)),
        async (permission) => {
          const visitorPermissions = [Permission.VIEW_PROJECTS, Permission.VIEW_REVIEWS];
          const shouldBeVisible = visitorPermissions.includes(permission);

          // Setup: Visitor user with limited permissions
          mockUseRole.mockReturnValue({
            hasRole: (role: Role) => role === Role.VISITOR,
            currentRole: Role.VISITOR,
            loading: false,
          });

          mockUsePermission.mockReturnValue({
            hasPermission: (perm: Permission) => visitorPermissions.includes(perm),
            loading: false,
          });

          // Render component with permission requirement
          const { container } = render(
            <PermissionCheck permission={permission}>
              <button data-testid="action-button">Action</button>
            </PermissionCheck>
          );

          // Verify: Element visibility matches visitor permissions
          const button = container.querySelector('[data-testid="action-button"]');
          
          if (shouldBeVisible) {
            expect(button).toBeInTheDocument();
          } else {
            expect(button).not.toBeInTheDocument();
          }
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Additional property: Fallback content is shown when permission is denied
   */
  it('Property: Fallback content is rendered when user lacks permission', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom(Role.VISITOR, Role.PROGRAMMER),
        fc.constantFrom(
          Permission.DELETE_USER,
          Permission.MODIFY_CONFIG,
          Permission.CREATE_USER
        ),
        fc.string({ minLength: 1, maxLength: 30 }),
        async (userRole, requiredPermission, fallbackText) => {
          // Define permissions for each role
          const rolePermissions: Record<Role, Permission[]> = {
            [Role.ADMIN]: Object.values(Permission),
            [Role.PROGRAMMER]: [
              Permission.VIEW_PROJECTS,
              Permission.CREATE_PROJECT,
              Permission.MODIFY_PROJECT,
              Permission.VIEW_REVIEWS,
              Permission.CREATE_REVIEW,
              Permission.MODIFY_REVIEW,
            ],
            [Role.VISITOR]: [
              Permission.VIEW_PROJECTS,
              Permission.VIEW_REVIEWS,
            ],
          };

          const userPermissions = rolePermissions[userRole];
          const hasRequiredPermission = userPermissions.includes(requiredPermission);

          // Setup: User without required permission
          mockUseRole.mockReturnValue({
            hasRole: (role: Role) => role === userRole,
            currentRole: userRole,
            loading: false,
          });

          mockUsePermission.mockReturnValue({
            hasPermission: (perm: Permission) => userPermissions.includes(perm),
            loading: false,
          });

          // Render with fallback
          const { container } = render(
            <PermissionCheck
              permission={requiredPermission}
              fallback={<span data-testid="fallback">{fallbackText}</span>}
            >
              <button data-testid="protected-button">Protected Action</button>
            </PermissionCheck>
          );

          const button = container.querySelector('[data-testid="protected-button"]');
          const fallback = container.querySelector('[data-testid="fallback"]');

          // Verify: Either button or fallback is shown, never both
          if (hasRequiredPermission) {
            expect(button).toBeInTheDocument();
            expect(fallback).not.toBeInTheDocument();
          } else {
            expect(button).not.toBeInTheDocument();
            expect(fallback).toBeInTheDocument();
            expect(fallback?.textContent).toBe(fallbackText);
          }
        }
      ),
      { numRuns: 50 }
    );
  });
});
