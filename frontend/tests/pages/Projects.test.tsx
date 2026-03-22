/**
 * Projectscomponent单元test
 * 
 * test范围:
 * - project列表展示
 * - VirtualListintegration?00+project?
 * - project选择feature
 * - loadanderror状?
 * - ErrorBoundaryintegration
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Projects } from '../Projects';
import * as useProjectsHook from '../../hooks/useProjects';
import type { Project } from '../../hooks/useProjects';

// Mock hooks
jest.mock('../../hooks/useProjects');

// Mock components
jest.mock('../../components/VirtualList', () => ({
  VirtualList: ({ items, renderItem }: any) => (
    <div data-testid="virtual-list">
      {items.map((item: any, index: number) => (
        <div key={item.id}>{renderItem(item, index)}</div>
      ))}
    </div>
  ),
}));

jest.mock('../../components/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: any) => <div>{children}</div>,
}));

jest.mock('../../components/LoadingState', () => ({
  LoadingState: ({ text }: any) => <div data-testid="loading-state">{text}</div>,
}));

jest.mock('../../components/OfflineIndicator', () => ({
  OfflineIndicator: () => <div data-testid="offline-indicator" />,
}));

/**
 * Helper function to get sort buttons (not drag-and-drop buttons)
 */
function getSortButton(name: string | RegExp) {
  const buttons = screen.getAllByRole('button', { name });
  // Filter out sortable drag-and-drop buttons (they have aria-roledescription="sortable")
  const sortButton = buttons.find(btn => !btn.getAttribute('aria-roledescription'));
  if (!sortButton) {
    throw new Error(`Could not find sort button with name: ${name}`);
  }
  return sortButton;
}

// Helper function to create mock projects
function createMockProject(overrides?: Partial<Project>): Project {
  const id = overrides?.id || `project-${Math.random()}`;
  return {
    id,
    name: overrides?.name || `Project ${id}`,
    description: overrides?.description || `Description for ${id}`,
    github_repo_url: overrides?.github_repo_url || null,
    github_connection_type: overrides?.github_connection_type || 'https',
    github_ssh_key_id: overrides?.github_ssh_key_id || null,
    language: overrides?.language || 'TypeScript',
    is_active: overrides?.is_active !== undefined ? overrides.is_active : true,
    owner_id: overrides?.owner_id || 'user-1',
    created_at: overrides?.created_at || new Date().toISOString(),
    updated_at: overrides?.updated_at || new Date().toISOString(),
  };
}

// Helper function to create QueryClient
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

// Helper function to render with providers
function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('Projects Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should display loading state while fetching projects', () => {
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      expect(screen.getByTestId('loading-state')).toBeInTheDocument();
      expect(screen.getByText('Loading projects...')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should display error message when fetch fails', () => {
      const errorMessage = 'Network error';
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error(errorMessage),
      } as any);

      renderWithProviders(<Projects />);

      expect(screen.getByText('⚠️ Failed to load projects')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should display empty state when no projects exist', () => {
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      expect(screen.getByText('No projects found')).toBeInTheDocument();
      expect(screen.getByText('Create your first project to get started')).toBeInTheDocument();
    });
  });

  describe('Project List Display', () => {
    it('should display project list with correct information', () => {
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project Alpha', language: 'TypeScript' }),
        createMockProject({ id: '2', name: 'Project Beta', language: 'Python' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      expect(screen.getByText('Project Beta')).toBeInTheDocument();
      expect(screen.getByText('2 projects')).toBeInTheDocument();
    });

    it('should display project details correctly', () => {
      const mockProject = createMockProject({
        id: '1',
        name: 'Test Project',
        description: 'Test Description',
        language: 'JavaScript',
        is_active: true,
      });

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: [mockProject],
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      expect(screen.getByText('Test Project')).toBeInTheDocument();
      expect(screen.getByText('Test Description')).toBeInTheDocument();
      expect(screen.getByText(/Language: JavaScript/)).toBeInTheDocument();
      expect(screen.getByText(/Status:.*Active/)).toBeInTheDocument();
    });
  });

  describe('VirtualList Integration', () => {
    it('should use VirtualList when project count exceeds 100', () => {
      const mockProjects = Array.from({ length: 150 }, (_, i) =>
        createMockProject({ id: `project-${i}`, name: `Project ${i}` })
      );

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects enableVirtualScroll={true} />);

      // VirtualListshould被使?
      expect(screen.getByTestId('virtual-list')).toBeInTheDocument();
    });

    it('should not use VirtualList when project count is below 100', () => {
      const mockProjects = Array.from({ length: 50 }, (_, i) =>
        createMockProject({ id: `project-${i}`, name: `Project ${i}` })
      );

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects enableVirtualScroll={true} />);

      // VirtualList不should被use
      expect(screen.queryByTestId('virtual-list')).not.toBeInTheDocument();
    });

    it('should not use VirtualList when disabled', () => {
      const mockProjects = Array.from({ length: 150 }, (_, i) =>
        createMockProject({ id: `project-${i}`, name: `Project ${i}` })
      );

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects enableVirtualScroll={false} />);

      // VirtualList不should被use
      expect(screen.queryByTestId('virtual-list')).not.toBeInTheDocument();
    });
  });

  describe('Project Selection', () => {
    it('should allow selecting individual projects', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
        createMockProject({ id: '2', name: 'Project 2' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // get第一itemproject的checkbox
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes[0]).not.toBeChecked();

      // 点击checkbox
      await user.click(checkboxes[0]);

      // verify选中状?
      expect(checkboxes[0]).toBeChecked();
      expect(screen.getByText('1 selected')).toBeInTheDocument();
    });

    it('should allow deselecting projects', async () => {
      const user = userEvent.setup();
      const mockProjects = [createMockProject({ id: '1', name: 'Project 1' })];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const checkbox = screen.getAllByRole('checkbox')[0];

      // 选中
      await user.click(checkbox);
      expect(checkbox).toBeChecked();

      // cancel选中
      await user.click(checkbox);
      expect(checkbox).not.toBeChecked();
    });

    it('should support select all functionality', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
        createMockProject({ id: '2', name: 'Project 2' }),
        createMockProject({ id: '3', name: 'Project 3' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 点击"Select All"button
      const selectAllButton = screen.getByRole('button', { name: /select all/i });
      await user.click(selectAllButton);

      // verify所有project被选中
      expect(screen.getByText('3 selected')).toBeInTheDocument();
      const checkboxes = screen.getAllByRole('checkbox');
      checkboxes.forEach((checkbox) => {
        expect(checkbox).toBeChecked();
      });
    });

    it('should support deselect all functionality', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
        createMockProject({ id: '2', name: 'Project 2' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 先全?
      const selectAllButton = screen.getByRole('button', { name: /select all/i });
      await user.click(selectAllButton);
      expect(screen.getByText('2 selected')).toBeInTheDocument();

      // 再cancel全?
      const deselectAllButton = screen.getByRole('button', { name: /deselect all/i });
      await user.click(deselectAllButton);

      // verify没有project被选中
      expect(screen.queryByText(/selected/)).not.toBeInTheDocument();
    });
  });

  describe('Component Integration', () => {
    it('should render OfflineIndicator', () => {
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: [createMockProject()],
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      expect(screen.getByTestId('offline-indicator')).toBeInTheDocument();
    });

    it('should display correct project count in header', () => {
      const mockProjects = Array.from({ length: 42 }, (_, i) =>
        createMockProject({ id: `project-${i}` })
      );

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      expect(screen.getByText('42 projects')).toBeInTheDocument();
    });

    it('should use singular form for single project', () => {
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: [createMockProject()],
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      expect(screen.getByText('1 project')).toBeInTheDocument();
    });
  });

  describe('Search and Filter', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
    });

    it('should render search input', () => {
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: [createMockProject()],
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const searchInput = screen.getByPlaceholderText(/search projects/i);
      expect(searchInput).toBeInTheDocument();
    });

    it('should filter projects by name with debouncing', async () => {
      const user = userEvent.setup({ delay: null });
      const mockProjects = [
        createMockProject({ id: '1', name: 'Alpha Project' }),
        createMockProject({ id: '2', name: 'Beta Project' }),
        createMockProject({ id: '3', name: 'Gamma Project' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 所有projectshould可?
      expect(screen.getByText('Alpha Project')).toBeInTheDocument();
      expect(screen.getByText('Beta Project')).toBeInTheDocument();
      expect(screen.getByText('Gamma Project')).toBeInTheDocument();

      // inputsearch?
      const searchInput = screen.getByPlaceholderText(/search projects/i);
      await user.type(searchInput, 'Alpha');

      // wait防抖延迟?00ms?
      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      // waitReactupdate
      await waitFor(() => {
        expect(screen.getByText('Alpha Project')).toBeInTheDocument();
        expect(screen.queryByText('Beta Project')).not.toBeInTheDocument();
        expect(screen.queryByText('Gamma Project')).not.toBeInTheDocument();
      });
    });

    it('should filter projects by description', async () => {
      const user = userEvent.setup({ delay: null });
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1', description: 'Frontend application' }),
        createMockProject({ id: '2', name: 'Project 2', description: 'Backend service' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const searchInput = screen.getByPlaceholderText(/search projects/i);
      await user.type(searchInput, 'Frontend');

      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByText('Project 1')).toBeInTheDocument();
        expect(screen.queryByText('Project 2')).not.toBeInTheDocument();
      });
    });

    it('should filter projects by language', async () => {
      const user = userEvent.setup({ delay: null });
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1', language: 'TypeScript' }),
        createMockProject({ id: '2', name: 'Project 2', language: 'Python' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const searchInput = screen.getByPlaceholderText(/search projects/i);
      await user.type(searchInput, 'Python');

      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.queryByText('Project 1')).not.toBeInTheDocument();
        expect(screen.getByText('Project 2')).toBeInTheDocument();
      });
    });

    it('should filter projects by status', async () => {
      const user = userEvent.setup({ delay: null });
      const mockProjects = [
        createMockProject({ id: '1', name: 'Active Project', is_active: true }),
        createMockProject({ id: '2', name: 'Inactive Project', is_active: false }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const searchInput = screen.getByPlaceholderText(/search projects/i);
      await user.type(searchInput, 'inactive');

      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.queryByText('Active Project')).not.toBeInTheDocument();
        expect(screen.getByText('Inactive Project')).toBeInTheDocument();
      });
    });

    it('should be case-insensitive', async () => {
      const user = userEvent.setup({ delay: null });
      const mockProjects = [
        createMockProject({ id: '1', name: 'UPPERCASE PROJECT' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const searchInput = screen.getByPlaceholderText(/search projects/i);
      await user.type(searchInput, 'uppercase');

      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByText('UPPERCASE PROJECT')).toBeInTheDocument();
      });
    });

    it('should show clear button when search has text', async () => {
      const user = userEvent.setup({ delay: null });
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: [createMockProject()],
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const searchInput = screen.getByPlaceholderText(/search projects/i);
      
      // 清除button不should存?
      expect(screen.queryByLabelText('Clear search')).not.toBeInTheDocument();

      // input文本
      await user.type(searchInput, 'test');

      // 清除buttonshould出现
      expect(screen.getByLabelText('Clear search')).toBeInTheDocument();
    });

    it('should clear search when clear button is clicked', async () => {
      const user = userEvent.setup({ delay: null });
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: [createMockProject({ name: 'Test Project' })],
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const searchInput = screen.getByPlaceholderText(/search projects/i) as HTMLInputElement;
      await user.type(searchInput, 'test');

      expect(searchInput.value).toBe('test');

      const clearButton = screen.getByLabelText('Clear search');
      await user.click(clearButton);

      expect(searchInput.value).toBe('');
    });

    it('should show no results message when search has no matches', async () => {
      const user = userEvent.setup({ delay: null });
      const mockProjects = [
        createMockProject({ id: '1', name: 'Alpha Project' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const searchInput = screen.getByPlaceholderText(/search projects/i);
      await user.type(searchInput, 'NonExistent');

      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      await waitFor(() => {
        expect(screen.getByText('No projects match your search')).toBeInTheDocument();
        expect(screen.getByText('Try adjusting your search terms')).toBeInTheDocument();
      });
    });

    it('should update project count when filtering', async () => {
      const user = userEvent.setup({ delay: null });
      const mockProjects = [
        createMockProject({ id: '1', name: 'Alpha Project' }),
        createMockProject({ id: '2', name: 'Beta Project' }),
        createMockProject({ id: '3', name: 'Gamma Project' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 初始计数
      expect(screen.getByText('3 projects')).toBeInTheDocument();

      // search
      const searchInput = screen.getByPlaceholderText(/search projects/i);
      await user.type(searchInput, 'Alpha');

      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      // filter后的计数
      await waitFor(() => {
        expect(screen.getByText('1 project of 3')).toBeInTheDocument();
      });
    });

    it('should debounce search input within 300ms', async () => {
      const user = userEvent.setup({ delay: null });
      const mockProjects = [
        createMockProject({ id: '1', name: 'Alpha Project' }),
        createMockProject({ id: '2', name: 'Beta Project' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const searchInput = screen.getByPlaceholderText(/search projects/i);

      // 快速input多item字?
      await user.type(searchInput, 'A');
      await act(async () => {
        jest.advanceTimersByTime(100);
      });
      await user.type(searchInput, 'l');
      await act(async () => {
        jest.advanceTimersByTime(100);
      });
      await user.type(searchInput, 'p');

      // ?00ms之前，filter不should生效
      expect(screen.getByText('Alpha Project')).toBeInTheDocument();
      expect(screen.getByText('Beta Project')).toBeInTheDocument();

      // wait防抖延迟
      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      // 现在filtershould生效
      await waitFor(() => {
        expect(screen.getByText('Alpha Project')).toBeInTheDocument();
        expect(screen.queryByText('Beta Project')).not.toBeInTheDocument();
      });
    });
  });

  describe('Sorting', () => {
    it('should render sorting buttons', () => {
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: [createMockProject()],
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      expect(getSortButton(/Name/i)).toBeInTheDocument();
      expect(getSortButton(/Created/i)).toBeInTheDocument();
      expect(getSortButton(/Updated/i)).toBeInTheDocument();
      expect(getSortButton(/Status/i)).toBeInTheDocument();
    });

    it('should sort projects by name in ascending order by default', () => {
      const mockProjects = [
        createMockProject({ id: '1', name: 'Zebra Project' }),
        createMockProject({ id: '2', name: 'Alpha Project' }),
        createMockProject({ id: '3', name: 'Beta Project' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const projectNames = screen.getAllByRole('heading', { level: 3 });
      expect(projectNames[0]).toHaveTextContent('Alpha Project');
      expect(projectNames[1]).toHaveTextContent('Beta Project');
      expect(projectNames[2]).toHaveTextContent('Zebra Project');
    });

    it('should toggle sort order when clicking the same sort button', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Alpha Project' }),
        createMockProject({ id: '2', name: 'Beta Project' }),
        createMockProject({ id: '3', name: 'Zebra Project' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 初始sort：升?
      let projectNames = screen.getAllByRole('heading', { level: 3 });
      expect(projectNames[0]).toHaveTextContent('Alpha Project');
      expect(projectNames[2]).toHaveTextContent('Zebra Project');

      // 点击名称button切换为降?
      const nameButton = getSortButton(/Name/i);
      await user.click(nameButton);

      projectNames = screen.getAllByRole('heading', { level: 3 });
      expect(projectNames[0]).toHaveTextContent('Zebra Project');
      expect(projectNames[2]).toHaveTextContent('Alpha Project');

      // 再times点击切换回升?
      await user.click(nameButton);

      projectNames = screen.getAllByRole('heading', { level: 3 });
      expect(projectNames[0]).toHaveTextContent('Alpha Project');
      expect(projectNames[2]).toHaveTextContent('Zebra Project');
    });

    it('should sort projects by created date', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1', created_at: '2024-01-15T10:00:00Z' }),
        createMockProject({ id: '2', name: 'Project 2', created_at: '2024-01-10T10:00:00Z' }),
        createMockProject({ id: '3', name: 'Project 3', created_at: '2024-01-20T10:00:00Z' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 点击create日期button
      const createdButton = getSortButton(/Created/i);
      await user.click(createdButton);

      const projectNames = screen.getAllByRole('heading', { level: 3 });
      expect(projectNames[0]).toHaveTextContent('Project 2'); // 最?
      expect(projectNames[1]).toHaveTextContent('Project 1');
      expect(projectNames[2]).toHaveTextContent('Project 3'); // 最?
    });

    it('should sort projects by updated date', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1', updated_at: '2024-01-15T10:00:00Z' }),
        createMockProject({ id: '2', name: 'Project 2', updated_at: '2024-01-20T10:00:00Z' }),
        createMockProject({ id: '3', name: 'Project 3', updated_at: '2024-01-10T10:00:00Z' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 点击update日期button - use更具体的query
      const sortButtons = screen.getAllByRole('button', { name: /Updated/i });
      const updatedButton = sortButtons.find(btn => btn.textContent?.includes('Updated') && !btn.getAttribute('aria-roledescription'));
      expect(updatedButton).toBeDefined();
      await user.click(updatedButton!);

      const projectNames = screen.getAllByRole('heading', { level: 3 });
      expect(projectNames[0]).toHaveTextContent('Project 3'); // 最?
      expect(projectNames[1]).toHaveTextContent('Project 1');
      expect(projectNames[2]).toHaveTextContent('Project 2'); // 最?
    });

    it('should sort projects by status (active first)', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Inactive Project 1', is_active: false }),
        createMockProject({ id: '2', name: 'Active Project 1', is_active: true }),
        createMockProject({ id: '3', name: 'Inactive Project 2', is_active: false }),
        createMockProject({ id: '4', name: 'Active Project 2', is_active: true }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 点击status按?- use更具体的query
      const sortButtons = screen.getAllByRole('button', { name: /Status/i });
      const statusButton = sortButtons.find(btn => btn.textContent?.trim() === 'Status' && !btn.getAttribute('aria-roledescription'));
      expect(statusButton).toBeDefined();
      await user.click(statusButton!);

      const projectNames = screen.getAllByRole('heading', { level: 3 });
      // Active projects should come first
      expect(projectNames[0]).toHaveTextContent('Active Project');
      expect(projectNames[1]).toHaveTextContent('Active Project');
      expect(projectNames[2]).toHaveTextContent('Inactive Project');
      expect(projectNames[3]).toHaveTextContent('Inactive Project');
    });

    it('should show sort direction indicator on active sort button', async () => {
      const user = userEvent.setup();
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: [createMockProject()],
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      const nameButton = getSortButton(/Name/i);
      expect(nameButton).toHaveTextContent('↑');

      await user.click(nameButton);
      expect(nameButton).toHaveTextContent('↓');

      const createdButton = getSortButton(/Created/i);
      await user.click(createdButton);

      expect(createdButton).toHaveTextContent('↑');
      expect(nameButton).not.toHaveTextContent('↑');
      expect(nameButton).not.toHaveTextContent('↓');
    });

    it('should maintain sort when filtering', async () => {
      jest.useFakeTimers();
      const user = userEvent.setup({ delay: null });
      const mockProjects = [
        createMockProject({ id: '1', name: 'Zebra Alpha', description: 'Test' }),
        createMockProject({ id: '2', name: 'Alpha Beta', description: 'Test' }),
        createMockProject({ id: '3', name: 'Beta Gamma', description: 'Test' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 切换为降序排?
      const nameButton = getSortButton(/Name/i);
      await user.click(nameButton);

      // verify降序sort
      let projectNames = screen.getAllByRole('heading', { level: 3 });
      expect(projectNames[0]).toHaveTextContent('Zebra Alpha');

      // 应用filter
      const searchInput = screen.getByPlaceholderText(/search projects/i);
      await user.type(searchInput, 'Alpha');

      await act(async () => {
        jest.advanceTimersByTime(300);
      });

      // verifyfilter后仍保持降序sort
      await waitFor(() => {
        projectNames = screen.getAllByRole('heading', { level: 3 });
        expect(projectNames.length).toBe(2);
        expect(projectNames[0]).toHaveTextContent('Zebra Alpha');
        expect(projectNames[1]).toHaveTextContent('Alpha Beta');
      });

      jest.runOnlyPendingTimers();
      jest.useRealTimers();
    });

    it('should reset to ascending order when changing sort criteria', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ 
          id: '1', 
          name: 'Alpha Project',
          created_at: '2024-01-20T10:00:00Z'
        }),
        createMockProject({ 
          id: '2', 
          name: 'Beta Project',
          created_at: '2024-01-10T10:00:00Z'
        }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Projects />);

      // 切换名称sort为降?
      const nameButton = getSortButton(/Name/i);
      await user.click(nameButton);
      expect(nameButton).toHaveTextContent('↓');

      const createdButton = getSortButton(/Created/i);
      await user.click(createdButton);

      expect(createdButton).toHaveTextContent('↑');
      
      const projectNames = screen.getAllByRole('heading', { level: 3 });
      expect(projectNames[0]).toHaveTextContent('Beta Project');
    });
  });

  describe('Batch Operations', () => {
    it('should show batch operation buttons when projects are selected', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
        createMockProject({ id: '2', name: 'Project 2' }),
      ];

      const mockUpdateProject = jest.fn().mockResolvedValue({});
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: mockUpdateProject,
        mutateAsync: jest.fn().mockResolvedValue({}),
      } as any);

      renderWithProviders(<Projects />);

      // 批量操作button不shouldshow
      expect(screen.queryByRole('button', { name: /Delete/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Archive/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Add Tag/i })).not.toBeInTheDocument();

      // 选中一itemproject
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      // 批量操作buttonshouldshow
      expect(screen.getByRole('button', { name: /Delete/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Archive/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Add Tag/i })).toBeInTheDocument();
    });

    it('should perform batch delete operation', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
        createMockProject({ id: '2', name: 'Project 2' }),
        createMockProject({ id: '3', name: 'Project 3' }),
      ];

      const mockMutateAsync = jest.fn().mockResolvedValue({});
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: mockMutateAsync,
      } as any);

      // Mock window.confirm
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      renderWithProviders(<Projects />);

      // 选中两itemproject
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);
      await user.click(checkboxes[1]);

      expect(screen.getByText('2 selected')).toBeInTheDocument();

      // 点击deletebutton
      const deleteButton = screen.getByRole('button', { name: /Delete/i });
      await user.click(deleteButton);

      // verifyconfirm对话框
      expect(confirmSpy).toHaveBeenCalledWith(
        expect.stringContaining('Are you sure you want to delete 2 projects?')
      );

      // wait异步操作complete
      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledTimes(2);
      });

      // verify调用param（软delete：set为不活跃）
      expect(mockMutateAsync).toHaveBeenCalledWith({
        projectId: '1',
        updates: { is_active: false },
      });
      expect(mockMutateAsync).toHaveBeenCalledWith({
        projectId: '2',
        updates: { is_active: false },
      });

      // verifysuccesshint
      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith('Successfully deleted 2 projects');
      });

      // verifyproject从列表中移除
      await waitFor(() => {
        expect(screen.queryByText('Project 1')).not.toBeInTheDocument();
        expect(screen.queryByText('Project 2')).not.toBeInTheDocument();
        expect(screen.getByText('Project 3')).toBeInTheDocument();
      });

      confirmSpy.mockRestore();
      alertSpy.mockRestore();
    });

    it('should cancel batch delete when user declines confirmation', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
      ];

      const mockMutateAsync = jest.fn();
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: mockMutateAsync,
      } as any);

      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);

      renderWithProviders(<Projects />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      const deleteButton = screen.getByRole('button', { name: /Delete/i });
      await user.click(deleteButton);

      expect(confirmSpy).toHaveBeenCalled();
      expect(mockMutateAsync).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it('should perform batch archive operation', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1', is_active: true }),
        createMockProject({ id: '2', name: 'Project 2', is_active: true }),
      ];

      const mockMutateAsync = jest.fn().mockResolvedValue({});
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: mockMutateAsync,
      } as any);

      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      renderWithProviders(<Projects />);

      // 选中project
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      // 点击归档button
      const archiveButton = screen.getByRole('button', { name: /Archive/i });
      await user.click(archiveButton);

      expect(confirmSpy).toHaveBeenCalledWith(
        expect.stringContaining('Are you sure you want to archive 1 project?')
      );

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          projectId: '1',
          updates: { is_active: false },
        });
      });

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith('Successfully archived 1 project');
      });

      confirmSpy.mockRestore();
      alertSpy.mockRestore();
    });

    it('should open tag modal when Add Tag button is clicked', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: jest.fn().mockResolvedValue({}),
      } as any);

      renderWithProviders(<Projects />);

      // 选中project
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      // 点击addtagbutton
      const tagButton = screen.getByRole('button', { name: /Add Tag/i });
      await user.click(tagButton);

      // verify模态框open
      expect(screen.getByText(/Add Tags to 1 Project/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Enter tags.../i)).toBeInTheDocument();
    });

    it('should perform batch tag operation', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1', description: 'Original description' }),
        createMockProject({ id: '2', name: 'Project 2', description: null }),
      ];

      const mockMutateAsync = jest.fn().mockResolvedValue({});
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: mockMutateAsync,
      } as any);

      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      renderWithProviders(<Projects />);

      // 选中两itemproject
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);
      await user.click(checkboxes[1]);

      // opentag模态框
      const tagButton = screen.getByRole('button', { name: /Add Tag/i });
      await user.click(tagButton);

      // inputtag
      const tagInput = screen.getByPlaceholderText(/Enter tags.../i);
      await user.type(tagInput, 'frontend, react, typescript');

      // 点击addbutton
      const addButton = screen.getByRole('button', { name: /Add Tags/i });
      await user.click(addButton);

      // verifyAPI调用
      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledTimes(2);
      });

      // verifytag被add到description中
      expect(mockMutateAsync).toHaveBeenCalledWith({
        projectId: '1',
        updates: { description: 'Original description [Tags: frontend, react, typescript]' },
      });
      expect(mockMutateAsync).toHaveBeenCalledWith({
        projectId: '2',
        updates: { description: '[Tags: frontend, react, typescript]' },
      });

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith('Successfully added tags to 2 projects');
      });

      alertSpy.mockRestore();
    });

    it('should close tag modal when Cancel button is clicked', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: jest.fn().mockResolvedValue({}),
      } as any);

      renderWithProviders(<Projects />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      const tagButton = screen.getByRole('button', { name: /Add Tag/i });
      await user.click(tagButton);

      expect(screen.getByText(/Add Tags to 1 Project/i)).toBeInTheDocument();

      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      await user.click(cancelButton);

      // verify模态框close
      await waitFor(() => {
        expect(screen.queryByText(/Add Tags to 1 Project/i)).not.toBeInTheDocument();
      });
    });

    it('should close tag modal when clicking outside', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: jest.fn().mockResolvedValue({}),
      } as any);

      renderWithProviders(<Projects />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      const tagButton = screen.getByRole('button', { name: /Add Tag/i });
      await user.click(tagButton);

      // 点击模态框外部（背景）
      const modalBackdrop = screen.getByText(/Add Tags to 1 Project/i).parentElement?.parentElement;
      if (modalBackdrop) {
        await user.click(modalBackdrop);
      }

      // verify模态框close
      await waitFor(() => {
        expect(screen.queryByText(/Add Tags to 1 Project/i)).not.toBeInTheDocument();
      });
    });

    it('should support Enter key to submit tags', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1', description: null }),
      ];

      const mockMutateAsync = jest.fn().mockResolvedValue({});
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: mockMutateAsync,
      } as any);

      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      renderWithProviders(<Projects />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      const tagButton = screen.getByRole('button', { name: /Add Tag/i });
      await user.click(tagButton);

      const tagInput = screen.getByPlaceholderText(/Enter tags.../i);
      await user.type(tagInput, 'test-tag');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          projectId: '1',
          updates: { description: '[Tags: test-tag]' },
        });
      });

      alertSpy.mockRestore();
    });

    it('should support Escape key to close tag modal', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: jest.fn().mockResolvedValue({}),
      } as any);

      renderWithProviders(<Projects />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      const tagButton = screen.getByRole('button', { name: /Add Tag/i });
      await user.click(tagButton);

      const tagInput = screen.getByPlaceholderText(/Enter tags.../i);
      await user.type(tagInput, '{Escape}');

      await waitFor(() => {
        expect(screen.queryByText(/Add Tags to 1 Project/i)).not.toBeInTheDocument();
      });
    });

    it('should disable Add Tags button when input is empty', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
      ];

      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: jest.fn().mockResolvedValue({}),
      } as any);

      renderWithProviders(<Projects />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      const tagButton = screen.getByRole('button', { name: /Add Tag/i });
      await user.click(tagButton);

      const addButton = screen.getByRole('button', { name: /Add Tags/i });
      expect(addButton).toBeDisabled();

      const tagInput = screen.getByPlaceholderText(/Enter tags.../i);
      await user.type(tagInput, 'test');

      expect(addButton).not.toBeDisabled();
    });

    it('should show loading indicator during batch operations', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
      ];

      // Create a promise that we can control
      let resolvePromise: () => void;
      const promise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      const mockMutateAsync = jest.fn().mockReturnValue(promise);
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: mockMutateAsync,
      } as any);

      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      renderWithProviders(<Projects />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      const deleteButton = screen.getByRole('button', { name: /Delete/i });
      await user.click(deleteButton);

      // verifyload指示器show
      await waitFor(() => {
        expect(screen.getByText('Processing batch operation...')).toBeInTheDocument();
      });

      // complete操作
      resolvePromise!();

      // verifyload指示器消失
      await waitFor(() => {
        expect(screen.queryByText('Processing batch operation...')).not.toBeInTheDocument();
      });

      confirmSpy.mockRestore();
      alertSpy.mockRestore();
    });

    it('should handle batch operation errors gracefully', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
      ];

      const mockMutateAsync = jest.fn().mockRejectedValue(new Error('Network error'));
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: mockMutateAsync,
      } as any);

      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      renderWithProviders(<Projects />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      const deleteButton = screen.getByRole('button', { name: /Delete/i });
      await user.click(deleteButton);

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith('Failed to delete some projects. Please try again.');
      });

      expect(consoleErrorSpy).toHaveBeenCalledWith('Batch delete failed:', expect.any(Error));

      confirmSpy.mockRestore();
      alertSpy.mockRestore();
      consoleErrorSpy.mockRestore();
    });

    it('should clear selection after successful batch operation', async () => {
      const user = userEvent.setup();
      const mockProjects = [
        createMockProject({ id: '1', name: 'Project 1' }),
        createMockProject({ id: '2', name: 'Project 2' }),
      ];

      const mockMutateAsync = jest.fn().mockResolvedValue({});
      jest.spyOn(useProjectsHook, 'useProjects').mockReturnValue({
        data: mockProjects,
        isLoading: false,
        error: null,
      } as any);
      jest.spyOn(useProjectsHook, 'useUpdateProject').mockReturnValue({
        mutate: jest.fn(),
        mutateAsync: mockMutateAsync,
      } as any);

      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      renderWithProviders(<Projects />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[0]);

      expect(screen.getByText('1 selected')).toBeInTheDocument();

      const archiveButton = screen.getByRole('button', { name: /Archive/i });
      await user.click(archiveButton);

      await waitFor(() => {
        expect(screen.queryByText(/selected/)).not.toBeInTheDocument();
      });

      confirmSpy.mockRestore();
      alertSpy.mockRestore();
    });
  });
});
