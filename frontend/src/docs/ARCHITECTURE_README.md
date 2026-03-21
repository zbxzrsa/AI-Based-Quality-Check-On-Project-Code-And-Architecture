# Architecture Visualization Component

## Overview

The Architecture component provides a graph-based visualization of system architecture, displaying components and their dependencies as an interactive node-edge graph. It uses ReactFlow for rendering and supports hierarchical component structures with performance metrics.

## Features

- **Node-based Graph Rendering**: Uses ReactFlow to render components as interactive nodes
- **Dependency Visualization**: Shows relationships between components as directed edges
- **Performance Metrics Display**: Shows response time, error rate, and throughput on each node (Requirement 4.3)
- **Health Status Indicators**: Color-coded health status indicator based on metrics
- **Interactive Node Expansion**: Click nodes with children to expand/collapse them (Requirement 4.2)
- **Expansion State Indicators**: Visual arrows (▶/▼) show expansion state
- **Multiple Node Types**: Supports service, component, module, database, and external types
- **Visual Legend**: Color-coded legend for different node types
- **Zoom and Pan**: Built-in controls for navigation
- **MiniMap**: Overview map for large architectures

## Usage

### Basic Usage

```tsx
import Architecture from '@/pages/Architecture';

function MyPage() {
  return <Architecture />;
}
```

### With Custom Data

```tsx
import Architecture, { ArchitectureNode } from '@/pages/Architecture';

const architectureData: ArchitectureNode = {
  id: 'root',
  name: 'My Application',
  type: 'service',
  children: [
    {
      id: 'frontend',
      name: 'Frontend',
      type: 'component',
      children: [],
      dependencies: ['api'],
      metrics: {
        responseTime: 120,
        errorRate: 0.5,
        throughput: 150,
      },
    },
    {
      id: 'api',
      name: 'API Gateway',
      type: 'service',
      children: [],
      dependencies: ['database'],
      metrics: {
        responseTime: 45,
        errorRate: 0.2,
        throughput: 500,
      },
    },
    {
      id: 'database',
      name: 'PostgreSQL',
      type: 'database',
      children: [],
      dependencies: [],
      metrics: {
        responseTime: 15,
        errorRate: 0.05,
        throughput: 1000,
      },
    },
  ],
  dependencies: [],
};

function MyPage() {
  return <Architecture data={architectureData} />;
}
```

### With Event Handlers

```tsx
import Architecture, { ArchitectureNode } from '@/pages/Architecture';

function MyPage() {
  const handleNodeClick = (node: ArchitectureNode) => {
    console.log('Node clicked:', node.name);
    // Handle node click - show details, navigate, etc.
  };

  const handleExport = (format: 'png' | 'svg') => {
    console.log('Export as:', format);
    // Implement export functionality
  };

  return (
    <Architecture
      data={architectureData}
      onNodeClick={handleNodeClick}
      onExport={handleExport}
    />
  );
}
```

## Data Model

### ArchitectureNode

```typescript
interface ArchitectureNode {
  id: string;                    // Unique identifier
  name: string;                  // Display name
  type: 'service' | 'component' | 'module' | 'database' | 'external';
  description?: string;          // Optional description
  children: ArchitectureNode[];  // Child components
  dependencies: string[];        // IDs of dependent nodes
  metrics?: {
    responseTime: number;        // Milliseconds
    errorRate: number;           // Percentage
    throughput: number;          // Requests per second
  };
  position?: {
    x: number;
    y: number;
  };
}
```

## Node Types and Colors

- **Service** (Blue): Backend services and APIs
- **Component** (Green): Frontend components and modules
- **Module** (Purple): Shared modules and libraries
- **Database** (Orange): Databases and data stores
- **External** (Gray): External services and integrations

## Health Status

The component automatically calculates health status based on metrics:

- **Healthy** (Green): Error rate ≤ 1%, Response time ≤ 1000ms
- **Warning** (Yellow): Error rate 1-5% or Response time > 1000ms
- **Critical** (Red): Error rate > 5%
- **Unknown** (Gray): No metrics available

## Interactions

### Node Expansion (Requirement 4.2)

- Click on nodes with children to expand/collapse them
- Expanded nodes show their child components in the graph
- Visual indicator (▶/▼) shows expansion state
- "Click to expand" / "Click to collapse" text provides clear feedback
- Expansion state is maintained during graph interactions

### Dependency Path Highlighting (Requirement 4.4)

- Click on any node to select it and highlight all dependency paths
- **Highlighted paths include:**
  - The selected node itself (with blue ring and glow effect)
  - All downstream dependencies (nodes that the selected node depends on)
  - All upstream dependencies (nodes that depend on the selected node)
  - All edges connecting these nodes (animated with blue color)
- **Visual indicators:**
  - Selected node: Blue ring with glow effect
  - Highlighted nodes: Light blue ring
  - Highlighted edges: Animated blue edges with increased width
  - Non-highlighted nodes/edges: Reduced opacity (30%)
- Click the same node again to deselect and clear highlighting
- A notification banner appears when a node is selected with a "Clear selection" button
- The algorithm traces both upstream and downstream dependencies recursively
- Handles circular dependencies correctly without infinite loops

### Performance Metrics Display (Requirement 4.3)

Each node displays comprehensive performance metrics:
- **Response Time**: Average response time in milliseconds
- **Error Rate**: Percentage of failed requests
- **Throughput**: Requests per second
- **Health Indicator**: Color-coded dot (green/yellow/red) shows overall health

### Navigation

- **Zoom**: Use mouse wheel or zoom controls
- **Pan**: Click and drag the canvas
- **Fit View**: Automatically adjusts zoom to show all nodes
- **MiniMap**: Click on minimap to navigate large graphs

## Integration with Existing Architecture Page

This component is designed to work alongside the existing architecture page at `/app/architecture/page.tsx`. The existing page provides:

- Branch selection and filtering
- Architecture statistics
- Branch health monitoring

This component provides:

- Detailed graph visualization
- Interactive node exploration
- Metrics display

You can integrate them by:

1. Using this component in the branch detail view (`/architecture/[branchId]`)
2. Passing branch-specific architecture data to this component
3. Handling node clicks to show detailed information

## Example Integration

```tsx
// In /app/architecture/[branchId]/page.tsx
import Architecture from '@/pages/Architecture';
import { useArchitectureData } from '@/hooks/useArchitecture';

export default function BranchArchitecturePage({ params }: { params: { branchId: string } }) {
  const { data, isLoading } = useArchitectureData(params.branchId);

  if (isLoading) return <LoadingState />;

  return (
    <MainLayout>
      <Architecture
        data={data}
        onNodeClick={(node) => {
          // Show node details in a modal or sidebar
        }}
      />
    </MainLayout>
  );
}
```

## Performance Considerations

- The component uses React.memo and useMemo for optimization
- Large graphs (100+ nodes) may impact performance
- Consider implementing virtualization for very large architectures
- Use the `fitView` prop to automatically adjust zoom level

## Testing

The component includes comprehensive unit tests covering:

- Basic rendering
- Data handling
- Node types
- Metrics display
- Dependencies
- Nested structures
- Event handlers

Run tests with:

```bash
npm test -- Architecture.test.tsx
```

## Requirements

This component satisfies requirements:
- ✅ 4.1: Displays system components and dependencies as a graph
- ✅ 4.2: Node click expands to show child components
- ✅ 4.3: Performance metrics displayed on component nodes
- ✅ 4.4: Highlights all dependency paths when component is selected
- Uses ReactFlow (similar to D3.js) for visualization
- Implements interactive node and edge rendering
- Supports the architecture data model from design document

## Future Enhancements

Planned features for subsequent tasks:

- **Task 8.6**: Export functionality (PNG/SVG)

## Dependencies

- `reactflow`: ^11.11.4 - Graph visualization library
- `react`: ^19.2.4 - React framework
- `lucide-react`: ^0.575.0 - Icons (if needed)

## Related Files

- `/src/pages/Architecture.tsx` - Main component
- `/src/pages/__tests__/Architecture.test.tsx` - Unit tests
- `/src/app/architecture/page.tsx` - Branch selection page
- `/src/components/architecture/architecture-graph.tsx` - Existing graph component
