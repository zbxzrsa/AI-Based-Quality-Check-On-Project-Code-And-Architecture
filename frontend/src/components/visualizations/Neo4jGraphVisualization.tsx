import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  TrendingDown
} from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';

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

export default function Neo4jGraphVisualization({ analysisId, className }: Neo4jGraphVisualizationProps) {
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
    maxComplexity: 20,
    showDriftOnly: false
  });
  const [viewMode, setViewMode] = useState<'all' | 'drift' | 'complexity' | 'layers' | 'clusters'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [forceGraphRef, setForceGraphRef] = useState<any>(null);
  const [graphStats, setGraphStats] = useState({
    clusteringCoefficient: 0,
    averagePathLength: 0,
    modularity: 0,
    couplingScore: 0
  });
  
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
      // For now, we'll generate sample data with realistic architecture
      const sampleData = generateSampleNeo4jGraphData();
      setGraphData(sampleData);
      setNodes(sampleData.nodes);
      setLinks(sampleData.links);
      
      // Calculate graph statistics
      calculateGraphStats(sampleData.nodes, sampleData.links);
    } catch (err) {
      setError('Failed to load architecture graph data');
      console.error('Error loading graph data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const generateSampleNeo4jGraphData = () => {
    // Generate sample architecture graph data with realistic patterns
    const nodes: Node[] = [];
    const links: Link[] = [];
    
    // Sample layers and modules for a typical web application
    const layers = ['Controller', 'Service', 'Repository', 'Database', 'Domain'];
    const modules = ['User', 'Auth', 'Product', 'Order', 'Payment', 'Notification'];
    
    // Create layer nodes
    layers.forEach((layer, index) => {
      nodes.push({
        id: `layer-${layer}`,
        name: layer,
        type: 'layer',
        size: 100,
        layer: layer,
        group: 'layers',
        cluster: index
      });
    });

    // Create module nodes with realistic architecture
    modules.forEach((module, index) => {
      const layer = layers[index % layers.length];
      nodes.push({
        id: `module-${module}`,
        name: module,
        type: 'module',
        size: 80,
        layer: layer,
        group: 'modules',
        cluster: index + 5
      });
      
      // Link module to layer
      links.push({
        source: `module-${module}`,
        target: `layer-${layer}`,
        type: 'dependency',
        weight: 1
      });
    });

    // Create realistic file structure
    const fileStructure = [
      // Controller layer files
      { path: 'controllers/user.py', layer: 'Controller', module: 'User', type: 'file' },
      { path: 'controllers/auth.py', layer: 'Controller', module: 'Auth', type: 'file' },
      { path: 'controllers/product.py', layer: 'Controller', module: 'Product', type: 'file' },
      { path: 'controllers/order.py', layer: 'Controller', module: 'Order', type: 'file' },
      
      // Service layer files
      { path: 'services/user_service.py', layer: 'Service', module: 'User', type: 'file' },
      { path: 'services/auth_service.py', layer: 'Service', module: 'Auth', type: 'file' },
      { path: 'services/product_service.py', layer: 'Service', module: 'Product', type: 'file' },
      { path: 'services/order_service.py', layer: 'Service', module: 'Order', type: 'file' },
      
      // Repository layer files
      { path: 'repositories/user_repo.py', layer: 'Repository', module: 'User', type: 'file' },
      { path: 'repositories/product_repo.py', layer: 'Repository', module: 'Product', type: 'file' },
      { path: 'repositories/order_repo.py', layer: 'Repository', module: 'Order', type: 'file' },
      
      // Domain models
      { path: 'models/user.py', layer: 'Domain', module: 'User', type: 'file' },
      { path: 'models/product.py', layer: 'Domain', module: 'Product', type: 'file' },
      { path: 'models/order.py', layer: 'Domain', module: 'Order', type: 'file' },
      { path: 'models/payment.py', layer: 'Domain', module: 'Payment', type: 'file' }
    ];

    fileStructure.forEach((file, index) => {
      const complexity = Math.floor(Math.random() * 15) + 1;
      const isDrift = Math.random() > 0.85; // 15% chance of drift
      
      nodes.push({
        id: `file-${file.path}`,
        name: file.path.split('/').pop() || file.path,
        type: 'file',
        size: 40,
        complexity: complexity,
        isDrift: isDrift,
        layer: file.layer,
        group: 'files',
        cluster: layers.indexOf(file.layer) + 10
      });
      
      // Link file to module
      links.push({
        source: `file-${file.path}`,
        target: `module-${file.module}`,
        type: 'dependency',
        weight: 1
      });
      
      // Link file to layer
      links.push({
        source: `file-${file.path}`,
        target: `layer-${file.layer}`,
        type: 'dependency',
        weight: 0.5
      });
    });

    // Create class nodes with realistic names
    const classes = [
      // Controllers
      { name: 'UserController', layer: 'Controller', module: 'User', complexity: 8 },
      { name: 'AuthController', layer: 'Controller', module: 'Auth', complexity: 6 },
      { name: 'ProductController', layer: 'Controller', module: 'Product', complexity: 7 },
      { name: 'OrderController', layer: 'Controller', module: 'Order', complexity: 9 },
      
      // Services
      { name: 'UserService', layer: 'Service', module: 'User', complexity: 12 },
      { name: 'AuthService', layer: 'Service', module: 'Auth', complexity: 10 },
      { name: 'ProductService', layer: 'Service', module: 'Product', complexity: 11 },
      { name: 'OrderService', layer: 'Service', module: 'Order', complexity: 14 },
      
      // Repositories
      { name: 'UserRepository', layer: 'Repository', module: 'User', complexity: 6 },
      { name: 'ProductRepository', layer: 'Repository', module: 'Product', complexity: 7 },
      { name: 'OrderRepository', layer: 'Repository', module: 'Order', complexity: 8 },
      
      // Models
      { name: 'User', layer: 'Domain', module: 'User', complexity: 4 },
      { name: 'Product', layer: 'Domain', module: 'Product', complexity: 5 },
      { name: 'Order', layer: 'Domain', module: 'Order', complexity: 6 },
      { name: 'Payment', layer: 'Domain', module: 'Payment', complexity: 5 }
    ];

    classes.forEach((cls, index) => {
      const file = fileStructure.find(f => f.module === cls.module && f.layer === cls.layer);
      const isDrift = Math.random() > 0.9; // 10% chance of drift
      
      nodes.push({
        id: `class-${cls.name}`,
        name: cls.name,
        type: 'class',
        size: 60,
        complexity: cls.complexity,
        isDrift: isDrift,
        layer: cls.layer,
        group: 'classes',
        cluster: layers.indexOf(cls.layer) + 15
      });
      
      // Link class to file
      if (file) {
        links.push({
          source: `class-${cls.name}`,
          target: `file-${file.path}`,
          type: 'containment',
          weight: 2
        });
      }
    });

    // Create function nodes
    const functions = [
      // Controller methods
      { name: 'get_user', layer: 'Controller', module: 'User', complexity: 3 },
      { name: 'create_user', layer: 'Controller', module: 'User', complexity: 4 },
      { name: 'login', layer: 'Controller', module: 'Auth', complexity: 5 },
      { name: 'get_product', layer: 'Controller', module: 'Product', complexity: 3 },
      { name: 'create_order', layer: 'Controller', module: 'Order', complexity: 6 },
      
      // Service methods
      { name: 'validate_user', layer: 'Service', module: 'User', complexity: 4 },
      { name: 'hash_password', layer: 'Service', module: 'Auth', complexity: 3 },
      { name: 'calculate_total', layer: 'Service', module: 'Order', complexity: 5 },
      { name: 'send_notification', layer: 'Service', module: 'Notification', complexity: 4 },
      
      // Repository methods
      { name: 'find_by_id', layer: 'Repository', module: 'User', complexity: 2 },
      { name: 'save', layer: 'Repository', module: 'User', complexity: 3 },
      { name: 'find_all', layer: 'Repository', module: 'Product', complexity: 2 }
    ];

    functions.forEach((func, index) => {
      const cls = classes.find(c => c.module === func.module && c.layer === func.layer);
      
      nodes.push({
        id: `function-${func.name}`,
        name: func.name,
        type: 'function',
        size: 20,
        complexity: func.complexity,
        layer: func.layer,
        group: 'functions',
        cluster: layers.indexOf(func.layer) + 20
      });
      
      // Link function to class
      if (cls) {
        links.push({
          source: `function-${func.name}`,
          target: `class-${cls.name}`,
          type: 'containment',
          weight: 3
        });
      }
    });

    // Add realistic cross-layer dependencies (drift)
    const driftLinks = [
      // Controller -> Repository (should go through Service)
      { source: 'class-UserController', target: 'class-UserRepository', type: 'violates', isDrift: true },
      { source: 'class-ProductController', target: 'class-ProductRepository', type: 'violates', isDrift: true },
      
      // Service -> Database (should go through Repository)
      { source: 'class-UserService', target: 'layer-Database', type: 'violates', isDrift: true },
      
      // Repository -> Service (circular dependency)
      { source: 'class-UserRepository', target: 'class-UserService', type: 'violates', isDrift: true },
      
      // Controller -> Domain (should go through Service)
      { source: 'class-OrderController', target: 'class-Order', type: 'violates', isDrift: true }
    ];

    driftLinks.forEach(link => {
      if (nodes.find(n => n.id === link.source) && nodes.find(n => n.id === link.target)) {
        links.push({
          source: link.source,
          target: link.target,
          type: link.type as Link['type'],
          weight: 2,
          isDrift: link.isDrift
        });
      }
    });

    return { nodes, links };
  };

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
        setError('Failed to parse imported graph data');
      }
    };
    reader.readAsText(file);
  };

  const resetView = () => {
    if (forceGraphRef) {
      forceGraphRef.zoomToFit(800);
    }
  };

  const applyForceLayout = () => {
    if (forceGraphRef) {
      forceGraphRef.d3Force('link').distance(100);
      forceGraphRef.d3Force('charge').strength(-300);
      forceGraphRef.d3Force('center').strength(0.1);
    }
  };

  const getRiskLevel = (score: number) => {
    if (score > 70) return { level: 'HIGH', color: '#ef4444' };
    if (score > 40) return { level: 'MEDIUM', color: '#f59e0b' };
    return { level: 'LOW', color: '#10b981' };
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Database className="h-5 w-5" />
            <CardTitle>Neo4j Architecture Graph Visualization</CardTitle>
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
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
                <p className="mt-2 text-sm text-gray-600">Loading Neo4j graph...</p>
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
            <ForceGraph2D
              ref={setForceGraphRef}
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
              d3Force="charge"
              d3ChargeStrength={-300}
              d3LinkDistance={100}
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
      </CardContent>
    </Card>
  );
}
