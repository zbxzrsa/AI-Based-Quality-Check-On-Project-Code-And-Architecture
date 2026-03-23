'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import {
  Network,
  Monitor,
  Server,
  Database,
  HardDrive,
  Brain,
  Search,
  Globe,
  Activity,
  Maximize2,
  Minimize2,
  CheckCircle2,
  AlertCircle,
  X,
  GitBranch,
  FolderTree,
  FileCode,
  Clock,
  ChevronRight,
  ArrowLeft,
  Info,
} from 'lucide-react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  BackgroundVariant,
  NodeTypes,
  MarkerType,
  Panel,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

/* ================================================================
   Types — matches backend BranchInfo / BranchArchitecture
   ================================================================ */
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
  properties?: Record<string, any>;
  metrics?: Record<string, number>;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  is_circular: boolean;
  properties?: Record<string, any>;
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
    high_violations: number;
  };
}

interface ProjectInfo {
  id: string;
  name: string;
  github_repo_url?: string;
  language?: string;
}

/* ================================================================
   Custom ReactFlow Nodes
   ================================================================ */
function ComponentNode({ data }: { data: any }) {
  const healthBorderColors: Record<string, string> = {
    healthy: '#22c55e', warning: '#eab308', critical: '#ef4444',
  };
  const healthDotColors: Record<string, string> = {
    healthy: '#22c55e', warning: '#eab308', critical: '#ef4444',
  };
  const typeIcons: Record<string, string> = {
    Component: '📦', module: '📁', class: '🏗️', function: '⚡', package: '📦',
    service: '🖥️', controller: '🎮', model: '💾', view: '👁️', Unknown: '❓',
  };

  const borderColor = healthBorderColors[data.health] || '#94a3b8';
  const dotColor = healthDotColors[data.health] || '#94a3b8';
  const icon = typeIcons[data.nodeType] || '📦';

  // Complexity → bar width
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
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px 6px' }}>
        <span style={{ fontSize: 20 }}>{icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 13, lineHeight: 1.3, wordBreak: 'break-word' }}>
            {data.label}
          </div>
          <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 1 }}>{data.nodeType}</div>
        </div>
        <div style={{ width: 10, height: 10, borderRadius: '50%', background: dotColor, flexShrink: 0 }} />
      </div>
      {/* Complexity bar */}
      <div style={{ padding: '4px 14px 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#94a3b8', marginBottom: 2 }}>
          <span>复杂度</span>
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

/* ================================================================
   Architecture Graph Component
   ================================================================ */
function ArchGraph({
  data,
  onNodeClick,
}: {
  data: BranchArchitecture;
  onNodeClick: (node: GraphNode) => void;
}) {
  const initialNodes: Node[] = useMemo(() => {
    return data.nodes.map((n) => ({
      id: n.id,
      type: 'componentNode',
      position: n.position,
      data: {
        label: n.label,
        nodeType: n.type,
        health: n.health,
        complexity: n.complexity,
      },
    }));
  }, [data.nodes]);

  const initialEdges: Edge[] = useMemo(() => {
    return data.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      animated: e.is_circular,
      style: {
        stroke: e.is_circular ? '#ef4444' : '#64748b',
        strokeWidth: e.is_circular ? 2.5 : 1.5,
        strokeDasharray: e.is_circular ? undefined : '6 3',
      },
      label: e.is_circular ? '循环依赖 ⚠' : undefined,
      labelStyle: { fontSize: 10, fontWeight: 700, fill: '#ef4444' },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: e.is_circular ? '#ef4444' : '#64748b',
        width: 14,
        height: 10,
      },
    }));
  }, [data.edges]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const orig = data.nodes.find((n) => n.id === node.id);
      if (orig) onNodeClick(orig);
    },
    [data.nodes, onNodeClick],
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
            const h = node.data?.health;
            return h === 'healthy' ? '#22c55e' : h === 'warning' ? '#eab308' : h === 'critical' ? '#ef4444' : '#94a3b8';
          }}
          maskColor="rgba(0,0,0,0.08)"
          style={{ bottom: 12, right: 12, borderRadius: 8, width: 140, height: 90 }}
        />
        <Panel position="top-right">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(255,255,255,0.95)', borderRadius: 8, padding: '6px 14px', fontSize: 11, border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />正常
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#eab308', display: 'inline-block' }} />警告
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', display: 'inline-block' }} />异常
            </span>
            <span style={{ height: 12, width: 1, background: '#e2e8f0' }} />
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 12, height: 2, background: '#ef4444', display: 'inline-block' }} />循环依赖
            </span>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}

/* ================================================================
   Node Detail Panel
   ================================================================ */
function NodeDetail({ node, onClose }: { node: GraphNode; onClose: () => void }) {
  const healthLabels: Record<string, string> = { healthy: '正常', warning: '警告', critical: '异常' };
  const healthColors: Record<string, string> = { healthy: '#22c55e', warning: '#eab308', critical: '#ef4444' };
  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderLeft: '4px solid #6366f1', borderRadius: 12, padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h4 style={{ fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Info style={{ width: 16, height: 16 }} />组件详情
        </h4>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
          <X style={{ width: 16, height: 16, color: '#94a3b8' }} />
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 13 }}>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>名称</div>
          <div style={{ fontWeight: 600 }}>{node.label}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>类型</div>
          <span style={{ padding: '2px 10px', borderRadius: 999, border: '1px solid #e2e8f0', fontSize: 12, background: '#f8fafc' }}>
            {node.type}
          </span>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>健康状态</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: healthColors[node.health] || '#94a3b8', display: 'inline-block' }} />
            {healthLabels[node.health] || node.health}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>复杂度</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 6, background: '#f1f5f9', borderRadius: 3 }}>
              <div style={{ width: `${Math.min(node.complexity / 10, 1) * 100}%`, height: '100%', background: node.complexity > 7 ? '#ef4444' : node.complexity > 4 ? '#eab308' : '#22c55e', borderRadius: 3 }} />
            </div>
            <span style={{ fontSize: 12, fontWeight: 600 }}>{node.complexity}/10</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   Statistics Card
   ================================================================ */
function StatCard({ label, value, icon, color }: { label: string; value: number | string; icon: React.ReactNode; color?: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: 16 }}>
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

/* ================================================================
   Main Architecture Page
   ================================================================ */
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

  // 1. Load projects on mount
  useEffect(() => {
    setMounted(true);
    fetch('/api/rbac/projects')
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setProjects(list);
        setLoadingProjects(false);
      })
      .catch(() => setLoadingProjects(false));
  }, []);

  // 2. Load branches when project is selected
  useEffect(() => {
    if (!selectedProjectId) { setBranches([]); setArchData(null); return; }
    setLoadingBranches(true);
    setBranches([]);
    setArchData(null);
    setSelectedBranchId('');
    setSelectedNode(null);

    fetch(`/api/architecture/${selectedProjectId}/branches`)
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setBranches(list);
        setLoadingBranches(false);
      })
      .catch(() => setLoadingBranches(false));
  }, [selectedProjectId]);

  // 3. Load architecture when branch is selected
  useEffect(() => {
    if (!selectedProjectId || !selectedBranchId) { setArchData(null); return; }
    setLoadingArch(true);
    setSelectedNode(null);

    fetch(`/api/architecture/${selectedProjectId}/branches/${selectedBranchId}/architecture`)
      .then((r) => {
        if (!r.ok) {
          console.error(`Architecture fetch failed: ${r.status} ${r.statusText}`);
          return r.json().then(err => {
            console.error('Architecture API error:', err);
            return null;
          });
        }
        return r.json();
      })
      .then((data) => {
        console.log('Architecture data received:', data);
        if (data && data.nodes && data.nodes.length > 0) setArchData(data);
        else setArchData(null);
        setLoadingArch(false);
      })
      .catch((err) => { console.error('Architecture fetch error:', err); setArchData(null); setLoadingArch(false); });
  }, [selectedProjectId, selectedBranchId]);

  // SSR guard — render identical loading state on server + first client render
  if (!mounted) {
    return (
      <MainLayout>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
            <Network style={{ width: 32, height: 32 }} />
            Architecture Analysis
          </h1>
          <p style={{ color: '#94a3b8', marginBottom: 24 }}>根据代码审查生成项目架构图</p>
          <div style={{ height: 500, background: '#f8fafc', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <p style={{ color: '#94a3b8' }}>加载中...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  const healthBadgeStyle = (h: string) =>
    h === 'healthy' ? { bg: '#dcfce7', color: '#166534', text: '健康' }
      : h === 'warning' ? { bg: '#fef9c3', color: '#854d0e', text: '警告' }
        : { bg: '#fecaca', color: '#991b1b', text: '异常' };

  return (
    <MainLayout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {/* Header */}
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
            <Network style={{ width: 32, height: 32 }} />
            Architecture Analysis
          </h1>
          <p style={{ color: '#94a3b8' }}>根据代码审查生成项目架构图</p>
        </div>

        {/* Step 1: Project Selector */}
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <FolderTree style={{ width: 18, height: 18, color: '#6366f1' }} />
            选择项目
          </h3>
          {loadingProjects ? (
            <p style={{ color: '#94a3b8', fontSize: 14 }}>正在加载项目列表...</p>
          ) : projects.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 24 }}>
              <p style={{ color: '#94a3b8', marginBottom: 12 }}>暂无项目，请先添加 GitHub 项目</p>
              <button onClick={() => router.push('/projects')} style={{ padding: '8px 20px', borderRadius: 8, background: '#6366f1', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13 }}>
                前往项目管理
              </button>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
              {projects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setSelectedProjectId(p.id)}
                  style={{
                    padding: '14px 16px',
                    borderRadius: 10,
                    border: selectedProjectId === p.id ? '2px solid #6366f1' : '1px solid #e2e8f0',
                    background: selectedProjectId === p.id ? '#eef2ff' : '#fff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.2s',
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{p.name}</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>
                    {p.github_repo_url ? p.github_repo_url.replace('https://github.com/', '') : '未关联仓库'}
                    {p.language && ` · ${p.language}`}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Step 2: Branch List */}
        {selectedProjectId && (
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
              <GitBranch style={{ width: 18, height: 18, color: '#6366f1' }} />
              已审查分支
            </h3>
            {loadingBranches ? (
              <p style={{ color: '#94a3b8', fontSize: 14 }}>正在加载分支数据...</p>
            ) : branches.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 24, background: '#f8fafc', borderRadius: 8 }}>
                <GitBranch style={{ width: 40, height: 40, color: '#cbd5e1', margin: '0 auto 12px' }} />
                <p style={{ color: '#94a3b8', fontSize: 14 }}>该项目暂无已审查的分支</p>
                <p style={{ color: '#cbd5e1', fontSize: 12, marginTop: 4 }}>请先通过 Pull Request 提交代码审查</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {branches.map((b) => {
                  const badge = healthBadgeStyle(b.health_status);
                  return (
                    <button
                      key={b.id}
                      onClick={() => setSelectedBranchId(b.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '12px 16px',
                        borderRadius: 10,
                        border: selectedBranchId === b.id ? '2px solid #6366f1' : '1px solid #e2e8f0',
                        background: selectedBranchId === b.id ? '#eef2ff' : '#fff',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.2s',
                        width: '100%',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <GitBranch style={{ width: 16, height: 16, color: '#6366f1' }} />
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 14 }}>{b.name}</div>
                          <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                            {b.last_commit} · {new Date(b.last_commit_date).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{ fontSize: 12, color: '#94a3b8' }}>{b.components_count} 组件</span>
                        {b.circular_dependencies > 0 && (
                          <span style={{ fontSize: 12, color: '#ef4444' }}>⚠ {b.circular_dependencies} 循环</span>
                        )}
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

        {/* Step 3: Architecture Graph */}
        {selectedBranchId && (
          <>
            {loadingArch ? (
              <div style={{ height: 500, background: '#f8fafc', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ textAlign: 'center' }}>
                  <Network style={{ width: 48, height: 48, color: '#94a3b8', margin: '0 auto 16px', animation: 'pulse 2s infinite' }} />
                  <p style={{ color: '#94a3b8', fontSize: 14 }}>正在加载架构图...</p>
                </div>
              </div>
            ) : archData && archData.nodes.length > 0 ? (
              <>
                <div style={isFullscreen ? { position: 'fixed', inset: 0, zIndex: 50, background: '#fff', padding: 24 } : {}}>
                  {isFullscreen && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                      <h2 style={{ fontSize: 20, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Network style={{ width: 24, height: 24 }} />
                        {archData.branch_info.name} — 架构图
                      </h2>
                      <button onClick={() => setIsFullscreen(false)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', cursor: 'pointer', fontSize: 13 }}>
                        <Minimize2 style={{ width: 16, height: 16 }} />关闭
                      </button>
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: selectedNode && !isFullscreen ? '1fr 260px' : '1fr', gap: 16 }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                        <h3 style={{ fontSize: 18, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                          <FileCode style={{ width: 20, height: 20 }} />
                          {archData.branch_info.name} — 代码架构图
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
                              <Maximize2 style={{ width: 14, height: 14 }} />全屏
                            </button>
                          )}
                        </div>
                      </div>
                      <ArchGraph data={archData} onNodeClick={setSelectedNode} />
                    </div>
                    {selectedNode && !isFullscreen && (
                      <NodeDetail node={selectedNode} onClose={() => setSelectedNode(null)} />
                    )}
                  </div>
                </div>

                {/* Statistics */}
                {!isFullscreen && archData.statistics && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                    <StatCard label="组件数" value={archData.statistics.total_components} icon={<FileCode style={{ width: 28, height: 28, color: '#3b82f6' }} />} />
                    <StatCard label="依赖关系" value={archData.statistics.total_dependencies} icon={<Network style={{ width: 28, height: 28, color: '#8b5cf6' }} />} />
                    <StatCard label="循环依赖" value={archData.statistics.circular_dependencies} icon={<AlertCircle style={{ width: 28, height: 28, color: '#ef4444' }} />} color={archData.statistics.circular_dependencies > 0 ? '#ef4444' : '#22c55e'} />
                    <StatCard label="平均复杂度" value={archData.statistics.avg_complexity + '/10'} icon={<Activity style={{ width: 28, height: 28, color: '#eab308' }} />} color="#eab308" />
                    <StatCard label="架构违规" value={archData.statistics.violations_count} icon={<AlertCircle style={{ width: 28, height: 28, color: '#f97316' }} />} color={archData.statistics.violations_count > 0 ? '#f97316' : '#22c55e'} />
                    <StatCard label="严重违规" value={archData.statistics.critical_violations} icon={<AlertCircle style={{ width: 28, height: 28, color: '#ef4444' }} />} color={archData.statistics.critical_violations > 0 ? '#ef4444' : '#22c55e'} />
                  </div>
                )}
              </>
            ) : (
              <div style={{ padding: 32, background: '#f8fafc', borderRadius: 12, textAlign: 'center' }}>
                <Network style={{ width: 48, height: 48, color: '#cbd5e1', margin: '0 auto 12px' }} />
                <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>暂无架构数据</h3>
                <p style={{ color: '#94a3b8', fontSize: 13 }}>
                  该分支的代码审查尚未生成架构分析，请先提交 Pull Request 进行代码审查
                </p>
              </div>
            )}
          </>
        )}

        {/* Empty state — no project or branch selected */}
        {!selectedProjectId && !loadingProjects && projects.length > 0 && (
          <div style={{ padding: 40, background: '#f8fafc', borderRadius: 12, textAlign: 'center' }}>
            <Network style={{ width: 56, height: 56, color: '#cbd5e1', margin: '0 auto 16px' }} />
            <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#475569' }}>选择项目查看架构图</h3>
            <p style={{ color: '#94a3b8', fontSize: 14 }}>
              请在上方选择一个项目，然后选择已审查的分支以查看代码架构图
            </p>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
