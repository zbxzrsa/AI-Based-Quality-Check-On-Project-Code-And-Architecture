'use client';

import { useCallback, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MiniMap,
  BackgroundVariant,
  NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Card } from '@/components/ui/card';

// Custom node component
function CustomNode({ data }: { data: any }) {
  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy':
        return 'border-green-500 bg-green-50 dark:bg-green-950/30';
      case 'warning':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950/30';
      case 'critical':
        return 'border-red-500 bg-red-50 dark:bg-red-950/30';
      default:
        return 'border-gray-500 bg-gray-50 dark:bg-gray-950/30';
    }
  };

  return (
    <div
      className={`px-4 py-2 rounded-md border-2 ${getHealthColor(
        data.health
      )} min-w-[120px]`}
    >
      <div className="font-semibold text-sm">{data.label}</div>
      {data.type && (
        <div className="text-xs text-muted-foreground mt-1">{data.type}</div>
      )}
      {data.complexity && (
        <div className="text-xs text-muted-foreground">
          Complexity: {data.complexity}
        </div>
      )}
    </div>
  );
}

const nodeTypes: NodeTypes = {
  custom: CustomNode,
};

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  health: 'healthy' | 'warning' | 'critical';
  complexity?: number;
  position: { x: number; y: number };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  isCircular?: boolean;
}

interface ArchitectureGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
  highlightCircularDeps?: boolean;
}

export default function ArchitectureGraph({
  nodes: initialNodes,
  edges: initialEdges,
  onNodeClick,
  highlightCircularDeps = true,
}: ArchitectureGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(
    initialNodes.map((node) => ({
      id: node.id,
      type: 'custom',
      data: {
        label: node.label,
        type: node.type,
        health: node.health,
        complexity: node.complexity,
      },
      position: node.position,
    }))
  );

  const [edges, setEdges, onEdgesChange] = useEdgesState(
    initialEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edge.type || 'default',
      animated: edge.isCircular && highlightCircularDeps,
      style: {
        stroke:
          edge.isCircular && highlightCircularDeps ? '#ef4444' : '#94a3b8',
        strokeWidth: edge.isCircular && highlightCircularDeps ? 3 : 2,
      },
      label: edge.isCircular && highlightCircularDeps ? 'Circular' : undefined,
      labelStyle: {
        fill: '#ef4444',
        fontWeight: 700,
      },
    }))
  );

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const originalNode = initialNodes.find((n) => n.id === node.id);
      if (originalNode && onNodeClick) {
        onNodeClick(originalNode);
      }
    },
    [initialNodes, onNodeClick]
  );

  return (
    <Card className="w-full h-[600px] overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
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
          maskColor="rgba(0, 0, 0, 0.1)"
        />
      </ReactFlow>
    </Card>
  );
}
