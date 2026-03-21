/**
 * Unit Tests for RBACGuard Component
 */
import { render, screen, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { RBACGuard } from '../RBACGuard';
import { Role, Permission } from '@/types/rbac';
import { useAuth } from '@/contexts/AuthContext';
import { useRole } from '@/hooks/useRole';
import { usePermission } from '@/hooks/usePermission';

// Mock dependencies
jest.mock('next/navigation');
jest.mock('@/contexts/AuthContext');
jest.mock('@/hooks/useRole');
jest.mock('@/hooks/usePermission');
jest.mock('lucide-react', () => require('../../../../__mocks__/lucide-react.tsx'));

const mockPush = jest.fn();
const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockUseRole = useRole as jest.MockedFunction<typeof useRole>;
const mockUsePermission = usePermission as jest.MockedFunction<typeof usePermission>;

type AuthHookValue = ReturnType<typeof useAuth>;
type RoleHookValue = ReturnType<typeof useRole>;
type PermissionHookValue = ReturnType<typeof usePermission>;

const mockAuthValue = (overrides: Partial<AuthHookValue> = {}): AuthHookValue => ({
  user: null,
  loading: false,
  role: null,
  permissions: [],
  login: jest.fn(),
  register: jest.fn(),
  logout: jest.fn(),
  refreshToken: jest.fn(),
  isAuthenticated: false,
  ...overrides,
});

const mockRoleValue = (overrides: Partial<RoleHookValue> = {}): RoleHookValue => ({
  hasRole: () => false,
  currentRole: null,
  loading: false,
  ...overrides,
});

const mockPermissionValue = (
  overrides: Partial<PermissionHookValue> = {}
): PermissionHookValue => ({
  hasPermission: () => false,
  loading: false,
  ...overrides,
});

const buildUser = (role: Role): NonNullable<AuthHookValue['user']> => ({
  id: '1',
  email: 'test@example.com',
  full_name: 'Test User',
  role,
  is_active: true,
});

describe('RBACGuard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseRouter.mockReturnValue({
      push: mockPush,
      replace: jest.fn(),
      refresh: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      prefetch: jest.fn(),
    });
  });

  it('shows loading state while checking authentication', () => {
    mockUseAuth.mockReturnValue(mockAuthValue({ loading: true }));
    mockUseRole.mockReturnValue(mockRoleValue({ loading: true }));
    mockUsePermission.mockReturnValue(mockPermissionValue({ loading: true }));

    render(
      <RBACGuard>
        <div>Protected Content</div>
      </RBACGuard>
    );

    expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
  });

  it('redirects to login when session is expired', async () => {
    mockUseAuth.mockReturnValue(mockAuthValue());
    mockUseRole.mockReturnValue(mockRoleValue());
    mockUsePermission.mockReturnValue(mockPermissionValue());

    render(
      <RBACGuard>
        <div>Protected Content</div>
      </RBACGuard>
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });

  it('redirects to unauthorized when role requirement is not met', async () => {
    mockUseAuth.mockReturnValue(mockAuthValue({
      user: buildUser(Role.USER),
      role: Role.USER,
      isAuthenticated: true,
    }));
    mockUseRole.mockReturnValue(mockRoleValue({
      hasRole: (role: Role) => role === Role.USER,
      currentRole: Role.USER,
    }));
    mockUsePermission.mockReturnValue(mockPermissionValue());

    render(
      <RBACGuard requiredRole={Role.ADMIN}>
        <div>Admin Content</div>
      </RBACGuard>
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/unauthorized');
    });
  });

  it('redirects to unauthorized when permission requirement is not met', async () => {
    mockUseAuth.mockReturnValue(mockAuthValue({
      user: buildUser(Role.USER),
      role: Role.USER,
      isAuthenticated: true,
    }));
    mockUseRole.mockReturnValue(mockRoleValue({
      hasRole: (role: Role) => role === Role.USER,
      currentRole: Role.USER,
    }));
    mockUsePermission.mockReturnValue(mockPermissionValue({
      hasPermission: (permission: Permission) => permission !== Permission.MODIFY_CONFIG,
    }));

    render(
      <RBACGuard requiredPermission={Permission.MODIFY_CONFIG}>
        <div>Settings Content</div>
      </RBACGuard>
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/unauthorized');
    });
  });

  it('renders children when all requirements are met', async () => {
    mockUseAuth.mockReturnValue(mockAuthValue({
      user: buildUser(Role.ADMIN),
      role: Role.ADMIN,
      permissions: [Permission.MODIFY_CONFIG],
      isAuthenticated: true,
    }));
    mockUseRole.mockReturnValue(mockRoleValue({
      hasRole: (role: Role) => role === Role.ADMIN,
      currentRole: Role.ADMIN,
    }));
    mockUsePermission.mockReturnValue(mockPermissionValue({
      hasPermission: () => true,
    }));

    render(
      <RBACGuard requiredRole={Role.ADMIN} requiredPermission={Permission.MODIFY_CONFIG}>
        <div>Protected Content</div>
      </RBACGuard>
    );

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  it('renders fallback when unauthorized', async () => {
    mockUseAuth.mockReturnValue(mockAuthValue({
      user: buildUser(Role.USER),
      role: Role.USER,
      isAuthenticated: true,
    }));
    mockUseRole.mockReturnValue(mockRoleValue({
      hasRole: (role: Role) => role === Role.USER,
      currentRole: Role.USER,
    }));
    mockUsePermission.mockReturnValue(mockPermissionValue());

    render(
      <RBACGuard
        requiredRole={Role.ADMIN}
        fallback={<div>Access Denied</div>}
      >
        <div>Admin Content</div>
      </RBACGuard>
    );

    await waitFor(() => {
      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
    });
  });
});
