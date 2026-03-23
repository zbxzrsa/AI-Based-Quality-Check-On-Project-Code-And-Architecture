'use client';

import { useCallback, useMemo } from 'react';
import ReactFlow, {
    Node,
    Edge,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    MiniMap,
    BackgroundVariant,
    NodeTypes,
    MarkerType,
    Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Monitor,
    Server,
    Database,
    HardDrive,
    Brain,
    GitBranch,
    Activity,
    Shield,
    Search,
    Globe,
} from 'lucide-react';

// Types
interface OverviewNode {
    id: string;
    label: string;
    type: string;
    group: string;
    health: string;
    description: string;
    position: { x: number; y: number };
    style?: { background: string; borderColor: string };
}

interface OverviewEdge {
    id: string;
    source: string;
    target: string;
    label: string;
    type: string;
    style?: Record<string, string>;
}

interface GroupInfo {
    id: string;
    label: string;
    color: string;
    borderColor: string;
}

// Icon mapping for node types
function getNodeIcon(type: string) {
    switch (type) {
        case 'frontend':
            return <Monitor className="h-5 w-5" />;
        case 'backend':
            return <Server className="h-5 w-5" />;
        case 'database':
            return <Database className="h-5 w-5" />;
        case 'cache':
            return <HardDrive className="h-5 w-5" />;
        case 'graph_db':
            return <Search className="h-5 w-5" />;
        case 'ai_engine':
            return <Brain className="h-5 w-5" />;
        case 'external':
            return <Globe className="h-5 w-5" />;
        case 'gateway':
            return <Shield className="h-5 w-5" />;
        default:
            return <Activity className="h-5 w-5" />;
    }
}

// Custom System Node Component
function SystemNode({ data }: { data: any }) {
    const healthBorder = {
        healthy: 'border-green-500',
        warning: 'border-yellow-500',
        critical: 'border-red-500',
    }[data.health as string] || 'border-slate-400';

    const healthDot = {
        healthy: 'bg-green-500',
        warning: 'bg-yellow-500',
        critical: 'bg-red-500',
    }[data.health as string] || 'bg-slate-400';

    return (
        <div
            className={`rounded-xl border-2 ${healthBorder} shadow-lg min-w-[160px] transition-all hover:shadow-xl`}
            style={{
                background: data.nodeStyle?.background || '#fff',
            }}
        >
            {/* Header with icon */}
            <div className="flex items-center gap-2 px-4 pt-3 pb-1">
                <div
                    className="p-1.5 rounded-lg"
                    style={{
                        background: data.nodeStyle?.borderColor
                            ? `${data.nodeStyle.borderColor}20`
                            : '#f1f5f9',
                    }}
                >
                    {getNodeIcon(data.nodeType)}
                </div>
                <div className="flex-1 min-w-0">
                    <div className="font-bold text-sm leading-tight whitespace-pre-line">
                        {data.label}
                    </div>
                </div>
                <div className={`w-2.5 h-2.5 rounded-full ${healthDot} flex-shrink-0`} />
            </div>
            {/* Description */}
            {data.description && (
                <div className="px-4 pb-3 pt-1">
                    <div className="text-[10px] text-slate-500 leading-tight">
                        {data.description}
                    </div>
                </div>
            )}
        </div>
    );
}

// Group/Zone background node
function GroupNode({ data }: { data: any }) {
    return (
        <div
            className="rounded-2xl border-2 border-dashed"
            style={{
                background: data.color || '#f8fafc',
                borderColor: data.borderColor || '#e2e8f0',
                width: data.width || 820,
                height: data.height || 120,
                opacity: 0.5,
            }}
        >
            <div
                className="absolute -top-3 left-4 px-3 py-0.5 rounded-full text-xs font-semibold"
                style={{
                    background: data.borderColor || '#e2e8f0',
                    color: '#1e293b',
                }}
            >
                {data.label}
            </div>
        </div>
    );
}

const nodeTypes: NodeTypes = {
    systemNode: SystemNode,
    groupNode: GroupNode,
};

interface SystemArchitectureGraphProps {
    nodes: OverviewNode[];
    edges: OverviewEdge[];
    groups: GroupInfo[];
    onNodeClick?: (node: OverviewNode) => void;
    className?: string;
}

export default function SystemArchitectureGraph({
    nodes: apiNodes,
    edges: apiEdges,
    groups,
    onNodeClick,
    className = '',
}: SystemArchitectureGraphProps) {
    // Build ReactFlow nodes from API data
    const initialNodes: Node[] = useMemo(() => {
        const rfNodes: Node[] = [];

        // Group background nodes — positioned behind
        const groupPositions: Record<string, { x: number; y: number; w: number; h: number }> = {
            client: { x: 20, y: 0, w: 820, h: 100 },
            application: { x: 20, y: 120, w: 820, h: 200 },
            data: { x: 20, y: 340, w: 820, h: 140 },
            external: { x: 20, y: 500, w: 820, h: 130 },
        };

        groups.forEach((group) => {
            const pos = groupPositions[group.id] || { x: 0, y: 0, w: 820, h: 120 };
            rfNodes.push({
                id: `group-${group.id}`,
                type: 'groupNode',
                position: { x: pos.x, y: pos.y },
                data: {
                    label: group.label,
                    color: group.color,
                    borderColor: group.borderColor,
                    width: pos.w,
                    height: pos.h,
                },
                draggable: false,
                selectable: false,
                style: { zIndex: -1 },
            });
        });

        // Component nodes
        apiNodes.forEach((node) => {
            rfNodes.push({
                id: node.id,
                type: 'systemNode',
                position: node.position,
                data: {
                    label: node.label,
                    nodeType: node.type,
                    health: node.health,
                    description: node.description,
                    nodeStyle: node.style,
                },
            });
        });

        return rfNodes;
    }, [apiNodes, groups]);

    // Build ReactFlow edges
    const initialEdges: Edge[] = useMemo(() => {
        return apiEdges.map((edge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            type: 'smoothstep',
            animated: edge.type === 'animated',
            style: {
                stroke: edge.type === 'animated' ? '#9333ea' : '#64748b',
                strokeWidth: edge.type === 'dashed' ? 1.5 : 2,
                strokeDasharray: edge.type === 'dashed' ? '6 3' : undefined,
            },
            labelStyle: {
                fontSize: 10,
                fontWeight: 600,
                fill: '#475569',
            },
            markerEnd: {
                type: MarkerType.ArrowClosed,
                color: edge.type === 'animated' ? '#9333ea' : '#64748b',
                width: 16,
                height: 12,
            },
        }));
    }, [apiEdges]);

    const [nodes, , onNodesChange] = useNodesState(initialNodes);
    const [edges, , onEdgesChange] = useEdgesState(initialEdges);

    const handleNodeClick = useCallback(
        (_event: React.MouseEvent, node: Node) => {
            const originalNode = apiNodes.find((n) => n.id === node.id);
            if (originalNode && onNodeClick) {
                onNodeClick(originalNode);
            }
        },
        [apiNodes, onNodeClick]
    );

    return (
        <Card className={`w-full h-[680px] overflow-hidden ${className}`}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={handleNodeClick}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.3}
                maxZoom={2}
                attributionPosition="bottom-left"
                proOptions={{ hideAttribution: true }}
            >
                <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e2e8f0" />
                <Controls
                    showInteractive={false}
                    style={{ bottom: 12, left: 12 }}
                />
                <MiniMap
                    nodeColor={(node) => {
                        if (node.id.startsWith('group-')) return 'transparent';
                        const health = node.data?.health;
                        switch (health) {
                            case 'healthy':
                                return '#22c55e';
                            case 'warning':
                                return '#eab308';
                            case 'critical':
                                return '#ef4444';
                            default:
                                return '#94a3b8';
                        }
                    }}
                    maskColor="rgba(0, 0, 0, 0.08)"
                    style={{ bottom: 12, right: 12, borderRadius: 8 }}
                />
                <Panel position="top-right">
                    <div className="flex items-center gap-3 bg-white/90 dark:bg-slate-900/90 rounded-lg px-3 py-2 text-xs shadow-sm border">
                        <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-green-500" />
                            正常
                        </span>
                        <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-yellow-500" />
                            警告
                        </span>
                        <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-red-500" />
                            异常
                        </span>
                        <span className="flex items-center gap-1 text-purple-600">
                            <span className="w-4 h-0 border-t-2 border-purple-500 border-dashed" />
                            AI
                        </span>
                    </div>
                </Panel>
            </ReactFlow>
        </Card>
    );
}
