'use client';

import { useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import ArchitectureGraph from '@/components/architecture/architecture-graph';
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
  ArrowLeft,
  GitBranch,
  Clock,
} from 'lucide-react';
import { useBranchArchitecture } from '@/hooks/useProjects';
import type { GraphNode, GraphEdge } from '@/hooks/useProjects';

export default function BranchArchitecturePage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const branchId = params?.branchId as string || '';
  const projectId = searchParams?.get('project') || '';
  
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [layoutAlgorithm, setLayoutAlgorithm] = useState('force-directed');

  const { data: architectureData, isLoading } = useBranchArchitecture(projectId, branchId);

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

  if (!projectId) {
    return (
      <MainLayout>
        <Card>
          <div className="p-6 text-center">
            <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Project Selected</h3>
            <Button onClick={() => router.push('/projects')}>
              Go to Projects
            </Button>
          </div>
        </Card>
      </MainLayout>
    );
  }

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

  if (!architectureData) {
    return (
      <MainLayout>
        <Card>
          <div className="p-6 text-center">
            <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Branch Not Found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              The requested branch could not be found or has no architecture data
            </p>
            <Button onClick={() => router.push(`/architecture?project=${projectId}`)}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Branches
            </Button>
          </div>
        </Card>
      </MainLayout>
    );
  }

  const { branch_info, nodes, edges, statistics } = architectureData;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push(`/architecture?project=${projectId}`)}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Branches
              </Button>
            </div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <GitBranch className="h-8 w-8" />
              {branch_info.name}
            </h1>
            <p className="text-muted-foreground mt-1">
              Architecture visualization for this branch
            </p>
          </div>
        </div>

        {/* Branch Info Card */}
        <Card className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Last Commit</p>
              <p className="font-medium">{branch_info.last_commit}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Author</p>
              <p className="font-medium">{branch_info.author}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Last Updated</p>
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                <p className="font-medium">
                  {new Date(branch_info.last_commit_date).toLocaleDateString()}
                </p>
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Components</p>
              <p className="font-medium">{branch_info.components_count}</p>
            </div>
          </div>
        </Card>

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

            {/* Statistics */}
            <Card className="p-4">
              <h3 className="text-sm font-semibold mb-4">Statistics</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Components</span>
                  <span className="font-medium">{statistics.total_components}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Dependencies</span>
                  <span className="font-medium">{statistics.total_dependencies}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Circular Deps</span>
                  <span className="font-medium text-red-600">
                    {statistics.circular_dependencies}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Avg Complexity</span>
                  <span className="font-medium">{statistics.avg_complexity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Violations</span>
                  <span className="font-medium text-yellow-600">
                    {statistics.violations_count}
                  </span>
                </div>
              </div>
            </Card>
          </div>

          {/* Graph Canvas */}
          <div className="lg:col-span-2">
            {nodes.length > 0 ? (
              <ArchitectureGraph
                nodes={nodes}
                edges={edges}
                onNodeClick={setSelectedNode}
                highlightCircularDeps={true}
              />
            ) : (
              <Card className="p-12">
                <div className="text-center">
                  <Network className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Architecture Data</h3>
                  <p className="text-sm text-muted-foreground">
                    This branch has not been analyzed yet or has no components
                  </p>
                </div>
              </Card>
            )}
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
                        Incoming ({edges.filter((e) => e.target === selectedNode.id).length})
                      </div>
                      <div className="space-y-1 text-sm">
                        {edges
                          .filter((e) => e.target === selectedNode.id)
                          .map((edge) => {
                            const sourceNode = nodes.find((n) => n.id === edge.source);
                            return (
                              <div key={edge.id} className="flex items-center gap-2">
                                <FileCode className="h-3 w-3" />
                                <span>{sourceNode?.label || 'Unknown'}</span>
                              </div>
                            );
                          })}
                        {edges.filter((e) => e.target === selectedNode.id).length === 0 && (
                          <p className="text-xs text-muted-foreground">No incoming dependencies</p>
                        )}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-2">
                        Outgoing ({edges.filter((e) => e.source === selectedNode.id).length})
                      </div>
                      <div className="space-y-1 text-sm">
                        {edges
                          .filter((e) => e.source === selectedNode.id)
                          .map((edge) => {
                            const targetNode = nodes.find((n) => n.id === edge.target);
                            return (
                              <div key={edge.id} className="flex items-center gap-2">
                                <FileCode className="h-3 w-3" />
                                <span>{targetNode?.label || 'Unknown'}</span>
                                {edge.is_circular && (
                                  <Badge variant="destructive" className="text-xs">
                                    Circular
                                  </Badge>
                                )}
                              </div>
                            );
                          })}
                        {edges.filter((e) => e.source === selectedNode.id).length === 0 && (
                          <p className="text-xs text-muted-foreground">No outgoing dependencies</p>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <h3 className="text-sm font-semibold mb-4">Actions</h3>
                  <div className="space-y-2">
                    <Button variant="outline" size="sm" className="w-full">
                      View Source Code
                    </Button>
                    <Button variant="outline" size="sm" className="w-full">
                      View History
                    </Button>
                    <Button variant="outline" size="sm" className="w-full">
                      Run Analysis
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
