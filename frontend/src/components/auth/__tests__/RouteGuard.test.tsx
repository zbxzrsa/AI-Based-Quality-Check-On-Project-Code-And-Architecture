/**
 * RouteGuard Component Tests
 * Tests authentication and authorization protection
 */
import { render, screen, waitFor } from '@testing-library/react';
import { useRouter, usePathname } from 'next/navigation';
import { RouteGuard } from '../RouteGuard';
import { useAuth } from '@/contexts/AuthContext';
import { Role, Permission } from '@/types/rbac';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
}));

// Mock AuthContext
jest.mock('@/contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

describe('RouteGuard', () => {
  const mockPush = jest.fn();
  const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;
  const mockUsePathname = usePathname as jest.MockedFunction<typeof usePathname>;
  const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseRouter.mockReturnValue({ push: mockPush } as any);
    mockUsePathname.mockReturnValue('/protected');
  });

  describe('Loading State', () => {
    it('should show loading spinner while authentication is loading', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        loading: true,
        isAuthenticated: false,
        permissions: [],
        role: null,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      );

      // Check for loading spinner by class name
      const loadingSpinner = document.querySelector('.animate-spin');
      expect(loadingSpinner).toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });

  describe('Authentication - Requirement 3.4', () => {
    it('should redirect unauthenticated users to login page', async () => {
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
        isAuthenticated: false,
        permissions: [],
        role: null,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login?returnUrl=%2Fprotected');
      });

      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    it('should redirect to custom path when redirectTo is specified', async () => {
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
        isAuthenticated: false,
        permissions: [],
        role: null,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard redirectTo="/custom-login">
          <div>Protected Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/custom-login?returnUrl=%2Fprotected');
      });
    });

    it('should render content for authenticated users', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: Role.PROGRAMMER,
          is_active: true,
        },
        loading: false,
        isAuthenticated: true,
        permissions: [Permission.VIEW_PROJECTS],
        role: Role.PROGRAMMER,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      );

      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    it('should use dashboard as default returnUrl when on login page', async () => {
      mockUsePathname.mockReturnValue('/login');
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
        isAuthenticated: false,
        permissions: [],
        role: null,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login?returnUrl=%2Fdashboard');
      });
    });
  });

  describe('Role-Based Authorization - Requirement 3.5', () => {
    it('should redirect users without required role to unauthorized page', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: Role.VISITOR,
          is_active: true,
        },
        loading: false,
        isAuthenticated: true,
        permissions: [Permission.VIEW_PROJECTS],
        role: Role.VISITOR,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard requiredRole={Role.ADMIN}>
          <div>Admin Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized');
      });

      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
    });

    it('should render content for users with required role', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          email: 'admin@example.com',
          name: 'Admin User',
          role: Role.ADMIN,
          is_active: true,
        },
        loading: false,
        isAuthenticated: true,
        permissions: [
          Permission.VIEW_PROJECTS,
          Permission.CREATE_PROJECT,
          Permission.MODIFY_PROJECT,
          Permission.DELETE_PROJECT,
        ],
        role: Role.ADMIN,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard requiredRole={Role.ADMIN}>
          <div>Admin Content</div>
        </RouteGuard>
      );

      expect(screen.getByText('Admin Content')).toBeInTheDocument();
    });
  });

  describe('Permission-Based Authorization - Requirement 3.5', () => {
    it('should redirect users without required permission to unauthorized page', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          email: 'visitor@example.com',
          name: 'Visitor User',
          role: Role.VISITOR,
          is_active: true,
        },
        loading: false,
        isAuthenticated: true,
        permissions: [Permission.VIEW_PROJECTS],
        role: Role.VISITOR,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard requiredPermission={Permission.MODIFY_PROJECT}>
          <div>Project Edit Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized');
      });

      expect(screen.queryByText('Project Edit Content')).not.toBeInTheDocument();
    });

    it('should render content for users with required permission', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          email: 'programmer@example.com',
          name: 'Programmer User',
          role: Role.PROGRAMMER,
          is_active: true,
        },
        loading: false,
        isAuthenticated: true,
        permissions: [
          Permission.VIEW_PROJECTS,
          Permission.CREATE_PROJECT,
          Permission.MODIFY_PROJECT,
        ],
        role: Role.PROGRAMMER,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard requiredPermission={Permission.MODIFY_PROJECT}>
          <div>Project Edit Content</div>
        </RouteGuard>
      );

      expect(screen.getByText('Project Edit Content')).toBeInTheDocument();
    });
  });

  describe('Combined Role and Permission Checks', () => {
    it('should check both role and permission when both are specified', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          email: 'programmer@example.com',
          name: 'Programmer User',
          role: Role.PROGRAMMER,
          is_active: true,
        },
        loading: false,
        isAuthenticated: true,
        permissions: [Permission.VIEW_PROJECTS, Permission.MODIFY_PROJECT],
        role: Role.PROGRAMMER,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard requiredRole={Role.ADMIN} requiredPermission={Permission.DELETE_PROJECT}>
          <div>Admin Delete Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized');
      });
    });

    it('should render when both role and permission requirements are met', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          email: 'admin@example.com',
          name: 'Admin User',
          role: Role.ADMIN,
          is_active: true,
        },
        loading: false,
        isAuthenticated: true,
        permissions: [
          Permission.VIEW_PROJECTS,
          Permission.CREATE_PROJECT,
          Permission.MODIFY_PROJECT,
          Permission.DELETE_PROJECT,
        ],
        role: Role.ADMIN,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard requiredRole={Role.ADMIN} requiredPermission={Permission.DELETE_PROJECT}>
          <div>Admin Delete Content</div>
        </RouteGuard>
      );

      expect(screen.getByText('Admin Delete Content')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should not redirect when loading completes and user is authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: Role.PROGRAMMER,
          is_active: true,
        },
        loading: false,
        isAuthenticated: true,
        permissions: [Permission.VIEW_PROJECTS],
        role: Role.PROGRAMMER,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      );

      expect(mockPush).not.toHaveBeenCalled();
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    it('should handle null user gracefully', async () => {
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
        isAuthenticated: false,
        permissions: [],
        role: null,
        login: jest.fn(),
        register: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
      });

      render(
        <RouteGuard requiredRole={Role.ADMIN}>
          <div>Admin Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login?returnUrl=%2Fprotected');
      });
    });
  });
});
