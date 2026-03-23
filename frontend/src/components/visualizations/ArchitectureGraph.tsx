import { useState, useRef, useMemo } from 'react';
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
  AlertTriangle,
  Eye,
  Download,
  Loader2,
  Lock
} from 'lucide-react';
import { apiClientEnhanced } from '@/lib/api-client';
import { validateArchitectureAnalysis, type ArchitectureAnalysis } from '@/lib/validations/api-schemas';
import { ErrorHandler } from '@/lib/error-handler';
import { featureFlagsService } from '@/lib/feature-flags';

interface Node {
  id: string;
  name: string;
  type: 'file' | 'class' | 'function' | 'module' | 'layer';
  size: number;
  complexity?: number;
  coupling?: number;
  isDrift?: boolean;
  layer?: string;
  group?: string;
  position?: { x: number; y: number };
}

interface Link {
  source: string;
  target: string;
  type: 'import' | 'inheritance' | 'dependency' | 'call' | 'containment';
  weight: number;
}

interface ArchitectureGraphProps {
  analysisId: string;
  className?: string;
}

/**
 * Fetch architecture analysis data from API
 * Validates Requirements: 1.4, 1.5, 2.7
 */
async function fetchArchitectureData(analysisId: string): Promise<ArchitectureAnalysis> {
  try {
    // apiClientEnhanced.get<T>() returns Promise<T>, not Promise<{data: T}>
    const response = await apiClientEnhanced.get<ArchitectureAnalysis>(
      `/architecture/${analysisId}`
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
 * Transform API data to component format
 * Validates Requirements: 4.1, 4.2
 */
function transformArchitectureData(data: ArchitectureAnalysis): { nodes: Node[]; links: Link[] } {
  // Transform nodes from API format to component format
  const nodes: Node[] = data.nodes.map(node => ({
    id: node.id,
    name: node.label,
    type: node.type as Node['type'],
    size: 50, // Default size
    complexity: node.complexity,
    isDrift: node.health === 'drift' || node.health === 'unhealthy',
    layer: node.properties?.layer as string | undefined,
    group: node.type,
    position: node.position as { x: number; y: number } | undefined,
  }));

  // Transform edges from API format to component format
  const links: Link[] = data.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    type: edge.type as Link['type'],
    weight: edge.is_circular ? 2 : 1,
  }));

  return { nodes, links };
}

export default function ArchitectureGraph({ analysisId, className }: ArchitectureGraphProps) {
  // Check feature flag status
  // Validates Requirements: 10.2, 10.8
  const isFeatureEnabled = featureFlagsService.isEnabled('architecture-graph-production');
  
  // Use TanStack Query for data fetching with caching and retry logic
  // Validates Requirements: 1.4, 1.5, 4.8
  const {
    data: architectureData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['architecture', analysisId],
    queryFn: () => fetchArchitectureData(analysisId),
    enabled: !!analysisId && isFeatureEnabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Transform API data to component format
  const { nodes, links } = useMemo(() => {
    if (!architectureData) {
      return { nodes: [], links: [] };
    }
    return transformArchitectureData(architectureData);
  }, [architectureData]);

  const [filters, setFilters] = useState({
    showFiles: true,
    showClasses: true,
    showFunctions: true,
    showModules: true,
    showLayers: true,
    showDrift: true,
    minComplexity: 0,
    maxComplexity: 20
  });
  const [viewMode, setViewMode] = useState<'all' | 'drift' | 'complexity' | 'layers'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  
  const graphRef = useRef<HTMLDivElement>(null);

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
    link.download = 'architecture-graph.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  const resetView = () => {
    // Placeholder for reset view functionality
    console.log('Reset view');
  };

  const applyForceLayout = () => {
    // Placeholder for force layout functionality
    console.log('Apply force layout');
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="h-5 w-5" />
            <CardTitle>Architecture Graph Visualization</CardTitle>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={exportGraphData}>
              <Download className="h-4 w-4 mr-2" />
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
                The Architecture Graph visualization is currently disabled. This feature is being progressively rolled out.
              </p>
              <p className="text-sm text-gray-500">
                Please contact your administrator if you need access to this feature.
              </p>
            </div>
          </div>
        ) : (
          <>
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
              {['layer', 'module', 'file', 'class', 'function'].map(type => (
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
            <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
              <div className="text-center">
                <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-700">Loading architecture graph...</p>
                <p className="mt-2 text-sm text-gray-500">Fetching data from server</p>
              </div>
            </div>
          ) : error ? (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
              <div className="text-center max-w-md px-4">
                <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-red-600" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Failed to Load Architecture Graph</h3>
                <p className="text-sm text-gray-600 mb-4">
                  {ErrorHandler.getUserMessage(ErrorHandler.handleError(error))}
                </p>
                <Button onClick={() => refetch()} variant="default">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
              </div>
            </div>
          ) : (
            <div className="w-full h-full relative">
              {/* Simple SVG-based graph visualization placeholder */}
              <svg className="w-full h-full">
                {/* Links */}
                {filteredLinks.map((link, index) => {
                  const sourceNode = filteredNodes.find(n => n.id === link.source);
                  const targetNode = filteredNodes.find(n => n.id === link.target);
                  
                  if (!sourceNode || !targetNode) return null;

                  // Use position from API data if available, otherwise use deterministic layout
                  const sourceIdx = filteredNodes.findIndex(n => n.id === link.source);
                  const targetIdx = filteredNodes.findIndex(n => n.id === link.target);
                  
                  // Get positions from API data or calculate deterministic positions
                  const sourcePos = nodes.find(n => n.id === link.source)?.position;
                  const targetPos = nodes.find(n => n.id === link.target)?.position;
                  
                  const x1 = sourcePos?.x ?? ((sourceIdx * 137) % 700) + 50;
                  const y1 = sourcePos?.y ?? ((sourceIdx * 211) % 500) + 50;
                  const x2 = targetPos?.x ?? ((targetIdx * 137) % 700) + 50;
                  const y2 = targetPos?.y ?? ((targetIdx * 211) % 500) + 50;

                  return (
                    <line
                      key={index}
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke={getLinkColor(link)}
                      strokeWidth={link.weight * 2}
                      opacity="0.6"
                    />
                  );
                })}

                {/* Nodes */}
                {filteredNodes.map((node, nodeIndex) => {
                  // Use position from API data if available, otherwise use deterministic layout
                  const apiNode = nodes.find(n => n.id === node.id);
                  const nodePos = apiNode?.position;
                  
                  const x = nodePos?.x ?? ((nodeIndex * 137) % 700) + 50;
                  const y = nodePos?.y ?? ((nodeIndex * 211) % 500) + 50;

                  return (
                    <g key={node.id} transform={`translate(${x}, ${y})`}>
                      {/* Drift indicator */}
                      {node.isDrift && (
                        <circle
                          r={getNodeSize(node) + 10}
                          fill="none"
                          stroke={getDriftSeverity(node) === 'high' ? '#ef4444' : getDriftSeverity(node) === 'medium' ? '#f59e0b' : '#eab308'}
                          strokeWidth="2"
                          opacity="0.8"
                          className="animate-pulse"
                        />
                      )}
                      
                      {/* Node */}
                      <circle
                        r={getNodeSize(node) / 10}
                        fill={getNodeTypeColor(node)}
                        opacity="0.8"
                        className="cursor-pointer hover:opacity-100 transition-opacity"
                        onClick={() => handleNodeClick({ id: node.id })}
                      />
                      
                      {/* Node label */}
                      <text
                        x="0"
                        y={getNodeSize(node) / 5}
                        textAnchor="middle"
                        fontSize="10"
                        fill="#333"
                        className="pointer-events-none"
                      >
                        {node.name}
                      </text>
                      
                      {/* Complexity indicator */}
                      {node.complexity && (
                        <text
                          x="0"
                          y={getNodeSize(node) / 2.5}
                          textAnchor="middle"
                          fontSize="8"
                          fill={node.complexity > 10 ? "#ef4444" : "#6b7280"}
                          className="pointer-events-none"
                        >
                          C:{node.complexity}
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>

              {/* Controls Overlay */}
              <div className="absolute top-2 right-2 flex space-x-2">
                <Button variant="outline" size="sm" className="bg-white">
                  <ZoomIn className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm" className="bg-white">
                  <ZoomOut className="h-4 w-4" />
                </Button>
              </div>

              {/* Statistics Overlay */}
              <div className="absolute bottom-2 left-2 bg-white p-2 rounded border">
                <div className="text-xs text-gray-600">
                  <div>Nodes: {filteredNodes.length}</div>
                  <div>Links: {filteredLinks.length}</div>
                  <div>Drift Nodes: {filteredNodes.filter(n => n.isDrift).length}</div>
                </div>
              </div>
            </div>
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
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
