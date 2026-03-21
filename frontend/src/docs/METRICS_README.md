# Metrics Component

## Overview

The Metrics component provides a comprehensive dashboard for displaying metric time series trends with day/week/month views. It integrates Recharts for data visualization and supports real-time metric monitoring.

## Features

### Core Functionality

1. **Time Series Visualization**
   - Display metrics over time using line charts
   - Support for multiple metrics on the same chart
   - Interactive tooltips and legends

2. **Time Range Selection**
   - Day view: 24 hourly data points
   - Week view: 7 daily data points
   - Month view: 30 daily data points

3. **Metric Summary Cards**
   - Display latest values for each metric
   - Color-coded by metric type
   - Shows unit of measurement

4. **Loading and Error States**
   - Animated loading spinner
   - User-friendly error messages
   - Graceful degradation

## Usage

### Basic Usage

```tsx
import Metrics from '@/pages/Metrics';

function App() {
  return <Metrics />;
}
```

### With Custom Initial Time Range

```tsx
import Metrics from '@/pages/Metrics';

function App() {
  return <Metrics initialTimeRange="day" />;
}
```

### With Time Range Change Callback

```tsx
import Metrics from '@/pages/Metrics';

function App() {
  const handleTimeRangeChange = (range: 'day' | 'week' | 'month') => {
    console.log('Time range changed to:', range);
  };

  return <Metrics onTimeRangeChange={handleTimeRangeChange} />;
}
```

## Component Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `initialTimeRange` | `'day' \| 'week' \| 'month'` | `'week'` | Initial time range for the view |
| `onTimeRangeChange` | `(range: TimeRange) => void` | `undefined` | Callback when time range changes |

## Data Model

### MetricDefinition

```typescript
interface MetricDefinition {
  id: string;           // Unique identifier
  name: string;         // Display name
  unit: string;         // Unit of measurement (e.g., 'ms', '%', 'score')
  color: string;        // Chart line color (hex)
}
```

### MetricDataPoint

```typescript
interface MetricDataPoint {
  timestamp: Date;      // Data point timestamp
  value: number;        // Metric value
  label?: string;       // Optional display label
}
```

## Chart Integration

The component uses **Recharts** for data visualization:

- `LineChart`: Main chart component
- `Line`: Individual metric lines
- `XAxis`: Time axis
- `YAxis`: Value axis
- `CartesianGrid`: Background grid
- `Tooltip`: Interactive tooltips
- `Legend`: Metric legend
- `ResponsiveContainer`: Responsive sizing

## Styling

The component uses Tailwind CSS for styling:

- Responsive grid layout
- Card-based design
- Color-coded metrics
- Hover effects on buttons
- Shadow and border styling

## Data Loading

Currently uses mock data generation. In production:

1. Replace `generateMockData` with API calls
2. Use the `ApiClient` service for data fetching
3. Implement proper error handling
4. Add retry logic for failed requests

### Example API Integration

```typescript
const loadData = async () => {
  setLoading(true);
  setError(null);
  
  try {
    const response = await apiClient.get(`/metrics?range=${timeRange}`);
    setMetricsData(response.data);
  } catch (err) {
    setError(err instanceof Error ? err : new Error('Failed to load metrics'));
  } finally {
    setLoading(false);
  }
};
```

## Testing

The component includes comprehensive unit tests:

- Loading state rendering
- Error state rendering
- Time range selection
- Data reloading on range change
- Callback invocation
- Chart rendering
- Summary card display

Run tests:

```bash
npm test -- Metrics.test.tsx
```

## Requirements Satisfied

- **Requirement 6.3**: Display metric time series trends with day/week/month views
  - ✅ Implemented time range selector
  - ✅ Integrated Recharts for visualization
  - ✅ Display trends over time
  - ✅ Support multiple time ranges

## Future Enhancements

1. **Custom Dashboard Support** (Requirement 6.1)
   - Allow users to create custom metric dashboards
   - Save and load dashboard configurations
   - Drag-and-drop widget layout

2. **Data Export** (Requirement 6.2)
   - Export metrics to CSV format
   - Export metrics to JSON format
   - Ensure data consistency

3. **Multi-Metric Comparison** (Requirement 6.4)
   - Select multiple metrics for comparison
   - Display on same chart with different scales
   - Toggle metric visibility

4. **Threshold Alerts** (Requirement 6.5)
   - Configure warning thresholds
   - Display alert indicators
   - Visual warnings for exceeded thresholds

5. **Real-time Updates**
   - WebSocket integration for live data
   - Auto-refresh at configurable intervals
   - Smooth data transitions

6. **Advanced Filtering**
   - Filter by metric tags
   - Search metrics by name
   - Group metrics by category

## Performance Considerations

- Uses `ResponsiveContainer` for efficient resizing
- Implements loading states to prevent UI blocking
- Memoization opportunities for expensive calculations
- Lazy loading for large datasets

## Accessibility

- Semantic HTML structure
- Keyboard navigation support
- ARIA labels for interactive elements
- Color contrast compliance
- Screen reader friendly

## Browser Compatibility

Tested and compatible with:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Dependencies

- React 18+
- Recharts 3.6.0+
- TypeScript 5+
- Tailwind CSS 3+

## Related Components

- `LineChart`: Reusable line chart component
- `GaugeChart`: Gauge visualization
- `BarChart`: Bar chart component
- `AreaChart`: Area chart component

## Architecture

```
Metrics Component
├── State Management
│   ├── timeRange (current view)
│   ├── loading (loading state)
│   ├── error (error state)
│   └── metricsData (chart data)
├── Data Loading
│   ├── useEffect hook
│   ├── generateMockData (temp)
│   └── API integration (future)
├── UI Components
│   ├── Header
│   ├── Time Range Selector
│   ├── Chart Container
│   └── Summary Cards
└── Chart Integration
    └── Recharts components
```

## Contributing

When modifying this component:

1. Update tests to cover new functionality
2. Maintain TypeScript type safety
3. Follow existing code style
4. Update this README with changes
5. Ensure accessibility compliance
6. Test across different time ranges
