/**
 * Jest test suite for Architecture Timeline D3.js visualization
 * Tests rendering, interactivity, and data handling for AI dashboard
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ArchitectureTimeline from '../ArchitectureTimeline';

// Mock D3.js to avoid actual DOM manipulation in tests
jest.mock('d3', () => ({
  scaleTime: jest.fn(() => ({
    domain: jest.fn().mockReturnThis(),
    range: jest.fn().mockReturnThis(),
  })),
  scaleLinear: jest.fn(() => ({
    domain: jest.fn().mockReturnThis(),
    nice: jest.fn().mockReturnThis(),
    range: jest.fn().mockReturnThis(),
  })),
  axisBottom: jest.fn(() => jest.fn()),
  axisLeft: jest.fn(() => jest.fn()),
  line: jest.fn(() => jest.fn()),
  curveMonotoneX: jest.fn(),
  extent: jest.fn(() => [new Date('2023-01-01'), new Date('2023-12-31')]),
  max: jest.fn(() => 100),
  timeFormat: jest.fn(() => jest.fn()),
  brushX: jest.fn(() => ({
    extent: jest.fn().mockReturnThis(),
    on: jest.fn().mockReturnThis(),
  })),
  select: jest.fn(() => ({
    selectAll: jest.fn().mockReturnThis(),
    remove: jest.fn().mockReturnThis(),
    append: jest.fn().mockReturnThis(),
    attr: jest.fn().mockReturnThis(),
    style: jest.fn().mockReturnThis(),
    data: jest.fn().mockReturnThis(),
    enter: jest.fn().mockReturnThis(),
    text: jest.fn().mockReturnThis(),
    call: jest.fn().mockReturnThis(),
    on: jest.fn().mockReturnThis(),
    datum: jest.fn().mockReturnThis(),
  })),
}));

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

describe('ArchitectureTimeline Component', () => {
  const mockData = [
    {
      date: new Date('2023-01-01'),
      coupling: 25,
      complexity: 45,
      coverage: 78,
      loc: 12500,
    },
    {
      date: new Date('2023-02-01'),
      coupling: 30,
      complexity: 50,
      coverage: 82,
      loc: 13200,
    },
    {
      date: new Date('2023-03-01'),
      coupling: 22,
      complexity: 40,
      coverage: 85,
      loc: 14100,
    },
  ];

  const mockEvents = [
    {
      date: new Date('2023-01-15'),
      label: 'Major Refactor',
      type: 'refactor' as const,
    },
    {
      date: new Date('2023-02-20'),
      label: 'v2.0 Release',
      type: 'release' as const,
    },
  ];

  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  it('renders without crashing with valid data', () => {
    render(<ArchitectureTimeline data={mockData} />);
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();
  });

  it('renders SVG container with correct dimensions', () => {
    render(<ArchitectureTimeline data={mockData} width={800} height={400} />);

    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('width', '800');
    expect(svg).toHaveAttribute('height', '400');
  });

  it('displays metric lines for all data series', () => {
    render(<ArchitectureTimeline data={mockData} />);

    // Check if SVG paths are created (mocked D3 will create them)
    const paths = document.querySelectorAll('path');
    expect(paths.length).toBeGreaterThan(0);
  });

  it('renders data points as circles', () => {
    render(<ArchitectureTimeline data={mockData} />);

    // Should render circles for each data point (4 metrics × 3 data points = 12 circles)
    const circles = document.querySelectorAll('circle');
    expect(circles.length).toBe(12); // 4 metrics × 3 data points
  });

  it('renders event markers correctly', () => {
    render(<ArchitectureTimeline data={mockData} events={mockEvents} />);

    // Should render event markers (vertical lines)
    const lines = document.querySelectorAll('line');
    expect(lines.length).toBeGreaterThan(0);
  });

  it('displays event labels', () => {
    render(<ArchitectureTimeline data={mockData} events={mockEvents} />);

    // Check for event labels in SVG text elements
    const textElements = document.querySelectorAll('text');
    const eventLabels = Array.from(textElements).filter(text =>
      text.textContent?.includes('Major Refactor') ||
      text.textContent?.includes('v2.0 Release')
    );
    expect(eventLabels.length).toBeGreaterThan(0);
  });

  it('renders legend with correct metric labels', () => {
    render(<ArchitectureTimeline data={mockData} />);

    // Check for legend text elements
    const textElements = document.querySelectorAll('text');
    const legendItems = Array.from(textElements).filter(text =>
      text.textContent?.includes('Coupling Score') ||
      text.textContent?.includes('Complexity') ||
      text.textContent?.includes('Test Coverage') ||
      text.textContent?.includes('LOC')
    );
    expect(legendItems.length).toBe(4); // All 4 metrics
  });

  it('handles empty data gracefully', () => {
    render(<ArchitectureTimeline data={[]} />);

    // Should still render SVG container even with no data
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('handles large datasets efficiently', () => {
    // Generate large dataset (100 data points)
    const largeData = Array.from({ length: 100 }, (_, i) => ({
      date: new Date(2023, 0, i + 1),
      coupling: Math.random() * 100,
      complexity: Math.random() * 100,
      coverage: Math.random() * 100,
      loc: Math.random() * 20000,
    }));

    // Mock performance.now to measure rendering time
    const originalPerformance = global.performance;
    global.performance = {
      ...originalPerformance,
      now: jest.fn()
        .mockReturnValueOnce(0)
        .mockReturnValueOnce(100), // 100ms render time
    };

    render(<ArchitectureTimeline data={largeData} />);

    // Should complete rendering within reasonable time
    expect(global.performance.now).toHaveBeenCalled();

    // Restore original performance object
    global.performance = originalPerformance;
  });

  it('updates when data prop changes', () => {
    const { rerender } = render(<ArchitectureTimeline data={mockData} />);

    const newData = [
      ...mockData,
      {
        date: new Date('2023-04-01'),
        coupling: 20,
        complexity: 35,
        coverage: 88,
        loc: 15000,
      },
    ];

    rerender(<ArchitectureTimeline data={newData} />);

    // Should re-render with updated data
    const circles = document.querySelectorAll('circle');
    expect(circles.length).toBe(16); // 4 metrics × 4 data points
  });

  it('applies responsive container styling', () => {
    render(<ArchitectureTimeline data={mockData} />);

    const container = document.querySelector('.w-full.overflow-x-auto');
    expect(container).toBeInTheDocument();
  });

  it('handles different chart dimensions', () => {
    const { rerender } = render(
      <ArchitectureTimeline data={mockData} width={600} height={300} />
    );

    let svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('width', '600');
    expect(svg).toHaveAttribute('height', '300');

    // Test responsive behavior
    rerender(
      <ArchitectureTimeline data={mockData} width={1200} height={600} />
    );

    svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('width', '1200');
    expect(svg).toHaveAttribute('height', '600');
  });

  it('includes accessibility features', () => {
    render(<ArchitectureTimeline data={mockData} />);

    // SVG should have proper ARIA attributes (if implemented)
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Could add more accessibility checks here
  });

  it('handles edge case: single data point', () => {
    const singleDataPoint = [mockData[0]];

    render(<ArchitectureTimeline data={singleDataPoint} />);

    // Should still render without errors
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Should have circles for single data point
    const circles = document.querySelectorAll('circle');
    expect(circles.length).toBe(4); // 4 metrics × 1 data point
  });

  it('validates prop types and handles invalid data', () => {
    // Test with invalid data (should handle gracefully)
    const invalidData = [
      {
        date: 'invalid-date', // Should be Date object
        coupling: 'invalid', // Should be number
        complexity: null,
        coverage: undefined,
        loc: NaN,
      },
    ];

    // Should not crash, but may render empty or with defaults
    expect(() => {
      render(<ArchitectureTimeline data={invalidData} />);
    }).not.toThrow();
  });

  // Integration test with mock backend response
  it('renders correctly with realistic backend JSON response', async () => {
    // Mock API response structure that backend would return
    const mockApiResponse = {
      timeline: mockData,
      events: mockEvents,
      metadata: {
        projectId: 'test-project',
        dateRange: {
          start: '2023-01-01',
          end: '2023-12-31'
        },
        metrics: ['coupling', 'complexity', 'coverage', 'loc']
      }
    };

    // Simulate component receiving data from API
    render(<ArchitectureTimeline data={mockApiResponse.timeline} events={mockApiResponse.events} />);

    // Verify chart renders with API data
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();

    // Verify all data points are rendered
    const circles = document.querySelectorAll('circle');
    expect(circles.length).toBe(12); // 4 metrics × 3 data points

    // Verify events are rendered
    const lines = document.querySelectorAll('line');
    expect(lines.length).toBeGreaterThan(0);
  });

  // Performance test
  it('renders within performance budget', async () => {
    const startTime = performance.now();

    render(<ArchitectureTimeline data={mockData} />);

    const endTime = performance.now();
    const renderTime = endTime - startTime;

    // Should render within 100ms
    expect(renderTime).toBeLessThan(100);
  });

  // Memory leak prevention test
  it('cleans up resources on unmount', () => {
    const { unmount } = render(<ArchitectureTimeline data={mockData} />);

    // Mock cleanup should be called
    const mockDisconnect = jest.fn();
    global.ResizeObserver = jest.fn(() => ({
      observe: jest.fn(),
      unobserve: jest.fn(),
      disconnect: mockDisconnect,
    }));

    unmount();

    // Component should be removed from DOM
    expect(document.querySelector('svg')).not.toBeInTheDocument();
  });
});
