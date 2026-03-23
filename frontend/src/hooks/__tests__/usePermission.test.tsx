/**
 * Unit tests for usePermission hook
 * Tests permission checking logic based on user roles
 */

import { renderHook } from '@testing-library/react';
import { usePermission } from '../usePermission';
import { useAuth } from '@/contexts/AuthContext';
import { Permission, Role } from '@/types/rbac';

// Mock the useAuth hook
jest.mock('@/contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe('usePermission', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Admin role', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'admin@test.com', role: Role.ADMIN, name: 'Admin' },
        loading: false,
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        refreshToken: jest.fn(),
      });
    });

    it('should have all permissions', () => {
      const { result } = renderHook(() => usePermission());

      expect(result.current.hasPermission(Permission.VIEW_PROJECTS)).toBe(true);
      expect(result.current.hasPermission(Permission.CREATE_PROJECT)).toBe(true);
      expect(result.current.hasPermission(Permission.MODIFY_PROJECT)).toBe(true);
      expect(result.current.hasPermission(Permission.DELETE_PROJECT)).toBe(true);
      expect(result.current.hasPermission(Permission.VIEW_USERS)).toBe(true);
      expect(result.current.hasPermission(Permission.CREATE_USER)).toBe(true);
      expect(result.current.hasPermission(Permission.MODIFY_USER)).toBe(true);
      expect(result.current.hasPermission(Permission.DELETE_USER)).toBe(true);
      expect(result.current.hasPermission(Permission.VIEW_REVIEWS)).toBe(true);
      expect(result.current.hasPermission(Permission.CREATE_REVIEW)).toBe(true);
      expect(result.current.hasPermission(Permission.MODIFY_REVIEW)).toBe(true);
      expect(result.current.hasPermission(Permission.MODIFY_CONFIG)).toBe(true);
    });

    it('should not be loading', () => {
      const { result } = renderHook(() => usePermission());
      expect(result.current.loading).toBe(false);
    });
  });

  describe('Programmer role', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: '2', email: 'dev@test.com', role: Role.PROGRAMMER, name: 'Developer' },
        loading: false,
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        refreshToken: jest.fn(),
      });
    });

    it('should have project and review permissions', () => {
      const { result } = renderHook(() => usePermission());

      expect(result.current.hasPermission(Permission.VIEW_PROJECTS)).toBe(true);
      expect(result.current.hasPermission(Permission.CREATE_PROJECT)).toBe(true);
      expect(result.current.hasPermission(Permission.MODIFY_PROJECT)).toBe(true);
      expect(result.current.hasPermission(Permission.VIEW_REVIEWS)).toBe(true);
      expect(result.current.hasPermission(Permission.CREATE_REVIEW)).toBe(true);
      expect(result.current.hasPermission(Permission.MODIFY_REVIEW)).toBe(true);
    });

    it('should not have user management permissions', () => {
      const { result } = renderHook(() => usePermission());

      expect(result.current.hasPermission(Permission.VIEW_USERS)).toBe(false);
      expect(result.current.hasPermission(Permission.CREATE_USER)).toBe(false);
      expect(result.current.hasPermission(Permission.MODIFY_USER)).toBe(false);
      expect(result.current.hasPermission(Permission.DELETE_USER)).toBe(false);
    });

    it('should not have delete project permission', () => {
      const { result } = renderHook(() => usePermission());
      expect(result.current.hasPermission(Permission.DELETE_PROJECT)).toBe(false);
    });

    it('should not have config modification permission', () => {
      const { result } = renderHook(() => usePermission());
      expect(result.current.hasPermission(Permission.MODIFY_CONFIG)).toBe(false);
    });
  });

  describe('Visitor role', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: '3', email: 'visitor@test.com', role: Role.VISITOR, name: 'Visitor' },
        loading: false,
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        refreshToken: jest.fn(),
      });
    });

    it('should only have view permissions', () => {
      const { result } = renderHook(() => usePermission());

      expect(result.current.hasPermission(Permission.VIEW_PROJECTS)).toBe(true);
      expect(result.current.hasPermission(Permission.VIEW_REVIEWS)).toBe(true);
    });

    it('should not have create/modify/delete permissions', () => {
      const { result } = renderHook(() => usePermission());

      expect(result.current.hasPermission(Permission.CREATE_PROJECT)).toBe(false);
      expect(result.current.hasPermission(Permission.MODIFY_PROJECT)).toBe(false);
      expect(result.current.hasPermission(Permission.DELETE_PROJECT)).toBe(false);
      expect(result.current.hasPermission(Permission.CREATE_REVIEW)).toBe(false);
      expect(result.current.hasPermission(Permission.MODIFY_REVIEW)).toBe(false);
      expect(result.current.hasPermission(Permission.VIEW_USERS)).toBe(false);
      expect(result.current.hasPermission(Permission.MODIFY_CONFIG)).toBe(false);
    });
  });

  describe('No user (unauthenticated)', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: null,
        loading: false,
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        refreshToken: jest.fn(),
      });
    });

    it('should have no permissions', () => {
      const { result } = renderHook(() => usePermission());

      expect(result.current.hasPermission(Permission.VIEW_PROJECTS)).toBe(false);
      expect(result.current.hasPermission(Permission.VIEW_REVIEWS)).toBe(false);
      expect(result.current.hasPermission(Permission.CREATE_PROJECT)).toBe(false);
    });
  });

  describe('Loading state', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: null,
        loading: true,
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        refreshToken: jest.fn(),
      });
    });

    it('should reflect loading state', () => {
      const { result } = renderHook(() => usePermission());
      expect(result.current.loading).toBe(true);
    });
  });

  describe('Invalid role', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: '4', email: 'test@test.com', role: 'INVALID_ROLE' as Role, name: 'Test' },
        loading: false,
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        refreshToken: jest.fn(),
      });
    });

    it('should have no permissions for invalid role', () => {
      const { result } = renderHook(() => usePermission());

      expect(result.current.hasPermission(Permission.VIEW_PROJECTS)).toBe(false);
      expect(result.current.hasPermission(Permission.CREATE_PROJECT)).toBe(false);
    });
  });
});
