'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { PageHeader } from '@/components/layout/page-header';
import { apiGet } from '@/lib/api-client';
import { Network, Activity, Maximize2, Minimize2, AlertCircle, X, GitBranch, FolderTree, FileCode, ChevronRight, Info } from 'lucide-react';
import ReactFlow, { Background, BackgroundVariant, Controls, Edge, MarkerType, MiniMap, Node, NodeTypes, Panel, useEdgesState, useNodesState } from 'reactflow';
import 'reactflow/dist/style.css';

interface BranchInfo {
  id: string;
  name: string;
  last_commit: string;
  last_commit_date: string;
  author: string;
  components_count: number;
  complexity: number;
  health_status: string;
  circular_dependencies: number;
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
  health: string;
  complexity: number;
  position: { x: number; y: number };
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  is_circular: boolean;
}

interface BranchArchitecture {
  branch_info: BranchInfo;
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics: {
    total_components: number;
    total_dependencies: number;
    circular_dependencies: number;
    avg_complexity: number;
    violations_count: number;
    critical_violations: number;
  };
}

interface ProjectInfo {
  id: string;
  name: string;
  github_repo_url?: string;
  language?: string;
}

function ComponentNode({ data }: { data: { label: string; nodeType: string; health: string; complexity: number } }) {
  const borderColor =
    data.health === 'healthy' ? '#22c55e' : data.health === 'warning' ? '#eab308' : data.health === 'critical' ? '#ef4444' : '#94a3b8';

  const complexityPercent = Math.min((data.complexity || 5) / 10, 1) * 100;
  const complexityColor = data.complexity > 7 ? '#ef4444' : data.complexity > 4 ? '#eab308' : '#22c55e';

  return (
    <div
      style={{
        background: '#fff',
        border: `2px solid ${borderColor}`,
        borderRadius: 12,
        minWidth: 180,
        boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
      }}
    >
      <div style={{ padding: '10px 14px 6px' }}>
        <div style={{ fontWeight: 700, fontSize: 13, lineHeight: 1.3, wordBreak: 'break-word' }}>{data.label}</div>
        <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>{data.nodeType}</div>
      </div>
      <div style={{ padding: '4px 14px 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#94a3b8', marginBottom: 2 }}>
          <span>Complexity</span>
          <span>{data.complexity || 5}/10</span>
        </div>
        <div style={{ width: '100%', height: 4, background: '#f1f5f9', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${complexityPercent}%`, height: '100%', background: complexityColor, borderRadius: 2 }} />
        </div>
      </div>
    </div>
  );
}

const nodeTypes: NodeTypes = {
  componentNode: ComponentNode,
};

function ArchitectureGraph({ data, onNodeClick }: { data: BranchArchitecture; onNodeClick: (node: GraphNode) => void }) {
  const initialNodes: Node[] = useMemo(
    () =>
      data.nodes.map((node) => ({
        id: node.id,
        type: 'componentNode',
        position: node.position,
        data: {
          label: node.label,
          nodeType: node.type,
          health: node.health,
          complexity: node.complexity,
        },
      })),
    [data.nodes]
  );

  const initialEdges: Edge[] = useMemo(
    () =>
      data.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: 'smoothstep',
        animated: edge.is_circular,
        style: {
          stroke: edge.is_circular ? '#ef4444' : '#64748b',
          strokeWidth: edge.is_circular ? 2.5 : 1.5,
          strokeDasharray: edge.is_circular ? undefined : '6 3',
        },
        label: edge.is_circular ? 'Circular dependency' : undefined,
        labelStyle: { fontSize: 10, fontWeight: 700, fill: '#ef4444' },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: edge.is_circular ? '#ef4444' : '#64748b',
          width: 14,
          height: 10,
        },
      })),
    [data.edges]
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const originalNode = data.nodes.find((item) => item.id === node.id);
      if (originalNode) {
        onNodeClick(originalNode);
      }
    },
    [data.nodes, onNodeClick]
  );

  return (
    <div style={{ width: '100%', height: 580, borderRadius: 12, overflow: 'hidden', border: '1px solid #e2e8f0' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.2}
        maxZoom={2.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e2e8f0" />
        <Controls showInteractive={false} style={{ bottom: 12, left: 12 }} />
        <MiniMap
          nodeColor={(node) => {
            const health = node.data?.health as string | undefined;
            return health === 'healthy' ? '#22c55e' : health === 'warning' ? '#eab308' : health === 'critical' ? '#ef4444' : '#94a3b8';
          }}
          maskColor="rgba(0,0,0,0.08)"
          style={{ bottom: 12, right: 12, borderRadius: 8, width: 140, height: 90 }}
        />
        <Panel position="top-right">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              background: 'rgba(255,255,255,0.95)',
              borderRadius: 8,
              padding: '6px 14px',
              fontSize: 11,
              border: '1px solid #e2e8f0',
              boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
              Healthy
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#eab308', display: 'inline-block' }} />
              Warning
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', display: 'inline-block' }} />
              Critical
            </span>
            <span style={{ height: 12, width: 1, background: '#e2e8f0' }} />
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 12, height: 2, background: '#ef4444', display: 'inline-block' }} />
              Circular dependency
            </span>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}

function NodeDetail({ node, onClose }: { node: GraphNode; onClose: () => void }) {
  const healthLabels: Record<string, string> = { healthy: 'Healthy', warning: 'Warning', critical: 'Critical' };
  const healthColors: Record<string, string> = { healthy: '#22c55e', warning: '#eab308', critical: '#ef4444' };

  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderLeft: '4px solid #6366f1', borderRadius: 12, padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h4 style={{ fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Info style={{ width: 16, height: 16 }} />
          Component details
        </h4>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
          <X style={{ width: 16, height: 16, color: '#94a3b8' }} />
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 13 }}>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>Name</div>
          <div style={{ fontWeight: 600 }}>{node.label}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>Type</div>
          <span style={{ padding: '2px 10px', borderRadius: 999, border: '1px solid #e2e8f0', fontSize: 12, background: '#f8fafc' }}>{node.type}</span>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>Health status</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: healthColors[node.health] || '#94a3b8', display: 'inline-block' }} />
            {healthLabels[node.health] || node.health}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>Complexity</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 6, background: '#f1f5f9', borderRadius: 3 }}>
              <div
                style={{
                  width: `${Math.min(node.complexity / 10, 1) * 100}%`,
                  height: '100%',
                  background: node.complexity > 7 ? '#ef4444' : node.complexity > 4 ? '#eab308' : '#22c55e',
                  borderRadius: 3,
                }}
              />
            </div>
            <span style={{ fontSize: 12, fontWeight: 600 }}>{node.complexity}/10</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: number | string; icon: React.ReactNode; color?: string }) {
  return (
    <div className="rounded-2xl border border-white/70 bg-white/85 p-4 shadow-sm dark:border-white/10 dark:bg-slate-950/60">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 13, color: '#94a3b8' }}>{label}</div>
          <div style={{ fontSize: 26, fontWeight: 700, color: color || '#1e293b', marginTop: 2 }}>{value}</div>
        </div>
        {icon}
      </div>
    </div>
  );
}

export default function ArchitecturePage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [branches, setBranches] = useState<BranchInfo[]>([]);
  const [selectedBranchId, setSelectedBranchId] = useState('');
  const [archData, setArchData] = useState<BranchArchitecture | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [loadingArch, setLoadingArch] = useState(false);

  useEffect(() => {
    setMounted(true);
    apiGet<ProjectInfo[]>('/api/rbac/projects')
      .then((data) => {
        setProjects(Array.isArray(data) ? data : []);
        setLoadingProjects(false);
      })
      .catch(() => setLoadingProjects(false));
  }, []);

  useEffect(() => {
    if (!selectedProjectId) {
      setBranches([]);
      setArchData(null);
      return;
    }

    setLoadingBranches(true);
    setBranches([]);
    setArchData(null);
    setSelectedBranchId('');
    setSelectedNode(null);

    apiGet<BranchInfo[]>(`/api/architecture/${selectedProjectId}/branches`)
      .then((data) => {
        setBranches(Array.isArray(data) ? data : []);
        setLoadingBranches(false);
      })
      .catch(() => setLoadingBranches(false));
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedProjectId || !selectedBranchId) {
      setArchData(null);
      return;
    }

    setLoadingArch(true);
    setSelectedNode(null);

    apiGet<BranchArchitecture>(`/api/architecture/${selectedProjectId}/branches/${selectedBranchId}/architecture`)
      .then((data) => {
        setArchData(data && data.nodes && data.nodes.length > 0 ? data : null);
        setLoadingArch(false);
      })
      .catch(() => {
        setArchData(null);
        setLoadingArch(false);
      });
  }, [selectedBranchId, selectedProjectId]);

  if (!mounted) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader
            title="Architecture Analysis"
            description="Generate an architecture view from reviewed project code."
          />
          <div className="flex h-[500px] items-center justify-center rounded-[28px] border border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
            <p style={{ color: '#94a3b8' }}>Loading...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  const healthBadgeStyle = (health: string) =>
    health === 'healthy'
      ? { bg: '#dcfce7', color: '#166534', text: 'Healthy' }
      : health === 'warning'
        ? { bg: '#fef9c3', color: '#854d0e', text: 'Warning' }
        : { bg: '#fecaca', color: '#991b1b', text: 'Critical' };

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <PageHeader
          title="Architecture Analysis"
          description="Generate an architecture view from reviewed project code, then drill into reviewed branches and graph-level component health in the same dashboard layout."
        />

        <div className="rounded-[28px] border border-white/70 bg-white/82 p-5 shadow-sm dark:border-white/10 dark:bg-slate-950/60">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <FolderTree style={{ width: 18, height: 18, color: '#6366f1' }} />
            Select a project
          </h3>
          {loadingProjects ? (
            <p style={{ color: '#94a3b8', fontSize: 14 }}>Loading projects...</p>
          ) : projects.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 24 }}>
              <p style={{ color: '#94a3b8', marginBottom: 12 }}>No projects are available yet. Add a GitHub project first.</p>
              <button onClick={() => router.push('/projects')} style={{ padding: '8px 20px', borderRadius: 8, background: '#6366f1', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13 }}>
                Go to Projects
              </button>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => setSelectedProjectId(project.id)}
                  style={{
                    padding: '14px 16px',
                    borderRadius: 10,
                    border: selectedProjectId === project.id ? '2px solid #6366f1' : '1px solid #e2e8f0',
                    background: selectedProjectId === project.id ? '#eef2ff' : '#fff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.2s',
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{project.name}</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>
                    {project.github_repo_url ? project.github_repo_url.replace('https://github.com/', '') : 'Repository not connected'}
                    {project.language && ` | ${project.language}`}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {selectedProjectId && (
          <div className="rounded-[28px] border border-white/70 bg-white/82 p-5 shadow-sm dark:border-white/10 dark:bg-slate-950/60">
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
              <GitBranch style={{ width: 18, height: 18, color: '#6366f1' }} />
              Reviewed branches
            </h3>
            {loadingBranches ? (
              <p style={{ color: '#94a3b8', fontSize: 14 }}>Loading branch data...</p>
            ) : branches.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 24, background: '#f8fafc', borderRadius: 8 }}>
                <GitBranch style={{ width: 40, height: 40, color: '#cbd5e1', margin: '0 auto 12px' }} />
                <p style={{ color: '#94a3b8', fontSize: 14 }}>No reviewed branches are available for this project.</p>
                <p style={{ color: '#cbd5e1', fontSize: 12, marginTop: 4 }}>Submit a pull request review first to generate branch architecture.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {branches.map((branch) => {
                  const badge = healthBadgeStyle(branch.health_status);
                  return (
                    <button
                      key={branch.id}
                      onClick={() => setSelectedBranchId(branch.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '12px 16px',
                        borderRadius: 10,
                        border: selectedBranchId === branch.id ? '2px solid #6366f1' : '1px solid #e2e8f0',
                        background: selectedBranchId === branch.id ? '#eef2ff' : '#fff',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.2s',
                        width: '100%',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <GitBranch style={{ width: 16, height: 16, color: '#6366f1' }} />
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 14 }}>{branch.name}</div>
                          <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                            {branch.last_commit} | {new Date(branch.last_commit_date).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{ fontSize: 12, color: '#94a3b8' }}>{branch.components_count} components</span>
                        {branch.circular_dependencies > 0 && <span style={{ fontSize: 12, color: '#ef4444' }}>Warning: {branch.circular_dependencies} cycles</span>}
                        <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600, background: badge.bg, color: badge.color }}>
                          {badge.text}
                        </span>
                        <ChevronRight style={{ width: 16, height: 16, color: '#cbd5e1' }} />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {selectedBranchId && (
          <>
            {loadingArch ? (
              <div style={{ height: 500, background: '#f8fafc', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ textAlign: 'center' }}>
                  <Network style={{ width: 48, height: 48, color: '#94a3b8', margin: '0 auto 16px', animation: 'pulse 2s infinite' }} />
                  <p style={{ color: '#94a3b8', fontSize: 14 }}>Loading architecture graph...</p>
                </div>
              </div>
            ) : archData && archData.nodes.length > 0 ? (
              <>
                <div style={isFullscreen ? { position: 'fixed', inset: 0, zIndex: 50, background: '#fff', padding: 24 } : {}}>
                  {isFullscreen && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                      <h2 style={{ fontSize: 20, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Network style={{ width: 24, height: 24 }} />
                        {archData.branch_info.name} architecture graph
                      </h2>
                      <button onClick={() => setIsFullscreen(false)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', cursor: 'pointer', fontSize: 13 }}>
                        <Minimize2 style={{ width: 16, height: 16 }} />
                        Close
                      </button>
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: selectedNode && !isFullscreen ? '1fr 260px' : '1fr', gap: 16 }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                        <h3 style={{ fontSize: 18, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                          <FileCode style={{ width: 20, height: 20 }} />
                          {archData.branch_info.name} code architecture
                        </h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          {(() => {
                            const badge = healthBadgeStyle(archData.branch_info.health_status);
                            return (
                              <span style={{ padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 600, background: badge.bg, color: badge.color }}>
                                {badge.text}
                              </span>
                            );
                          })()}
                          {!isFullscreen && (
                            <button onClick={() => setIsFullscreen(true)} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderRadius: 6, border: '1px solid #e2e8f0', background: '#fff', cursor: 'pointer', fontSize: 12 }}>
                              <Maximize2 style={{ width: 14, height: 14 }} />
                              Fullscreen
                            </button>
                          )}
                        </div>
                      </div>
                      <ArchitectureGraph data={archData} onNodeClick={setSelectedNode} />
                    </div>
                    {selectedNode && !isFullscreen && <NodeDetail node={selectedNode} onClose={() => setSelectedNode(null)} />}
                  </div>
                </div>

                {!isFullscreen && archData.statistics && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                    <StatCard label="Components" value={archData.statistics.total_components} icon={<FileCode style={{ width: 28, height: 28, color: '#3b82f6' }} />} />
                    <StatCard label="Dependencies" value={archData.statistics.total_dependencies} icon={<Network style={{ width: 28, height: 28, color: '#8b5cf6' }} />} />
                    <StatCard label="Circular dependencies" value={archData.statistics.circular_dependencies} icon={<AlertCircle style={{ width: 28, height: 28, color: '#ef4444' }} />} color={archData.statistics.circular_dependencies > 0 ? '#ef4444' : '#22c55e'} />
                    <StatCard label="Average complexity" value={`${archData.statistics.avg_complexity}/10`} icon={<Activity style={{ width: 28, height: 28, color: '#eab308' }} />} color="#eab308" />
                    <StatCard label="Architecture violations" value={archData.statistics.violations_count} icon={<AlertCircle style={{ width: 28, height: 28, color: '#f97316' }} />} color={archData.statistics.violations_count > 0 ? '#f97316' : '#22c55e'} />
                    <StatCard label="Critical violations" value={archData.statistics.critical_violations} icon={<AlertCircle style={{ width: 28, height: 28, color: '#ef4444' }} />} color={archData.statistics.critical_violations > 0 ? '#ef4444' : '#22c55e'} />
                  </div>
                )}
              </>
            ) : (
              <div style={{ padding: 32, background: '#f8fafc', borderRadius: 12, textAlign: 'center' }}>
                <Network style={{ width: 48, height: 48, color: '#cbd5e1', margin: '0 auto 12px' }} />
                <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No architecture data available</h3>
                <p style={{ color: '#94a3b8', fontSize: 13 }}>This branch does not have generated architecture analysis yet. Submit a pull request review first.</p>
              </div>
            )}
          </>
        )}

        {!selectedProjectId && !loadingProjects && projects.length > 0 && (
          <div style={{ padding: 40, background: '#f8fafc', borderRadius: 12, textAlign: 'center' }}>
            <Network style={{ width: 56, height: 56, color: '#cbd5e1', margin: '0 auto 16px' }} />
            <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#475569' }}>Select a project to view architecture</h3>
            <p style={{ color: '#94a3b8', fontSize: 14 }}>Choose a project above, then select a reviewed branch to explore the architecture graph.</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
