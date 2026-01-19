'use client';

import { useState } from 'react';
import MainLayout from '@/components/layout/main-layout';
import ArchitectureGraph, {
  GraphNode,
  GraphEdge,
} from '@/components/architecture/architecture-graph';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Network,
  Layers,
  AlertCircle,
  CheckCircle2,
  Info,
  Code,
  FileCode,
} from 'lucide-react';

export default function ArchitecturePage() {
  const [isLoading, setIsLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedProject, setSelectedProject] = useState('project-1');
  const [layoutAlgorithm, setLayoutAlgorithm] = useState('force-directed');

  // Mock data - replace with actual API call
  const mockNodes: GraphNode[] = [
    {
      id: '1',
      label: 'UserController',
      type: 'Controller',
      health: 'healthy',
      complexity: 5,
      position: { x: 250, y: 50 },
    },
    {
      id: '2',
      label: 'AuthService',
      type: 'Service',
      health: 'warning',
      complexity: 12,
      position: { x: 100, y: 200 },
    },
    {
      id: '3',
      label: 'UserService',
      type: 'Service',
      health: 'healthy',
      complexity: 8,
      position: { x: 400, y: 200 },
    },
    {
      id: '4',
      label: 'UserRepository',
      type: 'Repository',
      health: 'critical',
      complexity: 15,
      position: { x: 100, y: 350 },
    },
    {
      id: '5',
      label: 'Database',
      type: 'Data Store',
      health: 'healthy',
      complexity: 3,
      position: { x: 250, y: 500 },
    },
    {
      id: '6',
      label: 'EmailService',
      type: 'Service',
      health: 'healthy',
      complexity: 6,
      position: { x: 400, y: 350 },
    },
  ];

  const mockEdges: GraphEdge[] = [
    { id: 'e1-2', source: '1', target: '2', type: 'default' },
    { id: 'e1-3', source: '1', target: '3', type: 'default' },
    { id: 'e2-4', source: '2', target: '4', type: 'default' },
    { id: 'e3-4', source: '3', target: '4', type: 'default' },
    { id: 'e4-5', source: '4', target: '5', type: 'default' },
    { id: 'e3-6', source: '3', target: '6', type: 'default' },
    // Circular dependency example
    { id: 'e4-2', source: '4', target: '2', type: 'default', isCircular: true },
  ];

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'healthy':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'critical':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Info className="h-4 w-4 text-gray-500" />;
    }
  };

  if (isLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Network className="h-8 w-8" />
              Architecture Visualization
            </h1>
            <p className="text-muted-foreground mt-1">
              Interactive visualization of your project's architecture
            </p>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Control Panel */}
          <div className="lg:col-span-1 space-y-6">
            <Card className="p-4">
              <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                <Layers className="h-4 w-4" />
                Controls
              </h3>

              <div className="space-y-4">
                {/* Project Selector */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Project
                  </label>
                  <Select
                    value={selectedProject}
                    onValueChange={setSelectedProject}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="project-1">
                        AI Code Review Platform
                      </SelectItem>
                      <SelectItem value="project-2">E-commerce API</SelectItem>
                      <SelectItem value="project-3">
                        Analytics Dashboard
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Layout Algorithm */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Layout Algorithm
                  </label>
                  <Select
                    value={layoutAlgorithm}
                    onValueChange={setLayoutAlgorithm}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="force-directed">
                        Force Directed
                      </SelectItem>
                      <SelectItem value="hierarchical">Hierarchical</SelectItem>
                      <SelectItem value="circular">Circular</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* View Options */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Node Size By
                  </label>
                  <Select defaultValue="complexity">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="complexity">Complexity</SelectItem>
                      <SelectItem value="loc">Lines of Code</SelectItem>
                      <SelectItem value="dependencies">Dependencies</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Filter Options */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Filter by Layer
                  </label>
                  <Select defaultValue="all">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Layers</SelectItem>
                      <SelectItem value="presentation">Presentation</SelectItem>
                      <SelectItem value="business">Business Logic</SelectItem>
                      <SelectItem value="data">Data Access</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Health Filter */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Filter by Health
                  </label>
                  <Select defaultValue="all">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="healthy">Healthy</SelectItem>
                      <SelectItem value="warning">Warning</SelectItem>
                      <SelectItem value="critical">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </Card>

            {/* Legend */}
            <Card className="p-4">
              <h3 className="text-sm font-semibold mb-4">Legend</h3>
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded border-2 border-green-500 bg-green-50 dark:bg-green-950/30" />
                  <span>Healthy</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded border-2 border-yellow-500 bg-yellow-50 dark:bg-yellow-950/30" />
                  <span>Warning</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded border-2 border-red-500 bg-red-50 dark:bg-red-950/30" />
                  <span>Critical</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-0.5 bg-red-500" />
                  <span>Circular Dependency</span>
                </div>
              </div>
            </Card>
          </div>

          {/* Graph Canvas */}
          <div className="lg:col-span-2">
            <ArchitectureGraph
              nodes={mockNodes}
              edges={mockEdges}
              onNodeClick={setSelectedNode}
              highlightCircularDeps={true}
            />
          </div>

          {/* Details Panel */}
          <div className="lg:col-span-1 space-y-6">
            {selectedNode ? (
              <>
                <Card className="p-4">
                  <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                    <Code className="h-4 w-4" />
                    Component Details
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">
                        Name
                      </div>
                      <div className="font-medium">{selectedNode.label}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">
                        Type
                      </div>
                      <Badge variant="outline">{selectedNode.type}</Badge>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">
                        Health Status
                      </div>
                      <div className="flex items-center gap-2">
                        {getHealthIcon(selectedNode.health)}
                        <span className="capitalize">{selectedNode.health}</span>
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">
                        Complexity
                      </div>
                      <div className="font-medium">{selectedNode.complexity}</div>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <h3 className="text-sm font-semibold mb-4">Dependencies</h3>
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs text-muted-foreground mb-2">
                        Incoming (3)
                      </div>
                      <div className="space-y-1 text-sm">
                        <div className="flex items-center gap-2">
                          <FileCode className="h-3 w-3" />
                          <span>UserController</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <FileCode className="h-3 w-3" />
                          <span>AuthController</span>
                        </div>
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-2">
                        Outgoing (2)
                      </div>
                      <div className="space-y-1 text-sm">
                        <div className="flex items-center gap-2">
                          <FileCode className="h-3 w-3" />
                          <span>UserRepository</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <FileCode className="h-3 w-3" />
                          <span>EmailService</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <h3 className="text-sm font-semibold mb-4">Recent Changes</h3>
                  <div className="space-y-2 text-sm">
                    <div className="text-muted-foreground">
                      Last modified: 2 days ago
                    </div>
                    <div className="text-muted-foreground">
                      Modified by: john.doe
                    </div>
                    <Button variant="outline" size="sm" className="w-full mt-2">
                      View History
                    </Button>
                  </div>
                </Card>
              </>
            ) : (
              <Card className="p-6">
                <p className="text-sm text-muted-foreground text-center">
                  Click on a node to view details
                </p>
              </Card>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
