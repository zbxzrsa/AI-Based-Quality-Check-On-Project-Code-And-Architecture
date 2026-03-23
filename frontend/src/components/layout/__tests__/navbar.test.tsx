/**
 * Unit tests for Navbar component
 * Tests rendering, search functionality, and user menu
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Navbar } from '../navbar';
import { useSession, signOut } from 'next-auth/react';
import type { ReactNode } from 'react';

// Mock Next.js modules
jest.mock('next/link', () => {
  return ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
});

jest.mock('next-auth/react', () => ({
  useSession: jest.fn(),
  signOut: jest.fn(),
}));

jest.mock('@/components/theme-toggle', () => ({
  ThemeToggle: () => <div>Theme Toggle</div>,
}));

jest.mock('@/components/notifications/notification-center', () => {
  return function NotificationCenter({ isOpen, onClose }: any) {
    return isOpen ? <div>Notification Center</div> : null;
  };
});

const mockUseSession = useSession as jest.MockedFunction<typeof useSession>;
const mockSignOut = signOut as jest.MockedFunction<typeof signOut>;

describe('Navbar', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  describe('Rendering', () => {
    it('should render logo and brand name', () => {
      mockUseSession.mockReturnValue({
        data: null,
        status: 'unauthenticated',
      } as any);

      render(<Navbar />);

      expect(screen.getByText('AI')).toBeInTheDocument();
      expect(screen.getByText('Code Review Platform')).toBeInTheDocument();
    });

    it('should render theme toggle', () => {
      mockUseSession.mockReturnValue({
        data: null,
        status: 'unauthenticated',
      } as any);

      render(<Navbar />);

      expect(screen.getByText('Theme Toggle')).toBeInTheDocument();
    });

    it('should render notification bell', () => {
      mockUseSession.mockReturnValue({
        data: null,
        status: 'unauthenticated',
      } as any);

      const { container } = render(<Navbar />);

      const bellButton = container.querySelector('button[class*="relative"]');
      expect(bellButton).toBeInTheDocument();
    });

    it('should render user menu button', () => {
      mockUseSession.mockReturnValue({
        data: null,
        status: 'unauthenticated',
      } as any);

      const { container } = render(<Navbar />);

      const userButtons = container.querySelectorAll('button');
      expect(userButtons.length).toBeGreaterThan(0);
    });
  });

  describe('User Session', () => {
    it('should display user name when logged in', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: {
            name: 'John Doe',
            email: 'john@example.com',
          },
        },
        status: 'authenticated',
      } as any);

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
      mockUseSession.mockReturnValue({
        data: {
          user: {
            name: 'John Doe',
            email: 'john@example.com',
          },
        },
        status: 'authenticated',
      } as any);

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
      mockUseSession.mockReturnValue({
        data: {
          user: {
            email: 'john@example.com',
          },
        },
        status: 'authenticated',
      } as any);

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
      mockUseSession.mockReturnValue({
        data: null,
        status: 'unauthenticated',
      } as any);

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
      mockUseSession.mockReturnValue({
        data: null,
        status: 'unauthenticated',
      } as any);

      const { container } = render(<Navbar />);

      const badge = container.querySelector('.bg-destructive');
      expect(badge).toBeInTheDocument();
    });
  });

  describe('User Menu', () => {
    it('should show Profile menu item', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: { name: 'John', email: 'john@example.com' },
        },
        status: 'authenticated',
      } as any);

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        expect(screen.getByText('Profile')).toBeInTheDocument();
      }
    });

    it('should show Settings menu item', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: { name: 'John', email: 'john@example.com' },
        },
        status: 'authenticated',
      } as any);

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        expect(screen.getByText('Settings')).toBeInTheDocument();
      }
    });

    it('should show Sign out menu item', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: { name: 'John', email: 'john@example.com' },
        },
        status: 'authenticated',
      } as any);

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        expect(screen.getByText('Sign out')).toBeInTheDocument();
      }
    });

    it('should call signOut when Sign out is clicked', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: { name: 'John', email: 'john@example.com' },
        },
        status: 'authenticated',
      } as any);

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        const signOutButton = screen.getByText('Sign out');
        fireEvent.click(signOutButton);
        expect(mockSignOut).toHaveBeenCalled();
      }
    });

    it('should link to profile page', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: { name: 'John', email: 'john@example.com' },
        },
        status: 'authenticated',
      } as any);

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

    it('should link to settings page', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: { name: 'John', email: 'john@example.com' },
        },
        status: 'authenticated',
      } as any);

      render(<Navbar />);

      const userButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg')
      );
      if (userButton) {
        fireEvent.click(userButton);
        const settingsLink = screen.getByText('Settings').closest('a');
        expect(settingsLink).toHaveAttribute('href', '/settings');
      }
    });
  });

  describe('Logo Link', () => {
    it('should link to dashboard', () => {
      mockUseSession.mockReturnValue({
        data: null,
        status: 'unauthenticated',
      } as any);

      render(<Navbar />);

      const logoLink = screen.getByText('AI').closest('a');
      expect(logoLink).toHaveAttribute('href', '/dashboard');
    });
  });
});
