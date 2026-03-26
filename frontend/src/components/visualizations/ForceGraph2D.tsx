'use client';

import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useState,
} from 'react';

type GraphNode = {
  id: string;
  name?: string;
  label?: string;
  size?: number;
  [key: string]: unknown;
};

type GraphLink = {
  source: string | GraphNode;
  target: string | GraphNode;
  weight?: number;
  [key: string]: unknown;
};

interface ForceGraphData {
  nodes: GraphNode[];
  links?: GraphLink[];
  edges?: GraphLink[];
}

interface ZoomTransform {
  k: number;
}

export interface ForceGraphHandle {
  zoom: (value: number) => void;
  zoomToFit: () => void;
  d3Force: () => { distance: () => void; strength: () => void };
}

interface ForceGraph2DProps {
  graphData: ForceGraphData;
  nodeLabel?: string | ((node: GraphNode) => string);
  nodeColor?: (node: GraphNode) => string;
  nodeVal?: (node: GraphNode) => number;
  linkColor?: (link: GraphLink) => string;
  linkWidth?: (link: GraphLink) => number;
  onNodeClick?: (node: GraphNode) => void;
  onEngineStop?: () => void;
  onZoom?: (zoom: ZoomTransform) => void;
  width?: number;
  height?: number;
  nodeRelSize?: number;
  linkDirectionalArrowLength?: number;
  linkDirectionalArrowRelPos?: number;
  cooldownTicks?: number;
  enableNodeDrag?: boolean;
  enableZoomInteraction?: boolean;
  enablePanInteraction?: boolean;
  minZoom?: number;
  maxZoom?: number;
}

const DEFAULT_WIDTH = 800;
const DEFAULT_HEIGHT = 600;

function getNodeId(node: string | GraphNode): string {
  return typeof node === 'string' ? node : node.id;
}

const ForceGraph2D = forwardRef<ForceGraphHandle, ForceGraph2DProps>(function ForceGraph2D(
  {
    graphData,
    nodeLabel,
    nodeColor,
    nodeVal,
    linkColor,
    linkWidth,
    onNodeClick,
    onEngineStop,
    onZoom,
    width = DEFAULT_WIDTH,
    height = DEFAULT_HEIGHT,
  },
  ref
) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const links = graphData.links ?? graphData.edges ?? [];

  useImperativeHandle(ref, () => ({
    zoom: (value: number) => {
      setZoomLevel(value);
      onZoom?.({ k: value });
    },
    zoomToFit: () => {
      setZoomLevel(1);
      onZoom?.({ k: 1 });
    },
    d3Force: () => ({
      distance: () => undefined,
      strength: () => undefined,
    }),
  }), [onZoom]);

  useEffect(() => {
    onEngineStop?.();
  }, [graphData, onEngineStop]);

  const positionedNodes = useMemo(() => {
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.max(Math.min(width, height) / 3, 100);

    return graphData.nodes.map((node, index) => {
      const angle = (index / Math.max(graphData.nodes.length, 1)) * Math.PI * 2;
      return {
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });
  }, [graphData.nodes, height, width]);

  const nodeMap = useMemo(
    () => new Map(positionedNodes.map((node) => [node.id, node])),
    [positionedNodes]
  );

  return (
    <div
      data-testid="force-graph"
      className="h-full w-full overflow-hidden"
      style={{ backgroundColor: '#fff' }}
    >
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {links.map((link, index) => {
          const source = nodeMap.get(getNodeId(link.source));
          const target = nodeMap.get(getNodeId(link.target));

          if (!source || !target) {
            return null;
          }

          return (
            <line
              key={`link-${index}`}
              x1={source.x as number}
              y1={source.y as number}
              x2={target.x as number}
              y2={target.y as number}
              stroke={linkColor?.(link) ?? 'rgba(100, 100, 100, 0.35)'}
              strokeWidth={linkWidth?.(link) ?? 1}
            />
          );
        })}

        {positionedNodes.map((node) => {
          const label =
            typeof nodeLabel === 'function'
              ? nodeLabel(node)
              : typeof nodeLabel === 'string'
                ? String((node as Record<string, unknown>)[nodeLabel] ?? node.name ?? node.label ?? node.id)
                : String(node.name ?? node.label ?? node.id);
          const radius = Math.max(6, Math.min(24, Number(nodeVal?.(node) ?? node.size ?? 8)));

          return (
            <g
              key={node.id}
              onClick={() => onNodeClick?.(node)}
              style={{ cursor: onNodeClick ? 'pointer' : 'default' }}
            >
              <circle
                cx={node.x as number}
                cy={node.y as number}
                r={radius}
                fill={nodeColor?.(node) ?? '#3b82f6'}
                opacity={Math.max(0.4, Math.min(1, zoomLevel))}
              />
              <text
                x={(node.x as number) + radius + 4}
                y={(node.y as number) + 4}
                fontSize="12"
                fill="#374151"
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
});

export default ForceGraph2D;
