/**
 * Graph Virtualization Utilities
 * 
 * Provides level-of-detail rendering and virtualization for large graphs (>1000 nodes)
 * Ensures rendering completes within 5 seconds
 * 
 * Requirements: 1.8, 3.7
 */

export interface VirtualizedNode {
  id: string;
  name: string;
  type: string;
  size: number;
  x?: number;
  y?: number;
  visible: boolean;
  lod: 'high' | 'medium' | 'low';
  [key: string]: any;
}

export interface VirtualizedLink {
  source: string | VirtualizedNode;
  target: string | VirtualizedNode;
  visible: boolean;
  [key: string]: any;
}

export interface ViewportBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export interface VirtualizationConfig {
  nodeThreshold: number; // Threshold for enabling virtualization
  viewportPadding: number; // Extra space around viewport
  lodDistances: {
    high: number; // Distance for high detail
    medium: number; // Distance for medium detail
    low: number; // Distance for low detail
  };
}

const DEFAULT_CONFIG: VirtualizationConfig = {
  nodeThreshold: 1000,
  viewportPadding: 200,
  lodDistances: {
    high: 500,
    medium: 1000,
    low: 2000
  }
};

/**
 * Determines if virtualization should be enabled based on graph size
 */
export function shouldEnableVirtualization(
  nodeCount: number,
  config: VirtualizationConfig = DEFAULT_CONFIG
): boolean {
  return nodeCount > config.nodeThreshold;
}

/**
 * Calculates viewport bounds based on camera position and zoom
 */
export function calculateViewportBounds(
  cameraX: number,
  cameraY: number,
  zoom: number,
  width: number,
  height: number,
  padding: number = DEFAULT_CONFIG.viewportPadding
): ViewportBounds {
  const halfWidth = (width / zoom) / 2 + padding;
  const halfHeight = (height / zoom) / 2 + padding;

  return {
    minX: cameraX - halfWidth,
    maxX: cameraX + halfWidth,
    minY: cameraY - halfHeight,
    maxY: cameraY + halfHeight
  };
}

/**
 * Checks if a node is within the viewport bounds
 */
export function isNodeInViewport(
  node: VirtualizedNode,
  bounds: ViewportBounds
): boolean {
  if (node.x === undefined || node.y === undefined) return false;

  return (
    node.x >= bounds.minX &&
    node.x <= bounds.maxX &&
    node.y >= bounds.minY &&
    node.y <= bounds.maxY
  );
}

/**
 * Calculates distance from camera center to node
 */
export function calculateNodeDistance(
  node: VirtualizedNode,
  cameraX: number,
  cameraY: number
): number {
  if (node.x === undefined || node.y === undefined) return Infinity;

  const dx = node.x - cameraX;
  const dy = node.y - cameraY;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Determines level of detail for a node based on distance from camera
 */
export function calculateNodeLOD(
  distance: number,
  config: VirtualizationConfig = DEFAULT_CONFIG
): 'high' | 'medium' | 'low' {
  if (distance < config.lodDistances.high) return 'high';
  if (distance < config.lodDistances.medium) return 'medium';
  return 'low';
}

/**
 * Virtualizes nodes based on viewport and LOD
 */
export function virtualizeNodes<T extends VirtualizedNode>(
  nodes: T[],
  cameraX: number,
  cameraY: number,
  zoom: number,
  width: number,
  height: number,
  config: VirtualizationConfig = DEFAULT_CONFIG
): T[] {
  // If below threshold, return all nodes
  if (!shouldEnableVirtualization(nodes.length, config)) {
    return nodes.map(node => ({
      ...node,
      visible: true,
      lod: 'high' as const
    }));
  }

  const bounds = calculateViewportBounds(cameraX, cameraY, zoom, width, height, config.viewportPadding);

  return nodes.map(node => {
    const inViewport = isNodeInViewport(node, bounds);
    const distance = calculateNodeDistance(node, cameraX, cameraY);
    const lod = calculateNodeLOD(distance, config);

    return {
      ...node,
      visible: inViewport,
      lod
    };
  });
}

/**
 * Virtualizes links based on node visibility
 */
export function virtualizeLinks<T extends VirtualizedLink>(
  links: T[],
  visibleNodeIds: Set<string>
): T[] {
  return links.map(link => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target.id;

    const visible = visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId);

    return {
      ...link,
      visible
    };
  });
}

/**
 * Clusters nodes for simplified rendering at low LOD
 */
export interface NodeCluster {
  id: string;
  nodes: string[];
  x: number;
  y: number;
  size: number;
  type: string;
}

export function clusterNodes(
  nodes: VirtualizedNode[],
  clusterDistance: number = 100
): NodeCluster[] {
  const clusters: NodeCluster[] = [];
  const processed = new Set<string>();

  nodes.forEach(node => {
    if (processed.has(node.id) || !node.x || !node.y) return;

    // Find nearby nodes
    const nearbyNodes = nodes.filter(other => {
      if (processed.has(other.id) || !other.x || !other.y) return false;
      
      const dx = node.x! - other.x!;
      const dy = node.y! - other.y!;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      return distance < clusterDistance;
    });

    if (nearbyNodes.length >= 2) {
      // Create cluster
      const clusterNodes = nearbyNodes.map(n => n.id);
      const avgX = nearbyNodes.reduce((sum, n) => sum + (n.x || 0), 0) / nearbyNodes.length;
      const avgY = nearbyNodes.reduce((sum, n) => sum + (n.y || 0), 0) / nearbyNodes.length;
      const totalSize = nearbyNodes.reduce((sum, n) => sum + n.size, 0);

      clusters.push({
        id: `cluster-${clusters.length}`,
        nodes: clusterNodes,
        x: avgX,
        y: avgY,
        size: totalSize,
        type: 'cluster'
      });

      nearbyNodes.forEach(n => processed.add(n.id));
    }
  });

  return clusters;
}

/**
 * Simplifies graph for performance by removing low-importance nodes
 */
export function simplifyGraph<T extends VirtualizedNode>(
  nodes: T[],
  links: VirtualizedLink[],
  maxNodes: number = 500
): { nodes: T[]; links: VirtualizedLink[] } {
  if (nodes.length <= maxNodes) {
    return { nodes, links };
  }

  // Calculate node importance (degree centrality)
  const nodeDegrees = new Map<string, number>();
  nodes.forEach(node => nodeDegrees.set(node.id, 0));

  links.forEach(link => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target.id;

    nodeDegrees.set(sourceId, (nodeDegrees.get(sourceId) || 0) + 1);
    nodeDegrees.set(targetId, (nodeDegrees.get(targetId) || 0) + 1);
  });

  // Sort nodes by importance
  const sortedNodes = [...nodes].sort((a, b) => {
    const degreeA = nodeDegrees.get(a.id) || 0;
    const degreeB = nodeDegrees.get(b.id) || 0;
    return degreeB - degreeA;
  });

  // Keep top N nodes
  const keptNodes = sortedNodes.slice(0, maxNodes);
  const keptNodeIds = new Set(keptNodes.map(n => n.id));

  // Filter links to only include kept nodes
  const keptLinks = links.filter(link => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target.id;
    return keptNodeIds.has(sourceId) && keptNodeIds.has(targetId);
  });

  return {
    nodes: keptNodes,
    links: keptLinks
  };
}

/**
 * Performance monitoring for rendering
 */
export class RenderPerformanceMonitor {
  private startTime: number = 0;
  private frameCount: number = 0;
  private fps: number = 0;
  private lastFpsUpdate: number = 0;

  startFrame() {
    this.startTime = performance.now();
  }

  endFrame() {
    const endTime = performance.now();
    const frameDuration = endTime - this.startTime;

    this.frameCount++;

    // Update FPS every second
    if (endTime - this.lastFpsUpdate >= 1000) {
      this.fps = this.frameCount;
      this.frameCount = 0;
      this.lastFpsUpdate = endTime;
    }

    return {
      frameDuration,
      fps: this.fps
    };
  }

  getFPS(): number {
    return this.fps;
  }

  isPerformanceGood(): boolean {
    return this.fps >= 30; // Target 30 FPS minimum
  }
}

/**
 * Adaptive LOD controller that adjusts quality based on performance
 */
export class AdaptiveLODController {
  private monitor: RenderPerformanceMonitor;
  private config: VirtualizationConfig;
  private performanceHistory: number[] = [];
  private readonly historySize = 10;

  constructor(config: VirtualizationConfig = DEFAULT_CONFIG) {
    this.monitor = new RenderPerformanceMonitor();
    this.config = { ...config };
  }

  startFrame() {
    this.monitor.startFrame();
  }

  endFrame() {
    const metrics = this.monitor.endFrame();
    
    // Track performance history
    this.performanceHistory.push(metrics.fps);
    if (this.performanceHistory.length > this.historySize) {
      this.performanceHistory.shift();
    }

    // Adjust LOD distances based on performance
    this.adjustLODDistances();

    return metrics;
  }

  private adjustLODDistances() {
    if (this.performanceHistory.length < this.historySize) return;

    const avgFPS = this.performanceHistory.reduce((a, b) => a + b, 0) / this.performanceHistory.length;

    if (avgFPS < 20) {
      // Performance is poor, reduce LOD distances
      this.config.lodDistances.high *= 0.9;
      this.config.lodDistances.medium *= 0.9;
      this.config.lodDistances.low *= 0.9;
    } else if (avgFPS > 50) {
      // Performance is good, increase LOD distances
      this.config.lodDistances.high *= 1.05;
      this.config.lodDistances.medium *= 1.05;
      this.config.lodDistances.low *= 1.05;
    }

    // Clamp values
    this.config.lodDistances.high = Math.max(200, Math.min(1000, this.config.lodDistances.high));
    this.config.lodDistances.medium = Math.max(500, Math.min(2000, this.config.lodDistances.medium));
    this.config.lodDistances.low = Math.max(1000, Math.min(4000, this.config.lodDistances.low));
  }

  getConfig(): VirtualizationConfig {
    return { ...this.config };
  }

  getFPS(): number {
    return this.monitor.getFPS();
  }
}
