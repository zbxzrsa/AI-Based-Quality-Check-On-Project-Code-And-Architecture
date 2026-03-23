import React, { useState, useEffect } from 'react';
import { useAsyncAction } from '@/hooks/useAsyncAction';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { DashboardModal } from '../components/DashboardModal';
import { DashboardGrid } from '../components/DashboardGrid';
import { DashboardService } from '../services/DashboardService';
import { CustomDashboard, DashboardFormData, Widget } from '../types/dashboard';
import '../styles/responsive.css';

/**
 * Time range options for metric views
 */
type TimeRange = 'day' | 'week' | 'month';

/**
 * Metric data point interface
 */
interface MetricDataPoint {
  timestamp: Date;
  value: number;
  label?: string;
}

/**
 * Metric definition interface
 */
interface MetricDefinition {
  id: string;
  name: string;
  unit: string;
  color: string;
  threshold?: {
    warning: number;
    critical: number;
  };
}

/**
 * Alert level type
 */
type AlertLevel = 'normal' | 'warning' | 'critical';

/**
 * Props for the Metrics component
 */
interface MetricsProps {
  /**
   * Optional time range for initial view
   */
  initialTimeRange?: TimeRange;
  
  /**
   * Optional callback when time range changes
   */
  onTimeRangeChange?: (range: TimeRange) => void;
}

/**
 * Metrics Page Component
 * 
 * Displays metric time series trends with day/week/month views.
 * Integrates Recharts for data visualization.
 * Supports custom dashboard creation and management.
 * 
 * Requirements: 
 * - 6.1: Allow users to create and save custom dashboard configurations
 * - 6.3: Display metric time series trends with day/week/month views
 */
const Metrics: React.FC<MetricsProps> = ({ 
  initialTimeRange = 'week',
  onTimeRangeChange 
}) => {
  // Available metrics - defined first so it can be used in state initialization
  const metrics: MetricDefinition[] = [
    { 
      id: 'performance', 
      name: 'Performance Score', 
      unit: 'score', 
      color: '#3b82f6',
      threshold: {
        warning: 70,
        critical: 50
      }
    },
    { 
      id: 'errorRate', 
      name: 'Error Rate', 
      unit: '%', 
      color: '#ef4444',
      threshold: {
        warning: 3,
        critical: 5
      }
    },
    { 
      id: 'responseTime', 
      name: 'Response Time', 
      unit: 'ms', 
      color: '#22c55e',
      threshold: {
        warning: 150,
        critical: 200
      }
    },
  ];

  const [timeRange, setTimeRange] = useState<TimeRange>(initialTimeRange);
  const { execute, loading, error } = useAsyncAction<any[]>();
  const [metricsData, setMetricsData] = useState<any[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(
    metrics.map(m => m.id) // Initially all metrics are selected
  );

  // Custom dashboard state
  const [dashboards, setDashboards] = useState<CustomDashboard[]>([]);
  const [activeDashboard, setActiveDashboard] = useState<CustomDashboard | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [editingDashboard, setEditingDashboard] = useState<CustomDashboard | null>(null);

  // Mock current user (in production, this would come from auth context)
  const currentUser = {
    id: 'user_1',
    name: 'John Doe',
    email: 'john@example.com'
  };

  /**
   * Determine alert level based on metric value and thresholds
   */
  const getAlertLevel = (metric: MetricDefinition, value: number): AlertLevel => {
    if (!metric.threshold) {
      return 'normal';
    }

    // For metrics where lower is better (like errorRate and responseTime)
    const isLowerBetter = metric.id === 'errorRate' || metric.id === 'responseTime';

    if (isLowerBetter) {
      if (value >= metric.threshold.critical) {
        return 'critical';
      } else if (value >= metric.threshold.warning) {
        return 'warning';
      }
    } else {
      // For metrics where higher is better (like performance)
      if (value <= metric.threshold.critical) {
        return 'critical';
      } else if (value <= metric.threshold.warning) {
        return 'warning';
      }
    }

    return 'normal';
  };

  /**
   * Get alert indicator icon and color
   */
  const getAlertIndicator = (alertLevel: AlertLevel) => {
    switch (alertLevel) {
      case 'critical':
        return {
          icon: (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          ),
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          label: 'Critical'
        };
      case 'warning':
        return {
          icon: (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          ),
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          label: 'Warning'
        };
      default:
        return null;
    }
  };

  /**
   * Handle time range change
   */
  const handleTimeRangeChange = (range: TimeRange) => {
    setTimeRange(range);
    if (onTimeRangeChange) {
      onTimeRangeChange(range);
    }
  };

  /**
   * Handle metric selection toggle
   */
  const handleMetricToggle = (metricId: string) => {
    setSelectedMetrics(prev => {
      if (prev.includes(metricId)) {
        // Don't allow deselecting all metrics
        if (prev.length === 1) {
          return prev;
        }
        return prev.filter(id => id !== metricId);
      } else {
        return [...prev, metricId];
      }
    });
  };

  /**
   * Select all metrics
   */
  const handleSelectAllMetrics = () => {
    setSelectedMetrics(metrics.map(m => m.id));
  };

  /**
   * Deselect all metrics except one
   */
  const handleDeselectAllMetrics = () => {
    if (selectedMetrics.length > 0) {
      setSelectedMetrics([selectedMetrics[0]]);
    } else {
      setSelectedMetrics([metrics[0].id]);
    }
  };

  /**
   * Generate mock data based on time range
   * In production, this would fetch from an API
   */
  const generateMockData = (range: TimeRange): any[] => {
    const now = new Date();
    const data: any[] = [];
    
    let points: number;
    let interval: number; // in hours
    let labelFormat: (date: Date) => string;

    switch (range) {
      case 'day':
        points = 24;
        interval = 1;
        labelFormat = (date) => `${date.getHours()}:00`;
        break;
      case 'week':
        points = 7;
        interval = 24;
        labelFormat = (date) => date.toLocaleDateString('en-US', { weekday: 'short' });
        break;
      case 'month':
        points = 30;
        interval = 24;
        labelFormat = (date) => date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        break;
    }

    for (let i = points - 1; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * interval * 60 * 60 * 1000);
      data.push({
        timestamp: timestamp.toISOString(),
        label: labelFormat(timestamp),
        performance: 75 + Math.random() * 20,
        errorRate: Math.random() * 5,
        responseTime: 100 + Math.random() * 100,
      });
    }

    return data;
  };

  /**
   * Load metrics data
   */
  useEffect(() => {
    const loadData = async () => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return generateMockData(timeRange);
    };

    execute(loadData).then(data => {
      if (data) {
        setMetricsData(data);
      }
    });
  }, [timeRange, execute]);

  /**
   * Load custom dashboards
   */
  useEffect(() => {
    const loadDashboards = () => {
      const userDashboards = DashboardService.getDashboards(currentUser.id);
      setDashboards(userDashboards);
    };

    loadDashboards();
  }, []);

  /**
   * Handle dashboard creation
   */
  const handleCreateDashboard = (formData: DashboardFormData) => {
    const newDashboard = DashboardService.saveDashboard(formData, currentUser);
    setDashboards([...dashboards, newDashboard]);
    setActiveDashboard(newDashboard);
  };

  /**
   * Handle dashboard update
   */
  const handleUpdateDashboard = (formData: DashboardFormData) => {
    if (!editingDashboard) return;

    const updated = DashboardService.updateDashboard(editingDashboard.id, formData);
    if (updated) {
      setDashboards(dashboards.map(d => d.id === updated.id ? updated : d));
      if (activeDashboard?.id === updated.id) {
        setActiveDashboard(updated);
      }
    }
  };

  /**
   * Handle dashboard deletion
   */
  const handleDeleteDashboard = (dashboardId: string) => {
    if (window.confirm('Are you sure you want to delete this dashboard?')) {
      DashboardService.deleteDashboard(dashboardId);
      setDashboards(dashboards.filter(d => d.id !== dashboardId));
      if (activeDashboard?.id === dashboardId) {
        setActiveDashboard(null);
      }
    }
  };

  /**
   * Handle layout change
   */
  const handleLayoutChange = (widgets: Widget[]) => {
    if (!activeDashboard) return;

    const updatedLayout = {
      ...activeDashboard.layout,
      widgets
    };

    DashboardService.updateLayout(activeDashboard.id, updatedLayout);
    setActiveDashboard({
      ...activeDashboard,
      layout: updatedLayout
    });
  };

  /**
   * Open create modal
   */
  const openCreateModal = () => {
    setModalMode('create');
    setEditingDashboard(null);
    setIsModalOpen(true);
  };

  /**
   * Open edit modal
   */
  const openEditModal = (dashboard: CustomDashboard) => {
    setModalMode('edit');
    setEditingDashboard(dashboard);
    setIsModalOpen(true);
  };

  /**
   * Export metrics data as CSV
   */
  const exportAsCSV = () => {
    if (metricsData.length === 0) {
      alert('No data to export');
      return;
    }

    // Get metric IDs to export
    const metricIds = activeDashboard 
      ? activeDashboard.metrics 
      : metrics.map(m => m.id);

    // Build CSV header
    const headers = ['Timestamp', 'Label'];
    metricIds.forEach(metricId => {
      const metric = metrics.find(m => m.id === metricId);
      if (metric) {
        headers.push(`${metric.name} (${metric.unit})`);
      }
    });

    // Build CSV rows
    const rows = metricsData.map(dataPoint => {
      const row = [dataPoint.timestamp, dataPoint.label];
      metricIds.forEach(metricId => {
        row.push(dataPoint[metricId]?.toFixed(2) || '0');
      });
      return row;
    });

    // Combine headers and rows
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    const filename = activeDashboard 
      ? `${activeDashboard.name.replace(/\s+/g, '_')}_metrics_${timeRange}.csv`
      : `metrics_${timeRange}.csv`;
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  /**
   * Export metrics data as JSON
   */
  const exportAsJSON = () => {
    if (metricsData.length === 0) {
      alert('No data to export');
      return;
    }

    // Get metric IDs to export
    const metricIds = activeDashboard 
      ? activeDashboard.metrics 
      : metrics.map(m => m.id);

    // Build export data with metric definitions
    const exportData = {
      exportDate: new Date().toISOString(),
      timeRange,
      dashboard: activeDashboard ? {
        id: activeDashboard.id,
        name: activeDashboard.name,
        description: activeDashboard.description
      } : null,
      metrics: metricIds.map(metricId => {
        const metric = metrics.find(m => m.id === metricId);
        return metric ? {
          id: metric.id,
          name: metric.name,
          unit: metric.unit
        } : null;
      }).filter(Boolean),
      data: metricsData.map(dataPoint => {
        const point: any = {
          timestamp: dataPoint.timestamp,
          label: dataPoint.label
        };
        metricIds.forEach(metricId => {
          point[metricId] = dataPoint[metricId];
        });
        return point;
      })
    };

    // Create and download file
    const jsonContent = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    const filename = activeDashboard 
      ? `${activeDashboard.name.replace(/\s+/g, '_')}_metrics_${timeRange}.json`
      : `metrics_${timeRange}.json`;
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  /**
   * Render widget content
   */
  const renderWidget = (widget: Widget) => {
    const metric = metrics.find(m => m.id === widget.metricId);
    if (!metric) return <div>Unknown metric</div>;

    const latestValue = metricsData.length > 0 
      ? metricsData[metricsData.length - 1][metric.id]
      : 0;

    const alertLevel = getAlertLevel(metric, latestValue);
    const alertIndicator = getAlertIndicator(alertLevel);

    if (widget.chartType === 'number') {
      return (
        <div className="flex flex-col items-center justify-center h-full">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            {metric.name}
          </h3>
          <div className="flex items-center gap-2">
            <p className="text-4xl font-bold" style={{ color: metric.color }}>
              {latestValue.toFixed(1)}
              <span className="text-xl ml-1">{metric.unit}</span>
            </p>
            {alertIndicator && (
              <div className={`${alertIndicator.color}`} title={`${alertIndicator.label} threshold exceeded`}>
                {alertIndicator.icon}
              </div>
            )}
          </div>
          {alertIndicator && (
            <div className={`mt-2 px-3 py-1 rounded-full text-xs font-medium ${alertIndicator.bgColor} ${alertIndicator.color} border ${alertIndicator.borderColor}`}>
              {alertIndicator.label}
            </div>
          )}
        </div>
      );
    }

    return (
      <div className="h-full">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-gray-700">{metric.name}</h3>
          {alertIndicator && (
            <div className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${alertIndicator.bgColor} ${alertIndicator.color} border ${alertIndicator.borderColor}`}>
              <span className="w-3 h-3">{alertIndicator.icon}</span>
              <span>{alertIndicator.label}</span>
            </div>
          )}
        </div>
        <ResponsiveContainer width="100%" height="85%">
          <LineChart data={metricsData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="label" style={{ fontSize: '10px' }} />
            <YAxis style={{ fontSize: '10px' }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey={metric.id}
              stroke={metric.color}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  };

  /**
   * Render loading state
   */
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading metrics...</p>
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-red-600">
          <p className="text-xl font-semibold mb-2">Error loading metrics</p>
          <p className="text-sm">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Metrics Dashboard</h1>
          <p className="text-gray-600">Monitor system performance and trends over time</p>
        </div>
        <div className="flex gap-2">
          {/* Export Buttons */}
          <div className="flex gap-2 mr-2">
            <button
              onClick={exportAsCSV}
              disabled={metricsData.length === 0}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2 disabled:bg-gray-300 disabled:cursor-not-allowed"
              title="Export as CSV"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              CSV
            </button>
            <button
              onClick={exportAsJSON}
              disabled={metricsData.length === 0}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2 disabled:bg-gray-300 disabled:cursor-not-allowed"
              title="Export as JSON"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              JSON
            </button>
          </div>
          <button
            onClick={openCreateModal}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Dashboard
          </button>
        </div>
      </div>

      {/* Dashboard Tabs */}
      {dashboards.length > 0 && (
        <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
          <button
            onClick={() => setActiveDashboard(null)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
              !activeDashboard
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Default View
          </button>
          {dashboards.map((dashboard) => (
            <div key={dashboard.id} className="flex items-center gap-1">
              <button
                onClick={() => setActiveDashboard(dashboard)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                  activeDashboard?.id === dashboard.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {dashboard.name}
              </button>
              {activeDashboard?.id === dashboard.id && (
                <div className="flex gap-1">
                  <button
                    onClick={() => openEditModal(dashboard)}
                    className="p-2 text-gray-600 hover:text-blue-600 transition-colors"
                    title="Edit dashboard"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDeleteDashboard(dashboard.id)}
                    className="p-2 text-gray-600 hover:text-red-600 transition-colors"
                    title="Delete dashboard"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Custom Dashboard View */}
      {activeDashboard ? (
        <div>
          <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-semibold text-blue-900">{activeDashboard.name}</h2>
                {activeDashboard.description && (
                  <p className="text-sm text-blue-700 mt-1">{activeDashboard.description}</p>
                )}
              </div>
              <div className="text-sm text-blue-600">
                Refresh: {activeDashboard.refreshInterval}s
              </div>
            </div>
          </div>

          <DashboardGrid
            widgets={activeDashboard.layout.widgets}
            columns={activeDashboard.layout.columns}
            onLayoutChange={handleLayoutChange}
            editable={false}
            renderWidget={renderWidget}
          />
        </div>
      ) : (
        <>
          {/* Time Range Selector */}
          <div className="mb-6 flex gap-2">
            <button
              onClick={() => handleTimeRangeChange('day')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                timeRange === 'day'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Day
            </button>
            <button
              onClick={() => handleTimeRangeChange('week')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                timeRange === 'week'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Week
            </button>
            <button
              onClick={() => handleTimeRangeChange('month')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                timeRange === 'month'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Month
            </button>
          </div>

          {/* Multi-Metric Selection UI */}
          <div className="mb-6 bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700">
                Select Metrics to Compare
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={handleSelectAllMetrics}
                  className="text-xs px-3 py-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                >
                  Select All
                </button>
                <button
                  onClick={handleDeselectAllMetrics}
                  className="text-xs px-3 py-1 text-gray-600 hover:bg-gray-50 rounded transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              {metrics.map((metric) => {
                const isSelected = selectedMetrics.includes(metric.id);
                return (
                  <button
                    key={metric.id}
                    onClick={() => handleMetricToggle(metric.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                      isSelected
                        ? 'bg-blue-50 border-2 border-blue-500 text-blue-700'
                        : 'bg-gray-50 border-2 border-gray-200 text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: metric.color }}
                    />
                    <span>{metric.name}</span>
                    {isSelected && (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-gray-500 mt-3">
              {selectedMetrics.length} metric{selectedMetrics.length !== 1 ? 's' : ''} selected
              {selectedMetrics.length > 1 && ' - comparing in the same chart'}
            </p>
          </div>

          {/* Metrics Chart */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">
              Metric Trends
              {selectedMetrics.length > 1 && (
                <span className="text-sm font-normal text-gray-500 ml-2">
                  (Comparing {selectedMetrics.length} metrics)
                </span>
              )}
            </h2>
            
            <ResponsiveContainer width="100%" height={400}>
              <LineChart
                data={metricsData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="label" 
                  stroke="#6b7280"
                  style={{ fontSize: '12px' }}
                />
                <YAxis 
                  stroke="#6b7280"
                  style={{ fontSize: '12px' }}
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    padding: '12px'
                  }}
                />
                <Legend 
                  wrapperStyle={{ paddingTop: '20px' }}
                />
                
                {/* Threshold reference lines - only show if single metric selected */}
                {selectedMetrics.length === 1 && (() => {
                  const metric = metrics.find(m => m.id === selectedMetrics[0]);
                  if (metric?.threshold) {
                    return (
                      <>
                        <ReferenceLine
                          y={metric.threshold.warning}
                          stroke="#eab308"
                          strokeDasharray="5 5"
                          label={{ value: 'Warning', position: 'right', fill: '#eab308', fontSize: 12 }}
                        />
                        <ReferenceLine
                          y={metric.threshold.critical}
                          stroke="#ef4444"
                          strokeDasharray="5 5"
                          label={{ value: 'Critical', position: 'right', fill: '#ef4444', fontSize: 12 }}
                        />
                      </>
                    );
                  }
                  return null;
                })()}

                {metrics
                  .filter(metric => selectedMetrics.includes(metric.id))
                  .map((metric) => (
                    <Line
                      key={metric.id}
                      type="monotone"
                      dataKey={metric.id}
                      name={metric.name}
                      stroke={metric.color}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  ))}
              </LineChart>
            </ResponsiveContainer>

            {/* Threshold Legend */}
            {selectedMetrics.length === 1 && (() => {
              const metric = metrics.find(m => m.id === selectedMetrics[0]);
              if (metric?.threshold) {
                return (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs font-medium text-gray-700 mb-2">Threshold Configuration:</p>
                    <div className="flex gap-4 text-xs">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-0.5 bg-yellow-500" style={{ borderTop: '2px dashed #eab308' }}></div>
                        <span className="text-gray-600">Warning: {metric.threshold.warning}{metric.unit}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-0.5 bg-red-500" style={{ borderTop: '2px dashed #ef4444' }}></div>
                        <span className="text-gray-600">Critical: {metric.threshold.critical}{metric.unit}</span>
                      </div>
                    </div>
                  </div>
                );
              }
              return null;
            })()}
          </div>

          {/* Metric Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
            {metrics
              .filter(metric => selectedMetrics.includes(metric.id))
              .map((metric) => {
                const latestValue = metricsData.length > 0 
                  ? metricsData[metricsData.length - 1][metric.id]
                  : 0;
                
                const alertLevel = getAlertLevel(metric, latestValue);
                const alertIndicator = getAlertIndicator(alertLevel);

                return (
                  <div 
                    key={metric.id} 
                    className={`bg-white rounded-lg shadow p-6 ${
                      alertIndicator ? `border-2 ${alertIndicator.borderColor}` : ''
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-600">
                        {metric.name}
                      </h3>
                      {alertIndicator && (
                        <div className={`${alertIndicator.color}`} title={`${alertIndicator.label} threshold exceeded`}>
                          {alertIndicator.icon}
                        </div>
                      )}
                    </div>
                    <p className="text-3xl font-bold" style={{ color: metric.color }}>
                      {latestValue.toFixed(1)}
                      <span className="text-lg ml-1">{metric.unit}</span>
                    </p>
                    <div className="flex items-center justify-between mt-2">
                      <p className="text-sm text-gray-500">
                        Latest value from {timeRange} view
                      </p>
                      {alertIndicator && (
                        <span className={`text-xs font-medium px-2 py-1 rounded ${alertIndicator.bgColor} ${alertIndicator.color}`}>
                          {alertIndicator.label}
                        </span>
                      )}
                    </div>
                    {metric.threshold && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <p className="text-xs text-gray-500 mb-1">Thresholds:</p>
                        <div className="flex gap-3 text-xs">
                          <span className="text-yellow-600">
                            ⚠ Warning: {metric.threshold.warning}{metric.unit}
                          </span>
                          <span className="text-red-600">
                            ✕ Critical: {metric.threshold.critical}{metric.unit}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </>
      )}

      {/* Dashboard Modal */}
      <DashboardModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={modalMode === 'create' ? handleCreateDashboard : handleUpdateDashboard}
        initialData={editingDashboard ? {
          name: editingDashboard.name,
          description: editingDashboard.description,
          metrics: editingDashboard.metrics,
          timeRange: editingDashboard.timeRange,
          refreshInterval: editingDashboard.refreshInterval,
          shared: editingDashboard.shared
        } : undefined}
        availableMetrics={metrics}
        mode={modalMode}
      />
    </div>
  );
};

export default Metrics;
