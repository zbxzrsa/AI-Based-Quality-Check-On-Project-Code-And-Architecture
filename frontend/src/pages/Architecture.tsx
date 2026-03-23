/**
 * Architecture Visualization Page Component
 * 
 * This component provides a graph-based visualization of system architecture,
 * displaying components and their dependencies as nodes and edges.
 * 
 * Features:
 * - Node-based graph rendering using ReactFlow
 * - Support for hierarchical component structures
 * - Visual representation of dependencies
 * - Performance metrics display on nodes
 * 
 * Requirements: 4.1
 */

'use client';

import React, { useCallback, useMemo, useState, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MiniMap,
  BackgroundVariant,
  NodeTypes,
  MarkerType,
  Panel,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
// Placeholder for export functionality
// TODO: Implement export using html-to-image directly
import 'reactflow/dist/style.css';
import '../styles/responsive.css';

/**
 * Architecture node data model
 * Represents a component in the system architecture
 */
export interface ArchitectureNode {
  id: string;
  name: string;
  type: 'service' | 'component' | 'module' | 'database' | 'external';
  description?: string;
  children: ArchitectureNode[];
  dependencies: string[]; // IDs of dependent nodes
  metrics?: {
    responseTime: number; // milliseconds
    errorRate: number; // percentage
    throughput: number; // requests/second
  };
  position?: { x: number; y: number };
}

/**
 * Props for the Architecture component
 */
export interface ArchitectureProps {
  data?: ArchitectureNode;
  onNodeClick?: (node: ArchitectureNode) => void;
  onExport?: (format: 'png' | 'svg') => void;
}

/**
 * Custom node component for architecture visualization
 * Displays node information including type, metrics, and health status
 */
function ArchitectureNodeComponent({ data }: { data: any }) {
  const getNodeColor = (type: string) => {
    switch (type) {
      case 'service':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-950/30';
      case 'component':
        return 'border-green-500 bg-green-50 dark:bg-green-950/30';
      case 'module':
        return 'border-purple-500 bg-purple-50 dark:bg-purple-950/30';
      case 'database':
        return 'border-orange-500 bg-orange-50 dark:bg-orange-950/30';
      case 'external':
        return 'border-gray-500 bg-gray-50 dark:bg-gray-950/30';
      default:
        return 'border-gray-500 bg-gray-50 dark:bg-gray-950/30';
    }
  };

  const getHealthStatus = (metrics?: any) => {
    if (!metrics) return 'unknown';
    if (metrics.errorRate > 5) return 'critical';
    if (metrics.errorRate > 1 || metrics.responseTime > 1000) return 'warning';
    return 'healthy';
  };

  const healthStatus = getHealthStatus(data.metrics);
  const healthColor = {
    healthy: 'text-green-600',
    warning: 'text-yellow-600',
    critical: 'text-red-600',
    unknown: 'text-gray-600',
  }[healthStatus];

  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 ${getNodeColor(
        data.type
      )} min-w-[160px] shadow-md hover:shadow-lg transition-shadow ${
        data.isSelected ? 'ring-2 ring-blue-500 ring-offset-2' : ''
      } ${data.isHighlighted && !data.isSelected ? 'ring-1 ring-blue-300' : ''}`}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="font-semibold text-sm">{data.label}</div>
        {data.metrics && (
          <div
            className={`w-2 h-2 rounded-full ${
              healthStatus === 'healthy'
                ? 'bg-green-500'
                : healthStatus === 'warning'
                ? 'bg-yellow-500'
                : healthStatus === 'critical'
                ? 'bg-red-500'
                : 'bg-gray-500'
            }`}
            title={`Health: ${healthStatus}`}
          />
        )}
      </div>
      <div className="text-xs text-muted-foreground mb-2 capitalize">
        {data.type}
      </div>

      {data.metrics && (
        <div className="text-xs space-y-1 border-t pt-2 mt-2">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Response:</span>
            <span className="font-medium">{data.metrics.responseTime}ms</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Error Rate:</span>
            <span className={`font-medium ${healthColor}`}>
              {data.metrics.errorRate}%
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Throughput:</span>
            <span className="font-medium">{data.metrics.throughput}/s</span>
          </div>
        </div>
      )}

      {data.hasChildren && (
        <div className="text-xs text-muted-foreground mt-2 italic flex items-center gap-1">
          <span>{data.isExpanded ? '▼' : '▶'}</span>
          <span>{data.isExpanded ? 'Click to collapse' : 'Click to expand'}</span>
        </div>
      )}
    </div>
  );
}


// Register custom node types
const nodeTypes: NodeTypes = {
  architectureNode: ArchitectureNodeComponent,
};

/**
 * Trace all dependency paths from a selected node
 * Returns a set of node IDs and edge IDs that are part of the dependency paths
 * 
 * Algorithm:
 * 1. Start from the selected node
 * 2. Follow all dependencies recursively (downstream)
 * 3. Find all nodes that depend on the selected node (upstream)
 * 4. Mark all nodes and edges in these paths
 */
function traceDependencyPaths(
  rootNode: ArchitectureNode,
  selectedNodeId: string
): { highlightedNodes: Set<string>; highlightedEdges: Set<string> } {
  const highlightedNodes = new Set<string>();
  const highlightedEdges = new Set<string>();
  
  // Build a map of all nodes for quick lookup
  const nodeMap = new Map<string, ArchitectureNode>();
  const buildNodeMap = (node: ArchitectureNode) => {
    nodeMap.set(node.id, node);
    node.children.forEach(buildNodeMap);
  };
  buildNodeMap(rootNode);
  
  // Build reverse dependency map (who depends on whom)
  const reverseDeps = new Map<string, Set<string>>();
  nodeMap.forEach((node) => {
    node.dependencies.forEach((depId) => {
      if (!reverseDeps.has(depId)) {
        reverseDeps.set(depId, new Set());
      }
      reverseDeps.get(depId)!.add(node.id);
    });
  });
  
  // Add the selected node itself
  highlightedNodes.add(selectedNodeId);
  
  // Trace downstream dependencies (nodes that the selected node depends on)
  const traceDownstream = (nodeId: string) => {
    const node = nodeMap.get(nodeId);
    if (!node) return;
    
    node.dependencies.forEach((depId) => {
      if (!highlightedNodes.has(depId)) {
        highlightedNodes.add(depId);
        highlightedEdges.add(`${nodeId}-${depId}`);
        traceDownstream(depId);
      } else {
        highlightedEdges.add(`${nodeId}-${depId}`);
      }
    });
  };
  
  // Trace upstream dependencies (nodes that depend on the selected node)
  const traceUpstream = (nodeId: string) => {
    const dependents = reverseDeps.get(nodeId);
    if (!dependents) return;
    
    dependents.forEach((dependentId) => {
      if (!highlightedNodes.has(dependentId)) {
        highlightedNodes.add(dependentId);
        highlightedEdges.add(`${dependentId}-${nodeId}`);
        traceUpstream(dependentId);
      } else {
        highlightedEdges.add(`${dependentId}-${nodeId}`);
      }
    });
  };
  
  traceDownstream(selectedNodeId);
  traceUpstream(selectedNodeId);
  
  return { highlightedNodes, highlightedEdges };
}

/**
 * Convert ArchitectureNode data model to ReactFlow nodes and edges
 */
function convertToFlowElements(
  rootNode: ArchitectureNode,
  expandedNodes: Set<string> = new Set(),
  selectedNodeId: string | null = null
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  let nodeIndex = 0;

  // Calculate highlighted paths if a node is selected
  const { highlightedNodes, highlightedEdges } = selectedNodeId
    ? traceDependencyPaths(rootNode, selectedNodeId)
    : { highlightedNodes: new Set<string>(), highlightedEdges: new Set<string>() };

  function processNode(
    node: ArchitectureNode,
    level: number = 0,
    parentX: number = 0,
    parentY: number = 0
  ) {
    const x = node.position?.x ?? parentX + (nodeIndex % 3) * 250;
    const y = node.position?.y ?? parentY + level * 150;
    nodeIndex++;

    const isHighlighted = highlightedNodes.has(node.id);
    const isSelected = node.id === selectedNodeId;

    nodes.push({
      id: node.id,
      type: 'architectureNode',
      data: {
        label: node.name,
        type: node.type,
        description: node.description,
        metrics: node.metrics,
        hasChildren: node.children.length > 0,
        isExpanded: expandedNodes.has(node.id),
        isHighlighted,
        isSelected,
      },
      position: { x, y },
      style: isHighlighted
        ? {
            opacity: 1,
            filter: isSelected ? 'drop-shadow(0 0 8px rgba(59, 130, 246, 0.8))' : 'none',
          }
        : selectedNodeId
        ? { opacity: 0.3 }
        : {},
    });

    // Add edges for dependencies
    node.dependencies.forEach((depId) => {
      const edgeId = `${node.id}-${depId}`;
      const isEdgeHighlighted = highlightedEdges.has(edgeId);
      
      edges.push({
        id: edgeId,
        source: node.id,
        target: depId,
        type: 'smoothstep',
        animated: isEdgeHighlighted,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 20,
          height: 20,
          color: isEdgeHighlighted ? '#3b82f6' : '#94a3b8',
        },
        style: {
          strokeWidth: isEdgeHighlighted ? 3 : 2,
          stroke: isEdgeHighlighted ? '#3b82f6' : '#94a3b8',
          opacity: isEdgeHighlighted ? 1 : selectedNodeId ? 0.3 : 1,
        },
      });
    });

    // Process children if node is expanded
    if (expandedNodes.has(node.id) && node.children.length > 0) {
      node.children.forEach((child, index) => {
        processNode(child, level + 1, x + index * 200, y);
      });
    }
  }

  processNode(rootNode);
  return { nodes, edges };
}

/**
 * Generate sample architecture data for demonstration
 */
function generateSampleData(): ArchitectureNode {
  return {
    id: 'root',
    name: 'Application',
    type: 'service',
    description: 'Main application service',
    children: [
      {
        id: 'frontend',
        name: 'Frontend',
        type: 'component',
        description: 'React frontend application',
        children: [],
        dependencies: ['api-gateway'],
        metrics: {
          responseTime: 120,
          errorRate: 0.5,
          throughput: 150,
        },
      },
      {
        id: 'api-gateway',
        name: 'API Gateway',
        type: 'service',
        description: 'API gateway service',
        children: [],
        dependencies: ['auth-service', 'data-service'],
        metrics: {
          responseTime: 45,
          errorRate: 0.2,
          throughput: 500,
        },
      },
      {
        id: 'auth-service',
        name: 'Auth Service',
        type: 'service',
        description: 'Authentication service',
        children: [],
        dependencies: ['database'],
        metrics: {
          responseTime: 30,
          errorRate: 0.1,
          throughput: 200,
        },
      },
      {
        id: 'data-service',
        name: 'Data Service',
        type: 'service',
        description: 'Data processing service',
        children: [],
        dependencies: ['database', 'cache'],
        metrics: {
          responseTime: 80,
          errorRate: 1.2,
          throughput: 300,
        },
      },
      {
        id: 'database',
        name: 'PostgreSQL',
        type: 'database',
        description: 'Primary database',
        children: [],
        dependencies: [],
        metrics: {
          responseTime: 15,
          errorRate: 0.05,
          throughput: 1000,
        },
      },
      {
        id: 'cache',
        name: 'Redis Cache',
        type: 'database',
        description: 'Caching layer',
        children: [],
        dependencies: [],
        metrics: {
          responseTime: 5,
          errorRate: 0.01,
          throughput: 2000,
        },
      },
    ],
    dependencies: [],
  };
}

/**
 * Architecture Component Inner
 * 
 * Inner component that has access to ReactFlow context for export functionality.
 */
function ArchitectureInner({
  data,
  onNodeClick,
  onExport,
}: ArchitectureProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { getNodes } = useReactFlow();
  
  // TODO: Implement export using html-to-image directly
  
  // Use provided data or generate sample data
  const architectureData = useMemo(
    () => data || generateSampleData(),
    [data]
  );

  // Convert architecture data to ReactFlow format
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => convertToFlowElements(architectureData, expandedNodes, selectedNodeId),
    [architectureData, expandedNodes, selectedNodeId]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Handle new connections
  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Handle node clicks
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      // Find the original node data
      const findNode = (n: ArchitectureNode): ArchitectureNode | null => {
        if (n.id === node.id) return n;
        for (const child of n.children) {
          const found = findNode(child);
          if (found) return found;
        }
        return null;
      };

      const originalNode = findNode(architectureData);
      if (originalNode) {
        // Toggle selection for dependency path highlighting
        setSelectedNodeId((prev) => (prev === node.id ? null : node.id));
        
        // Toggle expansion if node has children
        if (originalNode.children.length > 0) {
          setExpandedNodes((prev) => {
            const next = new Set(prev);
            if (next.has(node.id)) {
              next.delete(node.id);
            } else {
              next.add(node.id);
            }
            return next;
          });
        }

        // Call external click handler
        if (onNodeClick) {
          onNodeClick(originalNode);
        }
      }
    },
    [architectureData, onNodeClick]
  );

  // Update nodes and edges when expanded nodes or selected node change
  React.useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = convertToFlowElements(
      architectureData,
      expandedNodes,
      selectedNodeId
    );
    setNodes(newNodes);
    setEdges(newEdges);
  }, [expandedNodes, selectedNodeId, architectureData, setNodes, setEdges]);

  /**
   * Export the architecture diagram as PNG
   * Uses react-to-image to capture the ReactFlow viewport
   */
  const handleExportPNG = useCallback(async () => {
    // TODO: Re-enable when html-to-image integration is complete
    console.warn('Export PNG is temporarily disabled');
    setIsExporting(false);
  }, []);

  /**
   * Export the architecture diagram as SVG
   * Uses react-to-image to capture the ReactFlow viewport as SVG
   */
  const handleExportSVG = useCallback(async () => {
    // TODO: Re-enable when html-to-image integration is complete
    console.warn('Export SVG is temporarily disabled');
    setIsExporting(false);
  }, []);

  return (
    <div ref={reactFlowWrapper} className="w-full h-screen bg-background">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
        minZoom={0.1}
        maxZoom={2}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const type = node.data?.type;
            switch (type) {
              case 'service':
                return '#3b82f6';
              case 'component':
                return '#22c55e';
              case 'module':
                return '#a855f7';
              case 'database':
                return '#f97316';
              case 'external':
                return '#6b7280';
              default:
                return '#94a3b8';
            }
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
        <Panel position="top-left" className="bg-background/80 backdrop-blur-sm p-4 rounded-lg shadow-lg">
          <h2 className="text-lg font-semibold mb-2">Architecture Visualization</h2>
          {selectedNodeId && (
            <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-950/50 rounded border border-blue-200 dark:border-blue-800">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                Showing dependency paths for selected node
              </p>
              <button
                onClick={() => setSelectedNodeId(null)}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1"
              >
                Clear selection
              </button>
            </div>
          )}
          <div className="text-sm space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span>Service</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span>Component</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-purple-500"></div>
              <span>Module</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-orange-500"></div>
              <span>Database</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gray-500"></div>
              <span>External</span>
            </div>
          </div>
        </Panel>
        <Panel position="top-right" className="bg-background/80 backdrop-blur-sm p-4 rounded-lg shadow-lg">
          <h3 className="text-sm font-semibold mb-2">Export</h3>
          <div className="flex flex-col gap-2">
            <button
              onClick={handleExportPNG}
              disabled={isExporting}
              className="px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              title="Export as PNG image"
            >
              {isExporting ? 'Exporting...' : 'Export PNG'}
            </button>
            <button
              onClick={handleExportSVG}
              disabled={isExporting}
              className="px-3 py-2 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              title="Export as SVG vector"
            >
              {isExporting ? 'Exporting...' : 'Export SVG'}
            </button>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}

/**
 * Architecture Component
 * 
 * Main component wrapper that provides ReactFlow context.
 * Supports node interaction, dependency visualization, metrics display, and export.
 * 
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
 */
export default function Architecture(props: ArchitectureProps) {
  return (
    <ReactFlowProvider>
      <ArchitectureInner {...props} />
    </ReactFlowProvider>
  );
}
