import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import { Permission, Role } from '@/types/rbac';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock fetch
global.fetch = jest.fn();

const createMockResponse = (data: unknown, options: { ok?: boolean; status?: number; contentType?: string } = {}) => ({
  ok: options.ok ?? true,
  status: options.status ?? 200,
  headers: {
    get: (header: string) => (header.toLowerCase() === 'content-type' ? options.contentType ?? 'application/json' : null),
  },
  json: async () => data,
  text: async () => (typeof data === 'string' ? data : JSON.stringify(data)),
});

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  it('should initialize with loading state', () => {
    (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => undefined));

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.user).toBe(null);
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should fetch current user on mount', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      full_name: 'Test User',
      role: Role.USER,
      is_active: true,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce(createMockResponse(mockUser));

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await waitFor(() => {
      expect(result.current.role).toBe(Role.USER);
    });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should handle login successfully', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      full_name: 'Test User',
      role: Role.USER,
      is_active: true,
    };

    // Mock initial fetch (no user)
    (global.fetch as jest.Mock).mockResolvedValueOnce(createMockResponse({ detail: 'Unauthorized' }, { ok: false, status: 401 }));

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Mock login and subsequent user fetch
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(createMockResponse({ success: true }))
      .mockResolvedValueOnce(createMockResponse(mockUser));

    await act(async () => {
      await result.current.login('test@example.com', 'password');
    });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should handle login failure', async () => {
    // Mock initial fetch (no user)
    (global.fetch as jest.Mock).mockResolvedValueOnce(createMockResponse({ detail: 'Unauthorized' }, { ok: false, status: 401 }));

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Mock failed login
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      createMockResponse({ detail: 'Invalid credentials' }, { ok: false, status: 401 })
    );

    await expect(
      act(async () => {
        await result.current.login('test@example.com', 'wrong-password');
      })
    ).rejects.toThrow('Invalid credentials');

    expect(result.current.user).toBe(null);
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should handle logout', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      full_name: 'Test User',
      role: Role.USER,
      is_active: true,
    };

    // Mock initial fetch with user
    (global.fetch as jest.Mock).mockResolvedValueOnce(createMockResponse(mockUser));

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
    });

    // Mock logout
    (global.fetch as jest.Mock).mockResolvedValueOnce(createMockResponse({ success: true }));

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBe(null);
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should refresh token successfully', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      full_name: 'Test User',
      role: Role.USER,
      is_active: true,
    };

    // Mock initial fetch with user
    (global.fetch as jest.Mock).mockResolvedValueOnce(createMockResponse(mockUser));

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
    });

    // Mock token refresh and user fetch
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(createMockResponse({ success: true }))
      .mockResolvedValueOnce(createMockResponse(mockUser));

    await act(async () => {
      await result.current.refreshToken();
    });

    expect(result.current.user).toEqual(mockUser);
  });

  it('should handle token refresh failure', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      full_name: 'Test User',
      role: Role.USER,
      is_active: true,
    };

    // Mock initial fetch with user
    (global.fetch as jest.Mock).mockResolvedValueOnce(createMockResponse(mockUser));

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
    });

    // Mock failed token refresh
    (global.fetch as jest.Mock).mockResolvedValueOnce(createMockResponse({ detail: 'Unauthorized' }, { ok: false, status: 401 }));

    await act(async () => {
      await result.current.refreshToken();
    });

    expect(result.current.user).toBe(null);
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should set correct permissions based on role', async () => {
    const mockAdminUser = {
      id: '1',
      email: 'admin@example.com',
      full_name: 'Admin User',
      role: Role.ADMIN,
      is_active: true,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce(createMockResponse(mockAdminUser));

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockAdminUser);
    });

    await waitFor(() => {
      expect(result.current.role).toBe(Role.ADMIN);
    });

    expect(result.current.permissions.length).toBeGreaterThan(0);
    expect(result.current.permissions).toContain(Permission.VIEW_PROJECTS);
    expect(result.current.permissions).toContain(Permission.CREATE_USER);
  });
});
