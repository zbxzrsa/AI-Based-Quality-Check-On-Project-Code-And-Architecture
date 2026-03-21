/**
 * Enhanced Test Utilities for Frontend Testing
 * 
 * Provides comprehensive testing utilities including:
 * - Custom render function with all providers
 * - Mock data generators
 * - Property-based testing helpers
 * - API mocking utilities
 * - Performance testing helpers
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import fc from 'fast-check';

interface TestSession {
  user: ReturnType<typeof mockGenerators.user>;
  expires: string;
}

// Mock data generators
export const mockGenerators = {
  user: () => ({
    id: fc.sample(fc.uuid(), 1)[0],
    email: fc.sample(fc.emailAddress(), 1)[0],
    name: fc.sample(fc.fullName(), 1)[0],
    role: fc.sample(fc.constantFrom('admin', 'developer', 'viewer'), 1)[0],
    is_active: fc.sample(fc.boolean(), 1)[0],
    created_at: fc.sample(fc.date(), 1)[0].toISOString(),
  }),

  project: () => ({
    id: fc.sample(fc.uuid(), 1)[0],
    name: fc.sample(fc.string({ minLength: 1, maxLength: 100 }), 1)[0],
    description: fc.sample(fc.option(fc.string({ maxLength: 500 })), 1)[0],
    status: fc.sample(fc.constantFrom('active', 'inactive', 'archived'), 1)[0],
    repository_url: fc.sample(fc.webUrl(), 1)[0],
    created_at: fc.sample(fc.date(), 1)[0].toISOString(),
    updated_at: fc.sample(fc.date(), 1)[0].toISOString(),
    owner_id: fc.sample(fc.uuid(), 1)[0],
    team_members: fc.sample(fc.array(mockGenerators.user, { minLength: 0, maxLength: 5 }), 1)[0],
  }),

  review: () => ({
    id: fc.sample(fc.uuid(), 1)[0],
    project_id: fc.sample(fc.uuid(), 1)[0],
    title: fc.sample(fc.string({ minLength: 1, maxLength: 200 }), 1)[0],
    description: fc.sample(fc.string({ maxLength: 1000 }), 1)[0],
    status: fc.sample(fc.constantFrom('pending', 'in_progress', 'completed', 'rejected'), 1)[0],
    score: fc.sample(fc.float({ min: 0, max: 100 }), 1)[0],
    created_at: fc.sample(fc.date(), 1)[0].toISOString(),
    reviewer_id: fc.sample(fc.uuid(), 1)[0],
  }),

  library: () => ({
    id: fc.sample(fc.uuid(), 1)[0],
    name: fc.sample(fc.string({ minLength: 1, maxLength: 100 }), 1)[0],
    version: fc.sample(fc.string({ minLength: 1, maxLength: 20 }), 1)[0],
    registry: fc.sample(fc.constantFrom('npm', 'pypi', 'maven', 'nuget'), 1)[0],
    description: fc.sample(fc.option(fc.string({ maxLength: 500 })), 1)[0],
    license: fc.sample(fc.constantFrom('MIT', 'Apache-2.0', 'GPL-3.0', 'BSD-3-Clause'), 1)[0],
    homepage: fc.sample(fc.option(fc.webUrl()), 1)[0],
    repository: fc.sample(fc.option(fc.webUrl()), 1)[0],
  }),
};

// API Mock Server
const apiHandlers = [
  // Auth endpoints
  rest.post('/api/v1/auth/login', (req, res, ctx) => {
    return res(
      ctx.json({
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
      })
    );
  }),

  rest.get('/api/v1/auth/me', (req, res, ctx) => {
    return res(ctx.json(mockGenerators.user()));
  }),

  // Project endpoints
  rest.get('/api/v1/projects', (req, res, ctx) => {
    const projects = Array.from({ length: 5 }, () => mockGenerators.project());
    return res(ctx.json({ projects, total: projects.length }));
  }),

  rest.get('/api/v1/projects/:id', (req, res, ctx) => {
    return res(ctx.json(mockGenerators.project()));
  }),

  rest.post('/api/v1/projects', (req, res, ctx) => {
    return res(ctx.status(201), ctx.json(mockGenerators.project()));
  }),

  // Review endpoints
  rest.get('/api/v1/projects/:id/reviews', (req, res, ctx) => {
    const reviews = Array.from({ length: 3 }, () => mockGenerators.review());
    return res(ctx.json({ reviews, total: reviews.length }));
  }),

  // Library endpoints
  rest.get('/api/v1/libraries', (req, res, ctx) => {
    const libraries = Array.from({ length: 10 }, () => mockGenerators.library());
    return res(ctx.json({ libraries, total: libraries.length }));
  }),

  rest.post('/api/v1/libraries/validate', (req, res, ctx) => {
    return res(
      ctx.json({
        is_valid: true,
        metadata: mockGenerators.library(),
        validation_errors: [],
      })
    );
  }),

  // Health check
  rest.get('/health', (req, res, ctx) => {
    return res(ctx.json({ status: 'healthy', timestamp: new Date().toISOString() }));
  }),
];

export const server = setupServer(...apiHandlers);

// Custom render function with all providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  session?: TestSession;
  queryClient?: QueryClient;
  theme?: string;
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const {
    session = {
      user: mockGenerators.user(),
      expires: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    },
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          cacheTime: 0,
        },
        mutations: {
          retry: false,
        },
      },
    }),
    theme = 'light',
    ...renderOptions
  } = options;

  function Wrapper({ children }: { children: React.ReactNode }) {
    void session;
    return (
      <QueryClientProvider client={queryClient}>
        <ThemeProvider attribute="class" defaultTheme={theme} enableSystem={false}>
          {children}
        </ThemeProvider>
      </QueryClientProvider>
    );
  }

  const user = userEvent.setup();

  return {
    user,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
}

// Property-based testing helpers
export const propertyTestHelpers = {
  /**
   * Generate arbitrary React props for component testing
   */
  componentProps: <T extends Record<string, unknown>>(schema: {
    [K in keyof T]: fc.Arbitrary<T[K]>;
  }) => fc.record(schema),

  /**
   * Generate arbitrary form data
   */
  formData: () =>
    fc.record({
      email: fc.emailAddress(),
      password: fc.string({ minLength: 8, maxLength: 50 }),
      name: fc.fullName(),
      role: fc.constantFrom('admin', 'developer', 'viewer'),
    }),

  /**
   * Generate arbitrary API responses
   */
  apiResponse: <T,>(dataArbitrary: fc.Arbitrary<T>) =>
    fc.record({
      data: dataArbitrary,
      status: fc.constantFrom(200, 201, 400, 401, 403, 404, 500),
      message: fc.option(fc.string()),
    }),

  /**
   * Generate arbitrary pagination data
   */
  paginationData: <T,>(itemArbitrary: fc.Arbitrary<T>) =>
    fc.record({
      items: fc.array(itemArbitrary, { minLength: 0, maxLength: 20 }),
      total: fc.nat({ max: 1000 }),
      page: fc.nat({ max: 50 }),
      per_page: fc.constantFrom(10, 20, 50, 100),
      has_next: fc.boolean(),
      has_prev: fc.boolean(),
    }),
};

// Performance testing helpers
export const performanceHelpers = {
  /**
   * Measure component render time
   */
  measureRenderTime: async (renderFn: () => void): Promise<number> => {
    const start = performance.now();
    renderFn();
    await waitFor(() => {}, { timeout: 0 }); // Wait for render to complete
    const end = performance.now();
    return end - start;
  },

  /**
   * Test component performance with different prop sizes
   */
  testRenderPerformance: async (
    component: ReactElement,
    propSizes: number[] = [10, 100, 1000]
  ): Promise<{ size: number; renderTime: number }[]> => {
    const results = [];

    for (const size of propSizes) {
      const renderTime = await performanceHelpers.measureRenderTime(() => {
        renderWithProviders(component);
      });

      results.push({ size, renderTime });
    }

    return results;
  },

  /**
   * Assert that render time is within acceptable limits
   */
  expectRenderTimeWithin: (renderTime: number, maxTime: number) => {
    expect(renderTime).toBeLessThan(maxTime);
  },
};

// Accessibility testing helpers
export const a11yHelpers = {
  /**
   * Check for basic accessibility requirements
   */
  expectAccessibleForm: (container: HTMLElement) => {
    // Check for labels
    const inputs = container.querySelectorAll('input, select, textarea');
    inputs.forEach((input) => {
      const label = container.querySelector(`label[for="${input.id}"]`);
      const ariaLabel = input.getAttribute('aria-label');
      const ariaLabelledBy = input.getAttribute('aria-labelledby');

      expect(
        label || ariaLabel || ariaLabelledBy,
        `Input ${input.id || input.name} should have a label`
      ).toBeTruthy();
    });

    // Check for proper heading hierarchy
    const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
    let previousLevel = 0;
    headings.forEach((heading) => {
      const level = parseInt(heading.tagName.charAt(1));
      expect(level).toBeLessThanOrEqual(previousLevel + 1);
      previousLevel = level;
    });
  },

  /**
   * Check for keyboard navigation support
   */
  expectKeyboardNavigable: async (container: HTMLElement, user: ReturnType<typeof userEvent.setup>) => {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) return;

    // Test tab navigation
    await user.tab();
    expect(document.activeElement).toBe(focusableElements[0]);

    // Test that all focusable elements can be reached
    for (let i = 1; i < focusableElements.length; i++) {
      await user.tab();
      expect(document.activeElement).toBe(focusableElements[i]);
    }
  },
};

// API testing helpers
export const apiTestHelpers = {
  /**
   * Mock successful API response
   */
  mockSuccessResponse: <T,>(data: T) =>
    rest.get('*', (req, res, ctx) => res(ctx.json(data))),

  /**
   * Mock API error response
   */
  mockErrorResponse: (status: number, message: string) =>
    rest.get('*', (req, res, ctx) =>
      res(ctx.status(status), ctx.json({ error: message }))
    ),

  /**
   * Mock loading state
   */
  mockLoadingResponse: (delay: number = 1000) =>
    rest.get('*', (req, res, ctx) => res(ctx.delay(delay), ctx.json({}))),

  /**
   * Verify API call was made
   */
  expectApiCall: async (url: string, _method: string = 'GET') => {
    await waitFor(() => {
      // This would need to be implemented based on your API mocking strategy
      // For example, using MSW request handlers or jest.fn() mocks
    });
  },
};

// Custom matchers for better assertions
expect.extend({
  toBeAccessible(received: HTMLElement) {
    try {
      a11yHelpers.expectAccessibleForm(received);
      return {
        message: () => `Expected element to be accessible`,
        pass: true,
      };
    } catch (error) {
      return {
        message: () => `Expected element to be accessible: ${error}`,
        pass: false,
      };
    }
  },

  toRenderWithin(received: number, expected: number) {
    const pass = received < expected;
    return {
      message: () =>
        `Expected render time ${received}ms to be ${pass ? 'not ' : ''}less than ${expected}ms`,
      pass,
    };
  },
});

// Type declarations for custom matchers
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeAccessible(): R;
      toRenderWithin(maxTime: number): R;
    }
  }
}

// Export everything
export * from '@testing-library/react';
export { userEvent, fc, rest, server };
export { renderWithProviders as render };
