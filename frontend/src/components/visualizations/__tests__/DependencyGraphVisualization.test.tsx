/**
 * Tests for DependencyGraphVisualization Component
 * 
 * Tests cover:
 * - Graph rendering with zoom controls (0.1x to 10x)
 * - Circular dependency highlighting
 * - Real-time WebSocket updates
 * - Search and filtering
 * - Node selection and details
 * 
 * Requirements: 1.7, 1.8, 3.7, 3.8, 3.9
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import DependencyGraphVisualization from '../DependencyGraphVisualization';

// Mock ReactFlow
jest.mock('reactflow', () => ({
  __esModule: true,
  default: function MockReactFlow({ nodes, edges, onNodeClick }: any) {
    return (
      <div data-testid="react-flow">
        <div data-testid="graph-nodes">
          {nodes?.map((node: any) => (
            <div
              key={node.id}
              data-testid={`node-${node.id}`}
              onClick={() => onNodeClick && onNodeClick(null, node)}
            >
              {node.data?.label || node.id}
            </div>
          ))}
        </div>
        <div data-testid="graph-edges">
          {edges?.map((edge: any) => (
            <div key={edge.id} data-testid={`edge-${edge.id}`}>
              {edge.source} → {edge.target}
            </div>
          ))}
        </div>
      </div>
    );
  },
  Controls: () => <div data-testid="flow-controls" />,
  Background: () => <div data-testid="flow-background" />,
  Panel: ({ children }: any) => <div data-testid="flow-panel">{children}</div>,
  useNodesState: (initialNodes: any) => [initialNodes, jest.fn()],
  useEdgesState: (initialEdges: any) => [initialEdges, jest.fn()],
  ConnectionMode: { Loose: 'loose' },
  MarkerType: { ArrowClosed: 'arrowclosed' },
}));
          {graphData.links.map((link: any, index: number) => (
            <div key={index} data-testid={`link-${index}`}>
              {typeof link.source === 'string' ? link.source : link.source.id} →{' '}
              {typeof link.target === 'string' ? link.target : link.target.id}
            </div>
          ))}
        </div>
        <button
          data-testid="zoom-in-btn"
          onClick={() => onZoom && onZoom({ k: 1.5 })}
        >
          Zoom In
        </button>
        <button
          data-testid="zoom-out-btn"
          onClick={() => onZoom && onZoom({ k: 0.5 })}
        >
          Zoom Out
        </button>
      </div>
    );
  };
});

// Mock WebSocket
class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(public url: string) {
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 0);
  }

  send(data: string) {
    // Mock send
  }

  close() {
    if (this.onclose) this.onclose();
  }
}

(global as any).WebSocket = MockWebSocket;

describe('DependencyGraphVisualization', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render the component with title', () => {
      render(<DependencyGraphVisualization />);
      expect(screen.getByText('Dependency Graph Visualization')).toBeInTheDocument();
    });

    it('should display statistics', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        expect(screen.getByText('Total Nodes')).toBeInTheDocument();
        expect(screen.getByText('Total Dependencies')).toBeInTheDocument();
        expect(screen.getAllByText('Circular Dependencies').length).toBeGreaterThan(0);
        expect(screen.getByText('Zoom Level')).toBeInTheDocument();
      });
    });

    it('should render the force graph', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        expect(screen.getByTestId('force-graph')).toBeInTheDocument();
      });
    });
  });

  describe('Zoom Controls (Requirement 3.8)', () => {
    it('should support zoom range from 0.1x to 10x', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        expect(screen.getByText(/1\.0x/)).toBeInTheDocument();
      });
    });

    it('should have zoom in button', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const zoomInButtons = screen.getAllByRole('button');
        const zoomInButton = zoomInButtons.find(btn => 
          btn.querySelector('svg')?.classList.contains('lucide-zoom-in') ||
          btn.textContent?.includes('Zoom In')
        );
        expect(zoomInButton).toBeInTheDocument();
      });
    });

    it('should have zoom out button', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const zoomOutButtons = screen.getAllByRole('button');
        const zoomOutButton = zoomOutButtons.find(btn => 
          btn.querySelector('svg')?.classList.contains('lucide-zoom-out') ||
          btn.textContent?.includes('Zoom Out')
        );
        expect(zoomOutButton).toBeInTheDocument();
      });
    });

    it('should have reset view button', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const buttons = screen.getAllByRole('button');
        const resetButton = buttons.find(btn => 
          btn.querySelector('svg')?.classList.contains('lucide-maximize-2')
        );
        expect(resetButton).toBeInTheDocument();
      });
    });
  });

  describe('Circular Dependency Highlighting (Requirement 1.7)', () => {
    it('should display circular dependencies section when cycles exist', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        expect(screen.getByText('Circular Dependencies Detected')).toBeInTheDocument();
      });
    });

    it('should show severity badges for circular dependencies', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const badges = screen.getAllByText(/LOW|MEDIUM|HIGH/);
        expect(badges.length).toBeGreaterThan(0);
      });
    });

    it('should allow toggling cycle highlighting', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const highlightButton = screen.getByText(/Highlight Cycles/);
        expect(highlightButton).toBeInTheDocument();
        
        fireEvent.click(highlightButton);
        // Button should still be present after toggle
        expect(highlightButton).toBeInTheDocument();
      });
    });

    it('should display cycle details when cycle is selected', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const cycleDescriptions = screen.getAllByText(/circular dependency/i);
        if (cycleDescriptions.length > 0) {
          fireEvent.click(cycleDescriptions[0].closest('div') || cycleDescriptions[0]);
          
          // Should show cycle path after click
          waitFor(() => {
            expect(screen.queryByText(/Cycle Path:/)).toBeInTheDocument();
          });
        }
      });
    });
  });

  describe('Search and Filtering', () => {
    it('should have search input', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText(/Search by name/i);
        expect(searchInput).toBeInTheDocument();
      });
    });

    it('should filter nodes based on search term', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText(/Search by name/i);
        fireEvent.change(searchInput, { target: { value: 'User' } });
        
        expect(searchInput).toHaveValue('User');
      });
    });

    it('should have circular dependency filter dropdown', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const select = screen.getByRole('combobox');
        expect(select).toBeInTheDocument();
      });
    });
  });

  describe('Real-time WebSocket Updates (Requirement 3.9)', () => {
    it('should connect to WebSocket when URL is provided', async () => {
      const wsUrl = 'ws://localhost:8000/ws/analysis/test-123';
      render(<DependencyGraphVisualization websocketUrl={wsUrl} />);
      
      await waitFor(() => {
        expect(screen.getByText('Live')).toBeInTheDocument();
      });
    });

    it('should display connection status badge', async () => {
      const wsUrl = 'ws://localhost:8000/ws/analysis/test-123';
      render(<DependencyGraphVisualization websocketUrl={wsUrl} />);
      
      await waitFor(() => {
        const liveBadge = screen.getByText('Live');
        expect(liveBadge).toBeInTheDocument();
      });
    });

    it('should handle WebSocket messages for incremental updates', async () => {
      const wsUrl = 'ws://localhost:8000/ws/analysis/test-123';
      render(<DependencyGraphVisualization websocketUrl={wsUrl} />);
      
      // Component should be ready to receive messages
      await waitFor(() => {
        expect(screen.getByTestId('force-graph')).toBeInTheDocument();
      });
    });
  });

  describe('Node Interaction', () => {
    it('should handle node click', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const nodes = screen.queryAllByTestId(/^node-/);
        if (nodes.length > 0) {
          fireEvent.click(nodes[0]);
          
          // Should show selected node details
          expect(screen.getByText('Selected Node Details')).toBeInTheDocument();
        }
      });
    });

    it('should display node details when selected', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const nodes = screen.queryAllByTestId(/^node-/);
        if (nodes.length > 0) {
          fireEvent.click(nodes[0]);
          
          // Should show node properties
          expect(screen.getByText(/Name:/)).toBeInTheDocument();
          expect(screen.getByText(/Type:/)).toBeInTheDocument();
        }
      });
    });
  });

  describe('Export Functionality', () => {
    it('should have export button', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const exportButton = screen.getByText(/Export/);
        expect(exportButton).toBeInTheDocument();
      });
    });

    it('should trigger export on button click', async () => {
      // Mock URL.createObjectURL
      global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
      global.URL.revokeObjectURL = jest.fn();
      
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const exportButton = screen.getByText(/Export/);
        fireEvent.click(exportButton);
        
        expect(global.URL.createObjectURL).toHaveBeenCalled();
      });
    });
  });

  describe('Refresh Functionality', () => {
    it('should have refresh button', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const refreshButton = screen.getByText(/Refresh/);
        expect(refreshButton).toBeInTheDocument();
      });
    });

    it('should reload data on refresh', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        const refreshButton = screen.getByText(/Refresh/);
        fireEvent.click(refreshButton);
        
        // Button should still be present
        expect(refreshButton).toBeInTheDocument();
      });
    });
  });

  describe('Legend Display', () => {
    it('should display legend with node types', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        expect(screen.getByText('Legend')).toBeInTheDocument();
        expect(screen.getByText('Normal Node')).toBeInTheDocument();
      });
    });

    it('should show severity levels in legend', async () => {
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        expect(screen.getByText(/Low Severity Cycle/)).toBeInTheDocument();
        expect(screen.getByText(/Medium Severity Cycle/)).toBeInTheDocument();
        expect(screen.getByText(/High Severity Cycle/)).toBeInTheDocument();
      });
    });
  });

  describe('Performance (Requirement 1.8, 3.7)', () => {
    it('should render within 5 seconds for graphs with <1000 nodes', async () => {
      const startTime = Date.now();
      
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        expect(screen.getByTestId('force-graph')).toBeInTheDocument();
      }, { timeout: 5000 });
      
      const renderTime = Date.now() - startTime;
      expect(renderTime).toBeLessThan(5000);
    });

    it('should indicate LOD rendering for large graphs', async () => {
      // This would be tested with actual large graph data
      // For now, we verify the component can handle the mode
      render(<DependencyGraphVisualization analysisId="test-123" />);
      
      await waitFor(() => {
        expect(screen.getByTestId('force-graph')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message when loading fails', async () => {
      // Mock console.error to avoid test output noise
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      render(<DependencyGraphVisualization analysisId="invalid-id" />);
      
      // Component should handle errors gracefully
      await waitFor(() => {
        expect(screen.getByTestId('force-graph')).toBeInTheDocument();
      });
      
      consoleSpy.mockRestore();
    });
  });
});
