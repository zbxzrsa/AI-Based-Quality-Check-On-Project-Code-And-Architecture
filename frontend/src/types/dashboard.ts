/**
 * Dashboard Types
 * 
 * Type definitions for custom dashboard functionality
 */

/**
 * User interface (simplified for dashboard context)
 */
export interface User {
  id: string;
  name: string;
  email: string;
}

/**
 * Time range configuration
 */
export interface TimeRange {
  type: 'relative' | 'absolute';
  // relative
  value?: number;
  unit?: 'minute' | 'hour' | 'day' | 'week' | 'month';
  // absolute
  start?: Date;
  end?: Date;
}

/**
 * Widget position and size in grid
 */
export interface WidgetPosition {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Widget configuration
 */
export interface Widget {
  id: string;
  metricId: string;
  position: WidgetPosition;
  chartType: 'line' | 'bar' | 'pie' | 'gauge' | 'number';
  options: Record<string, any>;
}

/**
 * Dashboard layout configuration
 */
export interface DashboardLayout {
  columns: number;
  widgets: Widget[];
}

/**
 * Custom dashboard model
 */
export interface CustomDashboard {
  id: string;
  name: string;
  description?: string;
  owner: User;
  metrics: string[]; // MetricDefinition IDs
  layout: DashboardLayout;
  timeRange: TimeRange;
  refreshInterval: number; // seconds
  shared: boolean;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Dashboard creation/edit form data
 */
export interface DashboardFormData {
  name: string;
  description?: string;
  metrics: string[];
  timeRange: TimeRange;
  refreshInterval: number;
  shared: boolean;
}
