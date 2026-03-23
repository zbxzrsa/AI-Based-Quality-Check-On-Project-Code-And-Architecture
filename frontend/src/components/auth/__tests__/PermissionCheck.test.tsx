/**
 * Unit Tests for PermissionCheck Component
 */
import { render, screen } from '@testing-library/react';
import { PermissionCheck } from '../PermissionCheck';
import { Role, Permission } from '@/types/rbac';
import { useRole } from '@/hooks/useRole';
import { usePermission } from '@/hooks/usePermission';

// Mock dependencies
jest.mock('@/hooks/useRole');
jest.mock('@/hooks/usePermission');

const mockUseRole = useRole as jest.MockedFunction<typeof useRole>;
const mockUsePermission = usePermission as jest.MockedFunction<typeof usePermission>;

describe('PermissionCheck', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders children when permission requirement is met', () => {
    mockUseRole.mockReturnValue({
      hasRole: () => true,
      currentRole: Role.ADMIN,
      loading: false,
    });

    mockUsePermission.mockReturnValue({
      hasPermission: (perm: Permission) => perm === Permission.MODIFY_CONFIG,
      loading: false,
    });

    render(
      <PermissionCheck permission={Permission.MODIFY_CONFIG}>
        <button>Delete</button>
      </PermissionCheck>
    );

    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('renders fallback when permission requirement is not met', () => {
    mockUseRole.mockReturnValue({
      hasRole: () => false,
      currentRole: Role.VISITOR,
      loading: false,
    });

    mockUsePermission.mockReturnValue({
      hasPermission: (perm: Permission) => perm !== Permission.DELETE_PROJECT,
      loading: false,
    });

    render(
      <PermissionCheck
        permission={Permission.DELETE_PROJECT}
        fallback={<span>Not authorized</span>}
      >
        <button>Delete</button>
      </PermissionCheck>
    );

    expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    expect(screen.getByText('Not authorized')).toBeInTheDocument();
  });

  it('renders children when role requirement is met', () => {
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
      <PermissionCheck role={Role.ADMIN}>
        <div>Admin Panel</div>
      </PermissionCheck>
    );

    expect(screen.getByText('Admin Panel')).toBeInTheDocument();
  });

  it('renders fallback when role requirement is not met', () => {
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
      <PermissionCheck role={Role.ADMIN} fallback={null}>
        <div>Admin Panel</div>
      </PermissionCheck>
    );

    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument();
  });

  it('renders fallback while loading', () => {
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
      <PermissionCheck
        permission={Permission.MODIFY_CONFIG}
        fallback={<span>Loading...</span>}
      >
        <button>Settings</button>
      </PermissionCheck>
    );

    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders children when both role and permission requirements are met', () => {
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
      <PermissionCheck role={Role.ADMIN} permission={Permission.DELETE_USER}>
        <button>Delete User</button>
      </PermissionCheck>
    );

    expect(screen.getByText('Delete User')).toBeInTheDocument();
  });

  it('hides UI elements without required permissions (Property 21)', () => {
    mockUseRole.mockReturnValue({
      hasRole: (role: Role) => role === Role.VISITOR,
      currentRole: Role.VISITOR,
      loading: false,
    });

    mockUsePermission.mockReturnValue({
      hasPermission: (perm: Permission) => 
        perm === Permission.VIEW_PROJECTS || perm === Permission.VIEW_REVIEWS,
      loading: false,
    });

    const { container } = render(
      <div>
        <PermissionCheck permission={Permission.DELETE_PROJECT}>
          <button>Delete</button>
        </PermissionCheck>
        <PermissionCheck permission={Permission.MODIFY_CONFIG}>
          <button>Configure</button>
        </PermissionCheck>
        <PermissionCheck permission={Permission.VIEW_PROJECTS}>
          <button>View</button>
        </PermissionCheck>
      </div>
    );

    // Delete and Configure buttons should be hidden
    expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    expect(screen.queryByText('Configure')).not.toBeInTheDocument();
    
    // View button should be visible
    expect(screen.getByText('View')).toBeInTheDocument();
  });
});
