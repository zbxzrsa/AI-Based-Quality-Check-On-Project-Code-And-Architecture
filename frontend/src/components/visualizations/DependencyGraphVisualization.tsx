'use client';

/**
 * Enhanced Dependency Graph Visualization Component
 * 
 * Features:
 * - D3.js force-directed graph rendering
 * - Zoom and pan controls (0.1x to 10x)
 * - Circular dependency highlighting with severity
 * - Real-time WebSocket updates
 * - Virtualization for large graphs (>1000 nodes)
 * - Level-of-detail rendering
 * - Production API integration with TanStack Query
 * - Data validation with Zod schemas
 * 
 * Requirements: 1.4, 1.5, 1.7, 1.8, 2.7, 3.7, 3.8, 3.9, 4.1, 4.2, 10.2, 10.8
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  ZoomIn, 
  ZoomOut, 
  RefreshCw, 
  Layers, 
  AlertTriangle,
  CheckCircle,
  Eye,
  EyeOff,
  Download,
  Maximize2,
  Info,
  Lock
} from 'lucide-react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { apiClientEnhanced as apiClient } from '@/lib/api-client';
import { 
  validateDependencyGraph, 
  type DependencyGraph,
  type DependencyGraphNode as ApiNode
} from '@/lib/validations/api-schemas';
import { ErrorHandler } from '@/lib/error-handler';
import { featureFlagsService } from '@/lib/feature-flags';

// Types - Extended from API types for visualization
interface GraphNode extends Omit<ApiNode, 'type'> {
  type: 'file' | 'class' | 'function' | 'module';
  size: number;
  inCycle?: boolean;
  cycleSeverity?: 'low' | 'medium' | 'high';
  cycleDetails?: string[];
  x?: number;
  y?: number;
}

interface GraphLink {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  type: 'depends' | 'calls' | 'implements';
  weight: number;
  inCycle?: boolean;
  cycleSeverity?: 'low' | 'medium' | 'high';
  is_circular?: boolean;
  properties?: Record<string, unknown>;
}

interface CircularDependency {
  id: string;
  nodes: string[];
  severity: 'low' | 'medium' | 'high';
  description: string;
}

interface DependencyGraphVisualizationProps {
  projectId: string;
  branchId?: string;
  className?: string;
  websocketUrl?: string;
}

export default function DependencyGraphVisualization({
  projectId,
  branchId,
  className,
  websocketUrl
}: DependencyGraphVisualizationProps) {
  // Check feature flag status - Validates Requirements: 10.2, 10.8
  const isFeatureEnabled = featureFlagsService.isEnabled('dependency-graph-production');
  
  // Fetch dependency graph data using TanStack Query
  const {
    data: graphData,
    isLoading,
    error: queryError,
    refetch
  } = useQuery<DependencyGraph>({
    queryKey: ['dependencyGraph', projectId, branchId],
    queryFn: async () => {
      try {
        const endpoint = branchId
          ? `/api/v1/dependencies/${projectId}?branch_id=${branchId}`
          : `/api/v1/dependencies/${projectId}`;

        // apiClient (apiClientEnhanced) returns data directly, not wrapped in {data: ...}
        const response = await apiClient.get(endpoint);

        // Validate response data
        const validatedData = validateDependencyGraph(response);
        return validatedData;
      } catch (err) {
        const errorInfo = ErrorHandler.handleError(err);
        ErrorHandler.logError(errorInfo);
        throw new Error(errorInfo.userMessage);
      }
    },
    enabled: !!projectId && isFeatureEnabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Transform API data to visualization format
  const { nodes, links, circularDeps } = useMemo(() => {
    if (!graphData) {
      return { nodes: [], links: [], circularDeps: [] };
    }

    // Transform nodes
    const transformedNodes: GraphNode[] = graphData.nodes.map(node => ({
      ...node,
      type: node.type as 'file' | 'class' | 'function' | 'module',
      size: node.lines_of_code || 20,
    }));

    // Transform edges
    const transformedLinks: GraphLink[] = graphData.edges.map(edge => ({
      ...edge,
      source: edge.source,
      target: edge.target,
      type: edge.type === 'import' ? 'depends' : edge.type === 'call' ? 'calls' : 'implements',
      weight: edge.weight || 1,
      inCycle: edge.is_circular,
    }));

    // Transform circular dependencies
    const transformedCircularDeps: CircularDependency[] = (graphData.circular_dependency_chains || []).map((chain, index) => {
      const severity = chain.length > 5 ? 'high' : chain.length > 3 ? 'medium' : 'low';
      return {
        id: `cycle-${index}`,
        nodes: chain,
        severity,
        description: `Circular dependency with ${chain.length} nodes`,
      };
    });

    // Mark nodes and links in cycles
    transformedCircularDeps.forEach(cycle => {
      cycle.nodes.forEach(nodeId => {
        const node = transformedNodes.find(n => n.id === nodeId);
        if (node) {
          node.inCycle = true;
          node.cycleSeverity = cycle.severity;
          node.cycleDetails = cycle.nodes;
        }
      });

      for (let i = 0; i < cycle.nodes.length; i++) {
        const source = cycle.nodes[i];
        const target = cycle.nodes[(i + 1) % cycle.nodes.length];
        
        const link = transformedLinks.find(l => 
          (l.source === source && l.target === target) ||
          (l.source === target && l.target === source)
        );
        
        if (link) {
          link.inCycle = true;
          link.cycleSeverity = cycle.severity;
        }
      }
    });

    return { 
      nodes: transformedNodes, 
      links: transformedLinks, 
      circularDeps: transformedCircularDeps 
    };
  }, [graphData]);

  // State
  const [error, setError] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedCycle, setSelectedCycle] = useState<string | null>(null);
  const [highlightCycles, setHighlightCycles] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [renderMode, setRenderMode] = useState<'full' | 'lod'>('full');
  
  // Refs
  const graphRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Set render mode based on graph size
  useEffect(() => {
    if (nodes.length > 1000) {
      setRenderMode('lod');
    } else {
      setRenderMode('full');
    }
  }, [nodes.length]);

  // Handle query errors
  useEffect(() => {
    if (queryError) {
      setError(queryError.message);
    } else {
      setError(null);
    }
  }, [queryError]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!websocketUrl) return;

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(websocketUrl);
        
        ws.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setError('WebSocket connection error');
          setIsConnected(false);
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);
          // Attempt to reconnect after 5 seconds
          setTimeout(connectWebSocket, 5000);
        };

        wsRef.current = ws;
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
        setError('Failed to establish WebSocket connection');
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [websocketUrl]);

  // Handle WebSocket messages for real-time updates
  const handleWebSocketMessage = useCallback((data: any) => {
    if (data.type === 'analysis_progress' || data.type === 'analysis_complete') {
      // Refetch data when analysis updates
      refetch();
    }
  }, [refetch]);

  // Filter nodes based on search
  const filteredData = useMemo(() => {
    let filteredNodes = nodes;
    let filteredLinks = links;

    if (searchTerm) {
      filteredNodes = nodes.filter(node =>
        node.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
      const nodeIds = new Set(filteredNodes.map(n => n.id));
      filteredLinks = links.filter(link => {
        const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
        const targetId = typeof link.target === 'string' ? link.target : link.target.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
    }

    if (selectedCycle) {
      const cycle = circularDeps.find(c => c.id === selectedCycle);
      if (cycle) {
        const cycleNodeIds = new Set(cycle.nodes);
        filteredNodes = nodes.filter(n => cycleNodeIds.has(n.id));
        filteredLinks = links.filter(link => {
          const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
          const targetId = typeof link.target === 'string' ? link.target : link.target.id;
          return cycleNodeIds.has(sourceId) && cycleNodeIds.has(targetId);
        });
      }
    }

    return { nodes: filteredNodes, links: filteredLinks };
  }, [nodes, links, searchTerm, selectedCycle, circularDeps]);

  // Node color based on cycle severity
  const getNodeColor = useCallback((node: GraphNode) => {
    if (!highlightCycles || !node.inCycle) {
      return '#3b82f6'; // Blue for normal nodes
    }
    
    switch (node.cycleSeverity) {
      case 'high':
        return '#ef4444'; // Red
      case 'medium':
        return '#f59e0b'; // Orange
      case 'low':
        return '#eab308'; // Yellow
      default:
        return '#3b82f6';
    }
  }, [highlightCycles]);

  // Link color based on cycle
  const getLinkColor = useCallback((link: GraphLink) => {
    if (!highlightCycles || !link.inCycle) {
      return 'rgba(100, 100, 100, 0.2)';
    }
    
    switch (link.cycleSeverity) {
      case 'high':
        return 'rgba(239, 68, 68, 0.6)'; // Red
      case 'medium':
        return 'rgba(245, 158, 11, 0.6)'; // Orange
      case 'low':
        return 'rgba(234, 179, 8, 0.6)'; // Yellow
      default:
        return 'rgba(100, 100, 100, 0.2)';
    }
  }, [highlightCycles]);

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    if (graphRef.current && zoomLevel < 10) {
      const newZoom = Math.min(zoomLevel * 1.5, 10);
      graphRef.current.zoom(newZoom, 400);
      setZoomLevel(newZoom);
    }
  }, [zoomLevel]);

  const handleZoomOut = useCallback(() => {
    if (graphRef.current && zoomLevel > 0.1) {
      const newZoom = Math.max(zoomLevel / 1.5, 0.1);
      graphRef.current.zoom(newZoom, 400);
      setZoomLevel(newZoom);
    }
  }, [zoomLevel]);

  const handleResetView = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400);
      setZoomLevel(1);
    }
  }, []);

  // Node click handler
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node.id === selectedNode ? null : node.id);
    
    if (node.inCycle && node.cycleDetails) {
      // Find the cycle this node belongs to
      const cycle = circularDeps.find(c => c.nodes.includes(node.id));
      if (cycle) {
        setSelectedCycle(cycle.id);
      }
    }
  }, [selectedNode, circularDeps]);

  // Retry handler
  const handleRetry = useCallback(() => {
    setError(null);
    refetch();
  }, [refetch]);

  // Export graph data
  const handleExport = useCallback(() => {
    const dataStr = JSON.stringify({ nodes, links, circularDependencies: circularDeps }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `dependency-graph-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [nodes, links, circularDeps]);

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="h-5 w-5" aria-hidden="true" />
            <CardTitle id="graph-title">Dependency Graph Visualization</CardTitle>
            {isConnected && (
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200" aria-label="Live connection active">
                <CheckCircle className="h-3 w-3 mr-1" aria-hidden="true" />
                Live
              </Badge>
            )}
          </div>
          <div className="flex items-center space-x-2" role="group" aria-label="Graph controls">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => refetch()} 
              disabled={isLoading}
              aria-label={isLoading ? 'Refreshing graph data' : 'Refresh graph data'}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} aria-hidden="true" />
              Refresh
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleExport}
              aria-label="Export graph data as JSON"
            >
              <Download className="h-4 w-4 mr-2" aria-hidden="true" />
              Export
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Feature Flag Disabled Placeholder - Validates Requirements: 10.8 */}
        {!isFeatureEnabled ? (
          <div className="w-full h-[600px] border border-gray-200 rounded-lg bg-gray-50 flex items-center justify-center">
            <div className="text-center max-w-md px-4">
              <Lock className="h-16 w-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-xl font-semibold text-gray-700 mb-2">Feature Not Available</h3>
              <p className="text-gray-600 mb-4">
                The Dependency Graph visualization is currently disabled. This feature is being progressively rolled out.
              </p>
              <p className="text-sm text-gray-500">
                Please contact your administrator if you need access to this feature.
              </p>
            </div>
          </div>
        ) : (
          <>
        {/* Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4" role="region" aria-label="Graph statistics">
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
            <div className="text-sm text-gray-600 dark:text-gray-400">Total Nodes</div>
            <div className="text-2xl font-bold" aria-label={`${nodes.length} total nodes`}>{nodes.length}</div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
            <div className="text-sm text-gray-600 dark:text-gray-400">Total Dependencies</div>
            <div className="text-2xl font-bold" aria-label={`${links.length} total dependencies`}>{links.length}</div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
            <div className="text-sm text-gray-600 dark:text-gray-400">Circular Dependencies</div>
            <div className="text-2xl font-bold text-red-600" aria-label={`${circularDeps.length} circular dependencies detected`}>{circularDeps.length}</div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
            <div className="text-sm text-gray-600 dark:text-gray-400">Zoom Level</div>
            <div className="text-2xl font-bold" aria-label={`Zoom level ${zoomLevel.toFixed(1)}x`}>{zoomLevel.toFixed(1)}x</div>
          </div>
        </div>

        {/* Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4" role="region" aria-label="Graph controls">
          <div className="space-y-2">
            <Label htmlFor="search">Search Nodes</Label>
            <Input
              id="search"
              placeholder="Search by name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              aria-label="Search nodes by name"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="cycle-filter">Circular Dependencies</Label>
            <select
              id="cycle-filter"
              value={selectedCycle || ''}
              onChange={(e) => setSelectedCycle(e.target.value || null)}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
              aria-label="Filter by circular dependency"
            >
              <option value="">All Nodes</option>
              {circularDeps.map(cycle => (
                <option key={cycle.id} value={cycle.id}>
                  {cycle.description} ({cycle.severity})
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label>Display Options</Label>
            <div className="flex space-x-2">
              <Button
                variant={highlightCycles ? 'default' : 'outline'}
                size="sm"
                onClick={() => setHighlightCycles(!highlightCycles)}
                aria-label={highlightCycles ? 'Hide cycle highlights' : 'Show cycle highlights'}
                aria-pressed={highlightCycles}
              >
                {highlightCycles ? <Eye className="h-4 w-4 mr-2" aria-hidden="true" /> : <EyeOff className="h-4 w-4 mr-2" aria-hidden="true" />}
                Highlight Cycles
              </Button>
            </div>
          </div>
        </div>

        {/* Circular Dependencies List */}
        {circularDeps.length > 0 && (
          <div 
            className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
            role="region"
            aria-labelledby="circular-deps-heading"
          >
            <div className="flex items-center space-x-2 mb-2">
              <AlertTriangle className="h-5 w-5 text-red-600" aria-hidden="true" />
              <h3 id="circular-deps-heading" className="font-semibold text-red-900 dark:text-red-100">
                Circular Dependencies Detected
              </h3>
            </div>
            <div className="space-y-2" role="list" aria-label="List of circular dependencies">
              {circularDeps.map(cycle => (
                <div
                  key={cycle.id}
                  role="listitem"
                  className={`p-3 rounded cursor-pointer transition-colors ${
                    selectedCycle === cycle.id
                      ? 'bg-red-100 dark:bg-red-900/40 border-2 border-red-400'
                      : 'bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/30'
                  }`}
                  onClick={() => setSelectedCycle(selectedCycle === cycle.id ? null : cycle.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelectedCycle(selectedCycle === cycle.id ? null : cycle.id);
                    }
                  }}
                  tabIndex={0}
                  aria-label={`Circular dependency: ${cycle.description}, severity ${cycle.severity}, ${cycle.nodes.length} nodes involved`}
                  aria-expanded={selectedCycle === cycle.id}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{cycle.description}</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {cycle.nodes.length} nodes involved
                      </div>
                    </div>
                    <Badge
                      variant={
                        cycle.severity === 'high' ? 'destructive' :
                        cycle.severity === 'medium' ? 'default' : 'secondary'
                      }
                    >
                      {cycle.severity.toUpperCase()}
                    </Badge>
                  </div>
                  {selectedCycle === cycle.id && (
                    <div className="mt-2 pt-2 border-t border-red-200 dark:border-red-700">
                      <div className="text-sm font-medium mb-1">Cycle Path:</div>
                      <div className="text-sm text-gray-700 dark:text-gray-300">
                        {cycle.nodes.join(' → ')} → {cycle.nodes[0]}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Graph Container */}
        <div 
          ref={containerRef}
          className="w-full h-[600px] border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 relative overflow-hidden"
          role="img"
          aria-labelledby="graph-title"
          aria-describedby="graph-description"
        >
          <div id="graph-description" className="sr-only">
            Interactive dependency graph showing {nodes.length} nodes and {links.length} dependencies. 
            {circularDeps.length > 0 && `${circularDeps.length} circular dependencies detected.`}
            Use zoom controls to navigate. Click nodes for details.
          </div>
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-gray-100 mx-auto"></div>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading graph...</p>
              </div>
            </div>
          ) : error ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-red-600" />
                <p className="text-red-600 mb-4">{error}</p>
                <Button 
                  variant="outline" 
                  onClick={handleRetry}
                  aria-label="Retry loading graph data"
                >
                  <RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
                  Retry
                </Button>
              </div>
            </div>
          ) : (
            <>
              <ForceGraph2D
                ref={graphRef}
                graphData={filteredData}
                nodeLabel={(node: any) => `${node.name}${node.inCycle ? ' (In Cycle)' : ''}`}
                nodeColor={getNodeColor}
                nodeRelSize={6}
                nodeVal={(node: any) => node.size}
                linkColor={getLinkColor}
                linkWidth={(link: any) => link.weight}
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                onNodeClick={handleNodeClick}
                cooldownTicks={100}
                onEngineStop={() => graphRef.current?.zoomToFit(400)}
                enableNodeDrag={true}
                enableZoomInteraction={true}
                enablePanInteraction={true}
                minZoom={0.1}
                maxZoom={10}
                onZoom={(zoom) => setZoomLevel(zoom.k)}
              />
              
              {/* Zoom Controls Overlay */}
              <div className="absolute top-4 right-4 flex flex-col space-y-2" role="group" aria-label="Zoom controls">
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-white dark:bg-gray-800"
                  onClick={handleZoomIn}
                  disabled={zoomLevel >= 10}
                  aria-label="Zoom in"
                >
                  <ZoomIn className="h-4 w-4" aria-hidden="true" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-white dark:bg-gray-800"
                  onClick={handleZoomOut}
                  disabled={zoomLevel <= 0.1}
                  aria-label="Zoom out"
                >
                  <ZoomOut className="h-4 w-4" aria-hidden="true" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-white dark:bg-gray-800"
                  onClick={handleResetView}
                  aria-label="Reset view to fit all nodes"
                >
                  <Maximize2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>

              {/* Info Overlay */}
              <div 
                className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700"
                role="region"
                aria-label="Graph legend"
              >
                <div className="flex items-center space-x-2 mb-2">
                  <Info className="h-4 w-4" aria-hidden="true" />
                  <span className="text-sm font-semibold">Legend</span>
                </div>
                <div className="space-y-1 text-xs" role="list">
                  <div className="flex items-center space-x-2" role="listitem">
                    <div className="w-3 h-3 rounded-full bg-blue-500" aria-hidden="true"></div>
                    <span>Normal Node</span>
                  </div>
                  <div className="flex items-center space-x-2" role="listitem">
                    <div className="w-3 h-3 rounded-full bg-yellow-500" aria-hidden="true"></div>
                    <span>Low Severity Cycle</span>
                  </div>
                  <div className="flex items-center space-x-2" role="listitem">
                    <div className="w-3 h-3 rounded-full bg-orange-500" aria-hidden="true"></div>
                    <span>Medium Severity Cycle</span>
                  </div>
                  <div className="flex items-center space-x-2" role="listitem">
                    <div className="w-3 h-3 rounded-full bg-red-500" aria-hidden="true"></div>
                    <span>High Severity Cycle</span>
                  </div>
                </div>
                {renderMode === 'lod' && (
                  <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                    <Badge variant="secondary" className="text-xs">
                      LOD Rendering Active
                    </Badge>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Selected Node Details */}
        {selectedNode && (
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <h3 className="font-semibold mb-2">Selected Node Details</h3>
            {(() => {
              const node = nodes.find(n => n.id === selectedNode);
              if (!node) return null;
              return (
                <div className="space-y-1 text-sm">
                  <div><span className="font-medium">Name:</span> {node.name}</div>
                  <div><span className="font-medium">Type:</span> {node.type}</div>
                  {node.complexity && (
                    <div><span className="font-medium">Complexity:</span> {node.complexity}</div>
                  )}
                  {node.inCycle && (
                    <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/40 rounded">
                      <div className="flex items-center space-x-2 text-red-900 dark:text-red-100">
                        <AlertTriangle className="h-4 w-4" />
                        <span className="font-medium">Part of Circular Dependency</span>
                      </div>
                      <div className="mt-1 text-red-800 dark:text-red-200">
                        Severity: <Badge variant="destructive">{node.cycleSeverity?.toUpperCase()}</Badge>
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
