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
jest.mock('lucide-react', () => ({
  Loader2: () => <div role="status">Loading...</div>,
}));

const mockPush = jest.fn();
const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockUseRole = useRole as jest.MockedFunction<typeof useRole>;
const mockUsePermission = usePermission as jest.MockedFunction<typeof usePermission>;

describe('RBACGuard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseRouter.mockReturnValue({ push: mockPush } as any);
  });

  it('shows loading state while checking authentication', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      session: null,
      loading: true,
      role: null,
      permissions: [],
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    });

    mockUseRole.mockReturnValue({
      hasRole: () => false,
      currentRole: null,
      loading: true,
    });

    mockUsePermission.mockReturnValue({
      hasPermission: () => false,
      loading: true,
    });

    render(
      <RBACGuard>
        <div>Protected Content</div>
      </RBACGuard>
    );

    expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
  });

  it('redirects to login when session is expired', async () => {
    mockUseAuth.mockReturnValue({
      user: null,
      session: null,
      loading: false,
      role: null,
      permissions: [],
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    });

    mockUseRole.mockReturnValue({
      hasRole: () => false,
      currentRole: null,
      loading: false,
    });

    mockUsePermission.mockReturnValue({
      hasPermission: () => false,
      loading: false,
    });

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
    mockUseAuth.mockReturnValue({
      user: { id: '1', role: Role.PROGRAMMER } as any,
      session: { user: { id: '1', role: Role.PROGRAMMER } } as any,
      loading: false,
      role: Role.PROGRAMMER,
      permissions: [],
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    });

    mockUseRole.mockReturnValue({
      hasRole: (role: Role) => role === Role.PROGRAMMER,
      currentRole: Role.PROGRAMMER,
      loading: false,
    });

    mockUsePermission.mockReturnValue({
      hasPermission: () => false,
      loading: false,
    });

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
    mockUseAuth.mockReturnValue({
      user: { id: '1', role: Role.VISITOR } as any,
      session: { user: { id: '1', role: Role.VISITOR } } as any,
      loading: false,
      role: Role.VISITOR,
      permissions: [],
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    });

    mockUseRole.mockReturnValue({
      hasRole: (role: Role) => role === Role.VISITOR,
      currentRole: Role.VISITOR,
      loading: false,
    });

    mockUsePermission.mockReturnValue({
      hasPermission: (perm: Permission) => perm !== Permission.MODIFY_CONFIG,
      loading: false,
    });

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
    mockUseAuth.mockReturnValue({
      user: { id: '1', role: Role.ADMIN } as any,
      session: { user: { id: '1', role: Role.ADMIN } } as any,
      loading: false,
      role: Role.ADMIN,
      permissions: [Permission.MODIFY_CONFIG],
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    });

    mockUseRole.mockReturnValue({
      hasRole: (role: Role) => role === Role.ADMIN,
      currentRole: Role.ADMIN,
      loading: false,
    });

    mockUsePermission.mockReturnValue({
      hasPermission: () => true,
      loading: false,
    });

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
    mockUseAuth.mockReturnValue({
      user: { id: '1', role: Role.VISITOR } as any,
      session: { user: { id: '1', role: Role.VISITOR } } as any,
      loading: false,
      role: Role.VISITOR,
      permissions: [],
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    });

    mockUseRole.mockReturnValue({
      hasRole: (role: Role) => role === Role.VISITOR,
      currentRole: Role.VISITOR,
      loading: false,
    });

    mockUsePermission.mockReturnValue({
      hasPermission: () => false,
      loading: false,
    });

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
