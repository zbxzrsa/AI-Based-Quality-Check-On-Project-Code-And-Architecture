'use client';

/**
 * Dependency Graph Visualization using React Flow
 */
import { useCallback, useState, useMemo } from 'react';
import ReactFlow, {
    Node,
    Edge,
    Controls,
    Background,
    MiniMap,
    useNodesState,
    useEdgesState,
    NodeProps,
    MarkerType,
    Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Search, ZoomIn, ZoomOut, Maximize, Download } from 'lucide-react';

interface GraphNode {
    id: string;
    type: 'module' | 'class' | 'function';
    name: string;
    importance: number; // in-degree + out-degree
    metadata?: Record<string, any>;
}

interface GraphEdge {
    source: string;
    target: string;
    type: 'depends' | 'calls' | 'implements';
    weight: number;
}

interface DependencyGraphProps {
    nodes: GraphNode[];
    edges: GraphEdge[];
    onNodeClick?: (node: GraphNode) => void;
}

// Custom node component
function CustomNode({ data }: NodeProps) {
    const getNodeColor = () => {
        switch (data.type) {
            case 'module':
                return 'bg-blue-500';
            case 'class':
                return 'bg-purple-500';
            case 'function':
                return 'bg-green-500';
            default:
                return 'bg-gray-500';
        }
    };

    return (
        <div
            className={`px-4 py-2 rounded-lg shadow-lg border-2 border-white dark:border-gray-700 ${getNodeColor()} text-white`}
            style={{
                minWidth: Math.max(80, data.importance * 10),
            }}
        >
            <div className="font-semibold text-sm truncate">{data.label}</div>
            <div className="text-xs opacity-75">{data.type}</div>
        </div>
    );
}

const nodeTypes = {
    custom: CustomNode,
};

export default function DependencyGraph({ nodes: graphNodes, edges: graphEdges, onNodeClick }: DependencyGraphProps) {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedType, setSelectedType] = useState<string>('all');

    // Transform data to React Flow format
    const initialNodes: Node[] = useMemo(
        () =>
            graphNodes.map((node, index) => ({
                id: node.id,
                type: 'custom',
                position: {
                    x: Math.random() * 500,
                    y: Math.random() * 500,
                },
                data: {
                    label: node.name,
                    type: node.type,
                    importance: node.importance,
                    ...node.metadata,
                },
            })),
        [graphNodes]
    );

    const initialEdges: Edge[] = useMemo(
        () =>
            graphEdges.map((edge) => ({
                id: `${edge.source}-${edge.target}`,
                source: edge.source,
                target: edge.target,
                type: 'smoothstep',
                animated: edge.type === 'calls',
                label: edge.type,
                labelStyle: { fontSize: 10, fill: '#666' },
                style: {
                    strokeWidth: Math.max(1, edge.weight * 2),
                    stroke:
                        edge.type === 'depends'
                            ? '#3b82f6'
                            : edge.type === 'calls'
                                ? '#10b981'
                                : '#8b5cf6',
                },
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color:
                        edge.type === 'depends'
                            ? '#3b82f6'
                            : edge.type === 'calls'
                                ? '#10b981'
                                : '#8b5cf6',
                },
            })),
        [graphEdges]
    );

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    // Filter nodes based on search and type
    const filteredNodes = useMemo(() => {
        return nodes.filter((node) => {
            const matchesSearch = node.data.label.toLowerCase().includes(searchTerm.toLowerCase());
            const matchesType = selectedType === 'all' || node.data.type === selectedType;
            return matchesSearch && matchesType;
        });
    }, [nodes, searchTerm, selectedType]);

    // Filter edges to only show those connected to visible nodes
    const filteredEdges = useMemo(() => {
        const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));
        return edges.filter(
            (edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
        );
    }, [edges, filteredNodes]);

    const onNodeClickHandler = useCallback(
        (event: any, node: Node) => {
            const graphNode = graphNodes.find((n) => n.id === node.id);
            if (graphNode && onNodeClick) {
                onNodeClick(graphNode);
            }
        },
        [graphNodes, onNodeClick]
    );

    const handleExport = () => {
        // Export to SVG/PNG (implementation would use html2canvas or similar)
        console.log('Export functionality to be implemented');
    };

    return (
        <div className="h-full w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden">
            <ReactFlow
                nodes={filteredNodes}
                edges={filteredEdges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClickHandler}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-left"
            >
                <Background />
                <Controls />
                <MiniMap
                    nodeColor={(node) => {
                        switch (node.data.type) {
                            case 'module':
                                return '#3b82f6';
                            case 'class':
                                return '#8b5cf6';
                            case 'function':
                                return '#10b981';
                            default:
                                return '#6b7280';
                        }
                    }}
                    maskColor="rgba(0, 0, 0, 0.1)"
                />

                {/* Control Panel */}
                <Panel position="top-right" className="space-y-2">
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 space-y-3">
                        {/* Search */}
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Search nodes..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                            />
                        </div>

                        {/* Type Filter */}
                        <select
                            value={selectedType}
                            onChange={(e) => setSelectedType(e.target.value)}
                            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                        >
                            <option value="all">All Types</option>
                            <option value="module">Modules</option>
                            <option value="class">Classes</option>
                            <option value="function">Functions</option>
                        </select>

                        {/* Actions */}
                        <div className="flex gap-2">
                            <button
                                onClick={handleExport}
                                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
                            >
                                <Download className="h-4 w-4" />
                                Export
                            </button>
                        </div>

                        {/* Legend */}
                        <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                            <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Legend
                            </p>
                            <div className="space-y-1.5">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded bg-blue-500" />
                                    <span className="text-xs text-gray-600 dark:text-gray-400">Module</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded bg-purple-500" />
                                    <span className="text-xs text-gray-600 dark:text-gray-400">Class</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded bg-green-500" />
                                    <span className="text-xs text-gray-600 dark:text-gray-400">Function</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </Panel>
            </ReactFlow>
        </div>
    );
}
