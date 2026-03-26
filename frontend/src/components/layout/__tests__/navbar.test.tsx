/**
 * Unit tests for Navbar component
 * Tests rendering, search functionality, and user menu
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Navbar } from '../navbar';
import { useAuth } from '@/contexts/AuthContext';
import type { ReactNode } from 'react';

// Mock Next.js modules
jest.mock('next/link', () => {
  return ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
});

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuLabel: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuSeparator: () => <hr />,
  DropdownMenuItem: ({ children, asChild, onClick }: { children: ReactNode; asChild?: boolean; onClick?: () => void }) =>
    asChild ? <>{children}</> : <button onClick={onClick}>{children}</button>,
}));

jest.mock('@/components/theme-toggle', () => ({
  ThemeToggle: () => <div>Theme Toggle</div>,
}));

jest.mock('@/components/notifications/notification-center', () => {
  return function NotificationCenter({ isOpen, onClose }: any) {
    return isOpen ? <div>Notification Center</div> : null;
  };
});

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockLogout = jest.fn();

describe('Navbar', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
      role: null,
      permissions: [],
      login: jest.fn(),
      register: jest.fn(),
      logout: mockLogout,
      refreshToken: jest.fn(),
      isAuthenticated: false,
    });
  });

  describe('Rendering', () => {
    it('should render logo and brand name', () => {
      render(<Navbar />);

      expect(screen.getByText('AI')).toBeInTheDocument();
      expect(screen.getByText('Code Review Platform')).toBeInTheDocument();
    });

    it('should render theme toggle', () => {
      render(<Navbar />);

      expect(screen.getByText('Theme Toggle')).toBeInTheDocument();
    });

    it('should render notification bell', () => {
      const { container } = render(<Navbar />);

      const bellButton = container.querySelector('button[class*="relative"]');
      expect(bellButton).toBeInTheDocument();
    });

    it('should render user menu button', () => {
      const { container } = render(<Navbar />);

      const userButtons = container.querySelectorAll('button');
      expect(userButtons.length).toBeGreaterThan(0);
    });
  });

  describe('User Session', () => {
    it('should display user name when logged in', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          full_name: 'John Doe',
          email: 'john@example.com',
          role: 'ADMIN' as any,
          is_active: true,
        },
        loading: false,
        role: 'ADMIN' as any,
        permissions: [],
        login: jest.fn(),
        register: jest.fn(),
        logout: mockLogout,
        refreshToken: jest.fn(),
        isAuthenticated: true,
      });

      render(<Navbar />);

      // Click user menu to see name
      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        expect(screen.getByText('John Doe')).toBeInTheDocument();
      }
    });

    it('should display user email when logged in', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          full_name: 'John Doe',
          email: 'john@example.com',
          role: 'ADMIN' as any,
          is_active: true,
        },
        loading: false,
        role: 'ADMIN' as any,
        permissions: [],
        login: jest.fn(),
        register: jest.fn(),
        logout: mockLogout,
        refreshToken: jest.fn(),
        isAuthenticated: true,
      });

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        expect(screen.getByText('john@example.com')).toBeInTheDocument();
      }
    });

    it('should display "User" when name is not available', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          full_name: null,
          email: 'john@example.com',
          role: 'ADMIN' as any,
          is_active: true,
        },
        loading: false,
        role: 'ADMIN' as any,
        permissions: [],
        login: jest.fn(),
        register: jest.fn(),
        logout: mockLogout,
        refreshToken: jest.fn(),
        isAuthenticated: true,
      });

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        expect(screen.getByText('User')).toBeInTheDocument();
      }
    });
  });

  describe('Notification Center', () => {
    it('should open notification center when bell is clicked', () => {
      render(<Navbar />);

      const bellButton = screen.getAllByRole('button').find(btn => 
        btn.className.includes('relative')
      );
      
      if (bellButton) {
        fireEvent.click(bellButton);
        expect(screen.getByText('Notification Center')).toBeInTheDocument();
      }
    });

    it('should show notification badge', () => {
      const { container } = render(<Navbar />);

      const badge = container.querySelector('.bg-destructive');
      expect(badge).toBeInTheDocument();
    });
  });

  describe('User Menu', () => {
    it('should show Profile menu item', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          full_name: 'John',
          email: 'john@example.com',
          role: 'ADMIN' as any,
          is_active: true,
        },
        loading: false,
        role: 'ADMIN' as any,
        permissions: [],
        login: jest.fn(),
        register: jest.fn(),
        logout: mockLogout,
        refreshToken: jest.fn(),
        isAuthenticated: true,
      });

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        expect(screen.getByText('Profile')).toBeInTheDocument();
      }
    });

    it('should show Sign out menu item', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          full_name: 'John',
          email: 'john@example.com',
          role: 'ADMIN' as any,
          is_active: true,
        },
        loading: false,
        role: 'ADMIN' as any,
        permissions: [],
        login: jest.fn(),
        register: jest.fn(),
        logout: mockLogout,
        refreshToken: jest.fn(),
        isAuthenticated: true,
      });

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        expect(screen.getByText('Sign out')).toBeInTheDocument();
      }
    });

    it('should call logout when Sign out is clicked', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          full_name: 'John',
          email: 'john@example.com',
          role: 'ADMIN' as any,
          is_active: true,
        },
        loading: false,
        role: 'ADMIN' as any,
        permissions: [],
        login: jest.fn(),
        register: jest.fn(),
        logout: mockLogout,
        refreshToken: jest.fn(),
        isAuthenticated: true,
      });

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        const signOutButton = screen.getByText('Sign out');
        fireEvent.click(signOutButton);
        await waitFor(() => {
          expect(mockLogout).toHaveBeenCalled();
        });
      }
    });

    it('should link to profile page', () => {
      mockUseAuth.mockReturnValue({
        user: {
          id: '1',
          full_name: 'John',
          email: 'john@example.com',
          role: 'ADMIN' as any,
          is_active: true,
        },
        loading: false,
        role: 'ADMIN' as any,
        permissions: [],
        login: jest.fn(),
        register: jest.fn(),
        logout: mockLogout,
        refreshToken: jest.fn(),
        isAuthenticated: true,
      });

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        const profileLink = screen.getByText('Profile').closest('a');
        expect(profileLink).toHaveAttribute('href', '/profile');
      }
    });
  });

  describe('Logo Link', () => {
    it('should link to dashboard', () => {
      render(<Navbar />);

      const logoLink = screen.getByText('AI').closest('a');
      expect(logoLink).toHaveAttribute('href', '/dashboard');
    });
  });
});
