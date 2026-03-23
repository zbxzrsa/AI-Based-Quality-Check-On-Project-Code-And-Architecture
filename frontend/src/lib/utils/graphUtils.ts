/**
 * Graph data transformation utilities
 */

export interface Neo4jNode {
  id: number | string;
  type: string;
  name: string;
  properties?: Record<string, any>;
}

export interface Neo4jEdge {
  source: number | string;
  target: number | string;
  type: string;
  weight?: number;
}

export interface GraphData {
  nodes: Neo4jNode[];
  links: Neo4jEdge[];
  metadata?: Record<string, any>;
}

/**
 * Transform Neo4j graph data to React Flow format
 */
export function transformToReactFlow(graphData: GraphData) {
  const nodes = graphData.nodes.map((node, index) => {
    // Calculate importance based on connections
    const inDegree = graphData.links.filter((link) => link.target === node.id).length;
    const outDegree = graphData.links.filter((link) => link.source === node.id).length;
    const importance = inDegree + outDegree;

    return {
      id: String(node.id),
      type: node.type.toLowerCase(),
      name: node.name,
      importance,
      metadata: node.properties,
    };
  });

  const edges = graphData.links.map((link) => ({
    source: String(link.source),
    target: String(link.target),
    type: link.type.toLowerCase(),
    weight: link.weight || 1,
  }));

  return { nodes, edges };
}

/**
 * Detect circular dependencies in a graph
 */
export function detectCircularDependencies(graphData: GraphData): string[][] {
  const adjacencyList = new Map<string, string[]>();
  
  // Build adjacency list
  graphData.nodes.forEach((node) => {
    adjacencyList.set(String(node.id), []);
  });
  
  graphData.links.forEach((link) => {
    const source = String(link.source);
    const target = String(link.target);
    const neighbors = adjacencyList.get(source) || [];
    neighbors.push(target);
    adjacencyList.set(source, neighbors);
  });

  const cycles: string[][] = [];
  const visited = new Set<string>();
  const recursionStack = new Set<string>();
  const currentPath: string[] = [];

  function dfs(nodeId: string): boolean {
    visited.add(nodeId);
    recursionStack.add(nodeId);
    currentPath.push(nodeId);

    const neighbors = adjacencyList.get(nodeId) || [];
    
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) {
          return true;
        }
      } else if (recursionStack.has(neighbor)) {
        // Found a cycle
        const cycleStart = currentPath.indexOf(neighbor);
        const cycle = currentPath.slice(cycleStart);
        cycles.push([...cycle, neighbor]); // Complete the cycle
      }
    }

    recursionStack.delete(nodeId);
    currentPath.pop();
    return false;
  }

  // Run DFS from each unvisited node
  graphData.nodes.forEach((node) => {
    if (!visited.has(String(node.id))) {
      dfs(String(node.id));
    }
  });

  return cycles;
}

/**
 * Calculate node centrality metrics
 */
export function calculateCentrality(graphData: GraphData) {
  const nodeMetrics = new Map<string, { inDegree: number; outDegree: number; betweenness: number }>();

  // Initialize
  graphData.nodes.forEach((node) => {
    nodeMetrics.set(String(node.id), { inDegree: 0, outDegree: 0, betweenness: 0 });
  });

  // Calculate degree centrality
  graphData.links.forEach((link) => {
    const source = String(link.source);
    const target = String(link.target);

    const sourceMetrics = nodeMetrics.get(source)!;
    sourceMetrics.outDegree++;

    const targetMetrics = nodeMetrics.get(target)!;
    targetMetrics.inDegree++;
  });

  return nodeMetrics;
}

/**
 * Build hierarchical tree structure from flat graph data
 */
export function buildHierarchyTree(graphData: GraphData, rootId?: string) {
  const nodeMap = new Map(graphData.nodes.map((node) => [String(node.id), { ...node, children: [] as any[] }]));

  // Find containment relationships (CONTAINS edges)
  graphData.links
    .filter((link) => link.type.toLowerCase() === 'contains')
    .forEach((link) => {
      const parent = nodeMap.get(String(link.source));
      const child = nodeMap.get(String(link.target));

      if (parent && child) {
        parent.children.push(child);
      }
    });

  // Find root nodes (nodes with no incoming CONTAINS edges)
  const childIds = new Set(
    graphData.links.filter((l) => l.type.toLowerCase() === 'contains').map((l) => String(l.target))
  );

  const roots = graphData.nodes.filter((node) => !childIds.has(String(node.id))).map((node) => nodeMap.get(String(node.id))!);

  // If rootId specified, return that subtree
  if (rootId) {
    return nodeMap.get(rootId) || null;
  }

  // Return all roots (forest)
  return roots.length === 1 ? roots[0] : { id: 'root', name: 'Root', type: 'root', children: roots };
}

/**
 * Filter graph by node types
 */
export function filterGraphByType(graphData: GraphData, types: string[]): GraphData {
  const typesSet = new Set(types.map((t) => t.toLowerCase()));

  const filteredNodes = graphData.nodes.filter((node) => typesSet.has(node.type.toLowerCase()));
  const nodeIds = new Set(filteredNodes.map((n) => String(n.id)));

  const filteredLinks = graphData.links.filter(
    (link) => nodeIds.has(String(link.source)) && nodeIds.has(String(link.target))
  );

  return {
    nodes: filteredNodes,
    links: filteredLinks,
    metadata: graphData.metadata,
  };
}

/**
 * Search nodes by name
 */
export function searchNodes(graphData: GraphData, query: string): Neo4jNode[] {
  const lowerQuery = query.toLowerCase();
  return graphData.nodes.filter((node) => node.name.toLowerCase().includes(lowerQuery));
}
