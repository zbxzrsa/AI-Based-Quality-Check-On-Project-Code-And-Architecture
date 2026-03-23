import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
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
  Filter, 
  Layers, 
  Database, 
  Code, 
  FileText,
  AlertTriangle,
  CheckCircle,
  Eye,
  EyeOff,
  Download,
  Upload,
  TrendingUp,
  TrendingDown,
  Loader2,
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
import { apiClientEnhanced } from '@/lib/api-client';
import { validateArchitectureAnalysis, type ArchitectureAnalysis } from '@/lib/validations/api-schemas';
import { ErrorHandler } from '@/lib/error-handler';
import { featureFlagsService } from '@/lib/feature-flags';

interface Node {
  id: string;
  name: string;
  type: 'file' | 'class' | 'function' | 'module' | 'layer' | 'repository' | 'service' | 'controller';
  size: number;
  complexity?: number;
  coupling?: number;
  isDrift?: boolean;
  layer?: string;
  group?: string;
  cluster?: number;
}

interface Link {
  source: string;
  target: string;
  type: 'import' | 'inheritance' | 'dependency' | 'call' | 'containment' | 'violates';
  weight: number;
  isDrift?: boolean;
}

interface Neo4jGraphVisualizationProps {
  analysisId?: string;
  className?: string;
}

/**
 * Fetch Neo4j architecture graph data from API
 * Validates Requirements: 1.4, 1.5, 2.7
 */
async function fetchNeo4jGraphData(analysisId: string): Promise<ArchitectureAnalysis> {
  try {
    // apiClientEnhanced.get<T>() returns Promise<T>, not Promise<{data: T}>
    const response = await apiClientEnhanced.get<ArchitectureAnalysis>(
      `/architecture/${analysisId}/neo4j`
    );

    // Validate response data
    const validatedData = validateArchitectureAnalysis(response);
    return validatedData;
  } catch (error) {
    // Handle and transform error
    const errorInfo = ErrorHandler.handleError(error);
    ErrorHandler.logError(errorInfo);
    throw error;
  }
}

/**
 * Transform API data to Neo4j graph component format
 * Validates Requirements: 4.1, 4.2
 */
function transformNeo4jGraphData(data: ArchitectureAnalysis): { nodes: Node[]; links: Link[] } {
  // Transform nodes from API format to component format
  const nodes: Node[] = data.nodes.map(node => {
    const complexity = node.complexity || 5;
    const isDrift = node.health === 'drift' || node.health === 'unhealthy';
    
    return {
      id: node.id,
      name: node.label,
      type: node.type as Node['type'],
      size: 50, // Default size
      complexity,
      coupling: node.metrics?.coupling,
      isDrift,
      layer: node.properties?.layer as string | undefined,
      group: node.type,
      cluster: node.properties?.cluster as number | undefined,
    };
  });

  // Transform edges from API format to component format
  const links: Link[] = data.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    type: edge.type as Link['type'],
    weight: edge.is_circular ? 2 : 1,
    isDrift: edge.is_circular || edge.type === 'violates',
  }));

  return { nodes, links };
}

export default function Neo4jGraphVisualization({ analysisId, className }: Neo4jGraphVisualizationProps) {
  // Check feature flag status - Validates Requirements: 10.2, 10.8
  const isFeatureEnabled = featureFlagsService.isEnabled('neo4j-graph-production');
  
  // Use TanStack Query for data fetching with caching and retry logic
  // Validates Requirements: 1.4, 1.5, 4.8
  const {
    data: architectureData,
    isLoading,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: ['neo4jGraph', analysisId],
    queryFn: () => fetchNeo4jGraphData(analysisId!),
    enabled: !!analysisId && isFeatureEnabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Transform API data to component format
  const { nodes: apiNodes, links: apiLinks } = useMemo(() => {
    if (!architectureData) {
      return { nodes: [], links: [] };
    }
    return transformNeo4jGraphData(architectureData);
  }, [architectureData]);

  const [nodes, setNodes] = useState<Node[]>([]);
  const [links, setLinks] = useState<Link[]>([]);
  const [filters, setFilters] = useState({
    showFiles: true,
    showClasses: true,
    showFunctions: true,
    showModules: true,
    showLayers: true,
    showDrift: true,
    minComplexity: 0,
    maxComplexity: 20,
    showDriftOnly: false
  });
  const [viewMode, setViewMode] = useState<'all' | 'drift' | 'complexity' | 'layers' | 'clusters'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const forceGraphRef = useRef<any>(null);
  const [graphStats, setGraphStats] = useState({
    clusteringCoefficient: 0,
    averagePathLength: 0,
    modularity: 0,
    couplingScore: 0
  });
  
  const graphRef = useRef<HTMLDivElement>(null);

  // Update local state when API data changes
  useEffect(() => {
    if (apiNodes.length > 0) {
      setNodes(apiNodes);
      setLinks(apiLinks);
      setGraphData({ nodes: apiNodes, links: apiLinks });
      calculateGraphStats(apiNodes, apiLinks);
    }
  }, [apiNodes, apiLinks]);

  const calculateGraphStats = (nodes: Node[], links: Link[]) => {
    // Calculate clustering coefficient
    const clusteringCoefficient = calculateClusteringCoefficient(nodes, links);
    
    // Calculate average path length
    const averagePathLength = calculateAveragePathLength(nodes, links);
    
    // Calculate modularity (simplified)
    const modularity = calculateModularity(nodes, links);
    
    // Calculate coupling score
    const couplingScore = calculateCouplingScore(nodes, links);

    setGraphStats({
      clusteringCoefficient,
      averagePathLength,
      modularity,
      couplingScore
    });
  };

  const calculateClusteringCoefficient = (nodes: Node[], links: Link[]): number => {
    // Simplified clustering coefficient calculation
    const nodeLinks: { [key: string]: string[] } = {};
    
    links.forEach(link => {
      if (!nodeLinks[link.source]) nodeLinks[link.source] = [];
      if (!nodeLinks[link.target]) nodeLinks[link.target] = [];
      
      nodeLinks[link.source].push(link.target);
      nodeLinks[link.target].push(link.source);
    });

    let totalCoefficient = 0;
    let nodeCount = 0;

    nodes.forEach(node => {
      const neighbors = nodeLinks[node.id] || [];
      if (neighbors.length < 2) return;

      let connections = 0;
      for (let i = 0; i < neighbors.length; i++) {
        for (let j = i + 1; j < neighbors.length; j++) {
          if (links.some(l => 
            (l.source === neighbors[i] && l.target === neighbors[j]) ||
            (l.source === neighbors[j] && l.target === neighbors[i])
          )) {
            connections++;
          }
        }
      }

      const maxConnections = (neighbors.length * (neighbors.length - 1)) / 2;
      const coefficient = maxConnections > 0 ? connections / maxConnections : 0;
      totalCoefficient += coefficient;
      nodeCount++;
    });

    return nodeCount > 0 ? totalCoefficient / nodeCount : 0;
  };

  const calculateAveragePathLength = (nodes: Node[], links: Link[]): number => {
    // Simplified average path length calculation
    // In a real implementation, this would use Dijkstra's algorithm
    const totalPaths = links.length;
    const totalDistance = links.reduce((sum, link) => sum + (link.weight || 1), 0);
    
    return totalPaths > 0 ? totalDistance / totalPaths : 0;
  };

  const calculateModularity = (nodes: Node[], links: Link[]): number => {
    // Simplified modularity calculation
    const layerGroups = new Map<string, Node[]>();
    
    nodes.forEach(node => {
      if (node.layer) {
        if (!layerGroups.has(node.layer)) {
          layerGroups.set(node.layer, []);
        }
        layerGroups.get(node.layer)!.push(node);
      }
    });

    let modularity = 0;
    const totalLinks = links.length;

    layerGroups.forEach((groupNodes, layer) => {
      const groupNodeIds = new Set(groupNodes.map(n => n.id));
      const internalLinks = links.filter(l => 
        groupNodeIds.has(l.source) && groupNodeIds.has(l.target)
      ).length;
      
      const groupSize = groupNodes.length;
      const expectedLinks = (groupSize * (groupSize - 1)) / 2;
      
      if (expectedLinks > 0) {
        modularity += (internalLinks / totalLinks) - Math.pow(groupSize / nodes.length, 2);
      }
    });

    return modularity;
  };

  const calculateCouplingScore = (nodes: Node[], links: Link[]): number => {
    // Calculate coupling based on cross-layer dependencies
    let crossLayerLinks = 0;
    let totalLinks = links.length;

    links.forEach(link => {
      const sourceNode = nodes.find(n => n.id === link.source);
      const targetNode = nodes.find(n => n.id === link.target);
      
      if (sourceNode && targetNode && sourceNode.layer && targetNode.layer && sourceNode.layer !== targetNode.layer) {
        crossLayerLinks++;
      }
    });

    return totalLinks > 0 ? (crossLayerLinks / totalLinks) * 100 : 0;
  };

  const filteredNodes = nodes.filter(node => {
    // Filter by type
    if (node.type === 'file' && !filters.showFiles) return false;
    if (node.type === 'class' && !filters.showClasses) return false;
    if (node.type === 'function' && !filters.showFunctions) return false;
    if (node.type === 'module' && !filters.showModules) return false;
    if (node.type === 'layer' && !filters.showLayers) return false;
    
    // Filter by complexity
    if (node.complexity && (node.complexity < filters.minComplexity || node.complexity > filters.maxComplexity)) {
      return false;
    }
    
    // Filter by drift
    if (!filters.showDrift && node.isDrift) return false;
    
    // Filter by search term
    if (searchTerm && !node.name.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    
    // Filter by view mode
    if (viewMode === 'drift' && !node.isDrift) return false;
    if (viewMode === 'complexity' && (!node.complexity || node.complexity < 10)) return false;
    if (viewMode === 'layers' && node.type !== 'layer') return false;
    if (viewMode === 'clusters' && !node.cluster) return false;
    
    // Show drift only mode
    if (filters.showDriftOnly && !node.isDrift) return false;
    
    return true;
  });

  const filteredLinks = links.filter(link => {
    const sourceNode = nodes.find(n => n.id === link.source);
    const targetNode = nodes.find(n => n.id === link.target);
    
    return sourceNode && targetNode && 
           filteredNodes.includes(sourceNode) && 
           filteredNodes.includes(targetNode);
  });

  const getNodeTypeColor = (node: Node) => {
    if (node.isDrift) return '#ef4444'; // Red for drift nodes
    
    switch (node.type) {
      case 'layer': return '#3b82f6'; // Blue
      case 'module': return '#22c55e'; // Green
      case 'file': return '#f59e0b'; // Orange
      case 'class': return '#8b5cf6'; // Purple
      case 'function': return '#06b6d4'; // Cyan
      case 'controller': return '#ef4444'; // Red
      case 'service': return '#10b981'; // Green
      case 'repository': return '#f59e0b'; // Orange
      default: return '#6b7280'; // Gray
    }
  };

  const getNodeTypeIcon = (type: string) => {
    switch (type) {
      case 'layer': return '🏗️';
      case 'module': return '📦';
      case 'file': return '📄';
      case 'class': return '🏗️';
      case 'function': return '⚙️';
      case 'controller': return '🎛️';
      case 'service': return '🔧';
      case 'repository': return '🗄️';
      default: return '❓';
    }
  };

  const getNodeSize = (node: Node) => {
    switch (node.type) {
      case 'layer': return node.size * 2.5;
      case 'module': return node.size * 2;
      case 'file': return node.size;
      case 'class': return node.size * 0.8;
      case 'function': return node.size * 0.5;
      default: return node.size;
    }
  };

  const getLinkColor = (link: Link) => {
    if (link.isDrift) return '#ef4444'; // Red for drift
    if (link.type === 'violates') return '#ef4444'; // Red for violations
    if (link.type === 'import') return '#ef4444'; // Red
    if (link.type === 'inheritance') return '#3b82f6'; // Blue
    if (link.type === 'dependency') return '#10b981'; // Green
    if (link.type === 'call') return '#f59e0b'; // Orange
    if (link.type === 'containment') return '#6b7280'; // Gray
    return '#6b7280'; // Gray
  };

  const getDriftSeverity = (node: Node) => {
    if (!node.isDrift) return 'none';
    if (node.complexity && node.complexity > 15) return 'high';
    if (node.complexity && node.complexity > 10) return 'medium';
    return 'low';
  };

  const handleNodeClick = (node: any) => {
    setSelectedNode(selectedNode === node.id ? null : node.id);
  };

  const exportGraphData = () => {
    const dataStr = JSON.stringify({ nodes, links }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'neo4j-architecture-graph.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  const importGraphData = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e: ProgressEvent<FileReader>) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        if (data.nodes && data.links) {
          setGraphData(data);
          setNodes(data.nodes);
          setLinks(data.links);
          calculateGraphStats(data.nodes, data.links);
        }
      } catch (err) {
        console.error('Failed to parse imported graph data:', err);
      }
    };
    reader.readAsText(file);
  };

  const resetView = () => {
    if (forceGraphRef.current) {
      forceGraphRef.current.zoomToFit(800);
    }
  };

  const applyForceLayout = () => {
    if (forceGraphRef.current) {
      forceGraphRef.current.d3Force('link').distance(100);
      forceGraphRef.current.d3Force('charge').strength(-300);
      forceGraphRef.current.d3Force('center').strength(0.1);
    }
  };

  const getRiskLevel = (score: number) => {
    if (score > 70) return { level: 'HIGH', color: '#ef4444' };
    if (score > 40) return { level: 'MEDIUM', color: '#f59e0b' };
    return { level: 'LOW', color: '#10b981' };
  };

  // Handle retry for failed requests
  const handleRetry = () => {
    refetch();
  };

  // Get error message
  const errorMessage = useMemo(() => {
    if (!queryError) return null;
    const errorInfo = ErrorHandler.handleError(queryError);
    return errorInfo.userMessage;
  }, [queryError]);

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Database className="h-5 w-5" />
            <CardTitle>Neo4j Architecture Graph Visualization</CardTitle>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={handleRetry} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={exportGraphData} disabled={isLoading || !graphData}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
            <label className="flex items-center space-x-2 cursor-pointer">
              <Upload className="h-4 w-4" />
              <span className="text-sm">Import</span>
              <Input
                type="file"
                accept=".json"
                onChange={importGraphData}
                className="hidden"
                disabled={isLoading}
              />
            </label>
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
                The Neo4j Graph visualization is currently disabled. This feature is being progressively rolled out.
              </p>
              <p className="text-sm text-gray-500">
                Please contact your administrator if you need access to this feature.
              </p>
            </div>
          </div>
        ) : (
          <>
        {/* Graph Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Clustering Coefficient</div>
                <div className="text-2xl font-bold">{graphStats.clusteringCoefficient.toFixed(3)}</div>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-500" />
            </div>
            <div className="text-xs text-gray-500 mt-1">Network clustering measure</div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Average Path Length</div>
                <div className="text-2xl font-bold">{graphStats.averagePathLength.toFixed(2)}</div>
              </div>
              <TrendingDown className="h-8 w-8 text-green-500" />
            </div>
            <div className="text-xs text-gray-500 mt-1">Network connectivity</div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Modularity Score</div>
                <div className="text-2xl font-bold">{graphStats.modularity.toFixed(3)}</div>
              </div>
              <Layers className="h-8 w-8 text-purple-500" />
            </div>
            <div className="text-xs text-gray-500 mt-1">Module separation quality</div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Coupling Score</div>
                <div className="text-2xl font-bold" style={{ color: getRiskLevel(graphStats.couplingScore).color }}>
                  {graphStats.couplingScore.toFixed(1)}%
                </div>
              </div>
              <AlertTriangle className="h-8 w-8" style={{ color: getRiskLevel(graphStats.couplingScore).color }} />
            </div>
            <div className="text-xs text-gray-500 mt-1">Cross-layer dependencies</div>
          </div>
        </div>

        {/* Controls */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          {/* Search */}
          <div className="space-y-2">
            <Label htmlFor="search">Search Components</Label>
            <div className="flex space-x-2">
              <Input
                id="search"
                placeholder="Search by name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <Button variant="outline" size="sm">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* View Modes */}
          <div className="space-y-2">
            <Label>View Mode</Label>
            <div className="flex space-x-2">
              <Button 
                variant={viewMode === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('all')}
              >
                All
              </Button>
              <Button 
                variant={viewMode === 'drift' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('drift')}
                className="flex items-center space-x-1"
              >
                <AlertTriangle className="h-4 w-4" />
                <span>Drift</span>
              </Button>
              <Button 
                variant={viewMode === 'complexity' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('complexity')}
                className="flex items-center space-x-1"
              >
                <Eye className="h-4 w-4" />
                <span>Complex</span>
              </Button>
              <Button 
                variant={viewMode === 'layers' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('layers')}
                className="flex items-center space-x-1"
              >
                <Layers className="h-4 w-4" />
                <span>Layers</span>
              </Button>
              <Button 
                variant={viewMode === 'clusters' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('clusters')}
                className="flex items-center space-x-1"
              >
                <Database className="h-4 w-4" />
                <span>Clusters</span>
              </Button>
            </div>
          </div>

          {/* Filters */}
          <div className="space-y-2">
            <Label>Filters</Label>
            <div className="flex space-x-2">
              <Button 
                variant={filters.showLayers ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({...filters, showLayers: !filters.showLayers})}
                className="flex items-center space-x-1"
              >
                <span>🏗️</span>
                <span>Layers</span>
              </Button>
              <Button 
                variant={filters.showModules ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({...filters, showModules: !filters.showModules})}
                className="flex items-center space-x-1"
              >
                <span>📦</span>
                <span>Modules</span>
              </Button>
              <Button 
                variant={filters.showFiles ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({...filters, showFiles: !filters.showFiles})}
                className="flex items-center space-x-1"
              >
                <span>📄</span>
                <span>Files</span>
              </Button>
              <Button 
                variant={filters.showClasses ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({...filters, showClasses: !filters.showClasses})}
                className="flex items-center space-x-1"
              >
                <span>🏗️</span>
                <span>Classes</span>
              </Button>
              <Button 
                variant={filters.showFunctions ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({...filters, showFunctions: !filters.showFunctions})}
                className="flex items-center space-x-1"
              >
                <span>⚙️</span>
                <span>Functions</span>
              </Button>
            </div>
            <div className="flex items-center space-x-2 mt-2">
              <Button 
                variant={filters.showDriftOnly ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({...filters, showDriftOnly: !filters.showDriftOnly})}
                className="flex items-center space-x-1"
              >
                <AlertTriangle className="h-4 w-4" />
                <span>Drift Only</span>
              </Button>
            </div>
          </div>

          {/* Complexity Range */}
          <div className="space-y-2">
            <Label>Complexity Range: {filters.minComplexity} - {filters.maxComplexity}</Label>
            <div className="flex space-x-2">
              <Input
                type="range"
                min="0"
                max="20"
                value={filters.minComplexity}
                onChange={(e) => setFilters({...filters, minComplexity: parseInt(e.target.value)})}
                className="flex-1"
              />
              <Input
                type="range"
                min="0"
                max="20"
                value={filters.maxComplexity}
                onChange={(e) => setFilters({...filters, maxComplexity: parseInt(e.target.value)})}
                className="flex-1"
              />
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          {/* Node Types Legend */}
          <div className="space-y-2">
            <Label>Node Types</Label>
            <div className="grid grid-cols-2 gap-2">
              {['layer', 'module', 'file', 'class', 'function', 'controller', 'service', 'repository'].map(type => (
                <div key={type} className="flex items-center space-x-2 p-2 bg-gray-50 rounded">
                  <span>{getNodeTypeIcon(type)}</span>
                  <span className="text-sm capitalize">{type}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Drift Legend */}
          <div className="space-y-2">
            <Label>Architectural Drift</Label>
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-sm">No Drift</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <span className="text-sm">Low Risk Drift</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                <span className="text-sm">Medium Risk Drift</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span className="text-sm">High Risk Drift</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                <span className="text-sm">Layer Violation</span>
              </div>
            </div>
          </div>

          {/* Link Types Legend */}
          <div className="space-y-2">
            <Label>Dependencies</Label>
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-sm">Normal Dependency</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                <span className="text-sm">Inheritance</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                <span className="text-sm">Function Call</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span className="text-sm">Cross-Layer Import</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                <span className="text-sm">Layer Violation</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
                <span className="text-sm">Containment</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <Label>Actions</Label>
            <div className="flex space-x-2">
              <Button variant="outline" size="sm" onClick={resetView}>
                <ZoomOut className="h-4 w-4 mr-2" />
                Reset View
              </Button>
              <Button variant="outline" size="sm" onClick={applyForceLayout}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Re-layout
              </Button>
            </div>
          </div>
        </div>

        {/* Graph Container */}
        <div 
          ref={graphRef}
          className="w-full h-[600px] border border-gray-200 rounded-lg bg-white relative"
        >
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90">
              <div className="text-center">
                <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-900">Loading Neo4j graph...</p>
                <p className="text-sm text-gray-600 mt-2">Fetching architecture data from server</p>
              </div>
            </div>
          ) : queryError ? (
            <div className="absolute inset-0 flex items-center justify-center bg-white">
              <div className="text-center max-w-md px-4">
                <AlertTriangle className="h-12 w-12 text-red-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Failed to Load Graph Data</h3>
                <p className="text-sm text-gray-600 mb-4">{errorMessage}</p>
                <div className="flex justify-center space-x-3">
                  <Button onClick={handleRetry} variant="default">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                  </Button>
                  <Button onClick={() => window.location.reload()} variant="outline">
                    Reload Page
                  </Button>
                </div>
              </div>
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center bg-white">
              <div className="text-center">
                <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No graph data available</p>
                <p className="text-sm text-gray-500 mt-2">Try adjusting your filters or refresh the data</p>
              </div>
            </div>
          ) : (
            <ForceGraph2D
              ref={forceGraphRef}
              graphData={{ nodes: filteredNodes, links: filteredLinks }}
              nodeLabel="name"
              nodeColor={getNodeTypeColor}
              nodeVal={(node: any) => getNodeSize(node)}
              linkColor={getLinkColor}
              linkWidth={(link: any) => (link.weight || 1) * 2}
              linkDirectionalArrowLength={6}
              linkDirectionalArrowRelPos={1}
              onNodeClick={handleNodeClick}
              width={graphRef.current?.clientWidth || 800}
              height={graphRef.current?.clientHeight || 600}
              cooldownTicks={100}
            />
          )}
        </div>

        {/* Statistics Overlay */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-semibold mb-2">Total Nodes</h4>
            <p className="text-2xl font-bold">{filteredNodes.length}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-semibold mb-2">Total Links</h4>
            <p className="text-2xl font-bold">{filteredLinks.length}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-semibold mb-2">Drift Nodes</h4>
            <p className="text-2xl font-bold text-red-600">{filteredNodes.filter(n => n.isDrift).length}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-semibold mb-2">High Complexity</h4>
            <p className="text-2xl font-bold text-orange-600">{filteredNodes.filter(n => n.complexity && n.complexity > 10).length}</p>
          </div>
        </div>

        {/* Selected Node Details */}
        {selectedNode && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-semibold mb-2">Selected Component</h3>
            {(() => {
              const node = filteredNodes.find(n => n.id === selectedNode);
              if (!node) return null;
              
              return (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Name</span>
                    <div className="font-medium">{node.name}</div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Type</span>
                    <div className="font-medium capitalize">{node.type}</div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Layer</span>
                    <div className="font-medium">{node.layer || 'Unknown'}</div>
                  </div>
                  {node.complexity && (
                    <div>
                      <span className="text-sm text-gray-600">Complexity</span>
                      <div className="font-medium">{node.complexity}</div>
                    </div>
                  )}
                  <div>
                    <span className="text-sm text-gray-600">Architectural Drift</span>
                    <div className={`font-medium ${node.isDrift ? 'text-red-600' : 'text-green-600'}`}>
                      {node.isDrift ? 'Yes' : 'No'}
                    </div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Drift Severity</span>
                    <div className="font-medium">
                      <Badge variant={getDriftSeverity(node) === 'high' ? 'destructive' : getDriftSeverity(node) === 'medium' ? 'default' : 'secondary'}>
                        {getDriftSeverity(node)}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Cluster</span>
                    <div className="font-medium">{node.cluster || 'N/A'}</div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Node Size</span>
                    <div className="font-medium">{getNodeSize(node)}</div>
                  </div>
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
