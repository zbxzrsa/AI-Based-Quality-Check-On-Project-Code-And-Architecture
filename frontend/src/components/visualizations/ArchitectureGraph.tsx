import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
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
  Upload
} from 'lucide-react';
// import ForceGraph2D from 'react-force-graph-2d';

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
}

interface Link {
  source: string;
  target: string;
  type: 'import' | 'inheritance' | 'dependency' | 'call' | 'containment';
  weight: number;
}

interface ArchitectureGraphProps {
  analysisId?: string;
  className?: string;
}

export default function ArchitectureGraph({ analysisId, className }: ArchitectureGraphProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [links, setLinks] = useState<Link[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
  const [graphData, setGraphData] = useState<any>(null);
  const [forceGraphRef, setForceGraphRef] = useState<any>(null);
  
  const graphRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (analysisId) {
      loadGraphData();
    }
  }, [analysisId]);

  const loadGraphData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // In a real implementation, this would fetch from the backend
      // For now, we'll generate sample data
      const sampleData = generateSampleGraphData();
      setGraphData(sampleData);
      setNodes(sampleData.nodes);
      setLinks(sampleData.links);
    } catch (err) {
      setError('Failed to load architecture graph data');
      console.error('Error loading graph data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const generateSampleGraphData = () => {
    // Generate sample architecture graph data
    const nodes: Node[] = [];
    const links: Link[] = [];
    
    // Sample layers and modules
    const layers = ['UI', 'Service', 'Business', 'Data'];
    const modules = ['User', 'Auth', 'Product', 'Order', 'Payment'];
    const fileTypes = ['python', 'javascript', 'typescript'];
    
    // Create layer nodes
    layers.forEach((layer, index) => {
      nodes.push({
        id: `layer-${layer}`,
        name: layer,
        type: 'layer',
        size: 100,
        layer: layer,
        group: 'layers'
      });
    });

    // Create module nodes
    modules.forEach((module, index) => {
      const layer = layers[index % layers.length];
      nodes.push({
        id: `module-${module}`,
        name: module,
        type: 'module',
        size: 80,
        layer: layer,
        group: 'modules'
      });
      
      // Link module to layer
      links.push({
        source: `module-${module}`,
        target: `layer-${layer}`,
        type: 'dependency',
        weight: 1
      });
    });

    // Create file nodes with realistic names
    const files = [
      'components/App.tsx', 'components/Header.tsx', 'components/Footer.tsx',
      'services/api.ts', 'services/auth.ts', 'services/user.ts',
      'utils/helpers.ts', 'utils/validation.ts', 'utils/format.ts',
      'models/User.ts', 'models/Product.ts', 'models/Order.ts',
      'controllers/user.py', 'controllers/product.py', 'controllers/order.py',
      'database/models.py', 'database/queries.py', 'database/connection.py'
    ];

    files.forEach((file, index) => {
      const module = modules[index % modules.length];
      const layer = layers[index % layers.length];
      const fileType = fileTypes[index % fileTypes.length];
      const complexity = Math.floor(Math.random() * 15) + 1;
      const isDrift = Math.random() > 0.7; // 30% chance of drift
      
      nodes.push({
        id: `file-${file}`,
        name: file.split('/').pop() || file,
        type: 'file',
        size: 40,
        complexity: complexity,
        isDrift: isDrift,
        layer: layer,
        group: 'files'
      });
      
      // Link file to module
      links.push({
        source: `file-${file}`,
        target: `module-${module}`,
        type: 'dependency',
        weight: 1
      });
      
      // Link file to layer
      links.push({
        source: `file-${file}`,
        target: `layer-${layer}`,
        type: 'dependency',
        weight: 0.5
      });
    });

    // Create class nodes with realistic names
    const classes = [
      'App', 'Header', 'Footer', 'ApiService', 'AuthService', 'UserService',
      'User', 'Product', 'Order', 'Validator', 'Formatter', 'Database',
      'UserController', 'ProductController', 'OrderController',
      'UserModel', 'ProductModel', 'OrderModel'
    ];

    classes.forEach((className, index) => {
      const file = files[index % files.length];
      const complexity = Math.floor(Math.random() * 20) + 1;
      const isDrift = Math.random() > 0.8; // 20% chance of drift
      
      nodes.push({
        id: `class-${className}`,
        name: className,
        type: 'class',
        size: 60,
        complexity: complexity,
        isDrift: isDrift,
        layer: nodes.find(n => n.id === `file-${file}`)?.layer || 'Unknown',
        group: 'classes'
      });
      
      // Link class to file
      links.push({
        source: `class-${className}`,
        target: `file-${file}`,
        type: 'containment',
        weight: 2
      });
    });

    // Create function nodes with realistic names
    const functions = [
      'render', 'handleClick', 'fetchData', 'validateInput', 'formatDate',
      'saveToDB', 'getUser', 'createOrder', 'calculateTotal', 'sendEmail',
      'authenticate', 'authorize', 'encryptPassword', 'decryptPassword'
    ];

    functions.forEach((funcName, index) => {
      const className = classes[index % classes.length];
      const complexity = Math.floor(Math.random() * 10) + 1;
      
      nodes.push({
        id: `function-${funcName}`,
        name: funcName,
        type: 'function',
        size: 20,
        complexity: complexity,
        layer: nodes.find(n => n.id === `class-${className}`)?.layer || 'Unknown',
        group: 'functions'
      });
      
      // Link function to class
      links.push({
        source: `function-${funcName}`,
        target: `class-${className}`,
        type: 'containment',
        weight: 3
      });
    });

    // Add realistic cross-layer dependencies (drift)
    const driftLinks = [
      { source: 'file-components/Header.tsx', target: 'file-database/connection.py', type: 'import' },
      { source: 'class-App', target: 'file-services/database.py', type: 'dependency' },
      { source: 'function-render', target: 'class-Database', type: 'call' },
      { source: 'class-UserService', target: 'file-database/models.py', type: 'import' },
      { source: 'function-authenticate', target: 'file-database/queries.py', type: 'call' }
    ];

    driftLinks.forEach(link => {
      if (nodes.find(n => n.id === link.source) && nodes.find(n => n.id === link.target)) {
        links.push({
          source: link.source,
          target: link.target,
          type: link.type as Link['type'],
          weight: 2
        });
      }
    });

    return { nodes, links };
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
        }
      } catch (err) {
        setError('Failed to parse imported graph data');
      }
    };
    reader.readAsText(file);
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
            <Button variant="outline" size="sm" onClick={loadGraphData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={exportGraphData}>
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
              />
            </label>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
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
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
                <p className="mt-2 text-sm text-gray-600">Loading architecture graph...</p>
              </div>
            </div>
          ) : error ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-red-600">
                <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
                <p>{error}</p>
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

                  // Simple positioning for demo
                  const x1 = Math.random() * 700 + 50;
                  const y1 = Math.random() * 500 + 50;
                  const x2 = Math.random() * 700 + 50;
                  const y2 = Math.random() * 500 + 50;

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
                {filteredNodes.map((node, index) => {
                  // Simple positioning for demo
                  const x = Math.random() * 700 + 50;
                  const y = Math.random() * 500 + 50;

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
      </CardContent>
    </Card>
  );
}
