/**
 * Performance Monitoring Dashboard
 * 
 * Provides real-time performance monitoring and optimization insights:
 * - API response times and cache hit rates
 * - Database query performance
 * - Frontend bundle analysis
 * - Real-time system metrics
 * - Performance recommendations
 * 
 * Requirements: 1.4, 1.5, 2.7, 4.1, 4.2, 4.6, 10.2, 10.8
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer
} from 'recharts';
import { 
  Activity, 
  Database, 
  Globe, 
  Zap, 
  TrendingUp, 
  AlertTriangle, 
  BarChart3,
  Cpu,
  RefreshCw,
  Lock
} from 'lucide-react';
import { apiClientEnhanced } from '@/lib/api-client';
import { validatePerformanceDashboardData, type PerformanceDashboardData } from '@/lib/validations/api-schemas';
import { ErrorHandler } from '@/lib/error-handler';
import { featureFlagsService } from '@/lib/feature-flags';

interface PerformanceDashboardProps {
  projectId: string;
  autoRefreshInterval?: number; // in milliseconds, default 30000 (30 seconds)
}

const COLORS = {
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#6366f1'
};

/**
 * Fetch performance metrics from production API
 */
async function fetchPerformanceMetrics(projectId: string): Promise<PerformanceDashboardData> {
  try {
    // apiClientEnhanced.get<T>() returns Promise<T>, not Promise<{data: T}>
    const response = await apiClientEnhanced.get<PerformanceDashboardData>(
      `/projects/${projectId}/metrics`
    );

    // Validate response data
    const validatedData = validatePerformanceDashboardData(response);
    return validatedData;
  } catch (error) {
    const errorInfo = ErrorHandler.handleError(error);
    ErrorHandler.logError(errorInfo);
    
    // Report to backend in production
    if (process.env.NODE_ENV === 'production') {
      await ErrorHandler.reportToBackend(errorInfo);
    }
    
    throw error;
  }
}

const PerformanceDashboard: React.FC<PerformanceDashboardProps> = ({ 
  projectId,
  autoRefreshInterval = 30000 
}) => {
  // Check feature flag status - Validates Requirements: 10.2, 10.8
  const isFeatureEnabled = featureFlagsService.isEnabled('performance-dashboard-production');
  
  // Fetch performance metrics using TanStack Query
  const {
    data: metricsData,
    isLoading,
    isError,
    error,
    refetch,
    isRefetching
  } = useQuery({
    queryKey: ['performance-metrics', projectId],
    queryFn: () => fetchPerformanceMetrics(projectId),
    enabled: isFeatureEnabled,
    refetchInterval: autoRefreshInterval,
    staleTime: 10000, // Consider data stale after 10 seconds
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Feature flag disabled - show placeholder (Validates Requirements: 10.8)
  if (!isFeatureEnabled) {
    return (
      <div className="space-y-6">
        <Card className="border-gray-200">
          <CardContent className="p-12">
            <div className="text-center max-w-md mx-auto">
              <Lock className="h-16 w-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-xl font-semibold text-gray-700 mb-2">Feature Not Available</h3>
              <p className="text-gray-600 mb-4">
                The Performance Dashboard is currently disabled. This feature is being progressively rolled out.
              </p>
              <p className="text-sm text-gray-500">
                Please contact your administrator if you need access to this feature.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Transform API data for chart display
  const performanceData = React.useMemo(() => {
    if (!metricsData?.metrics.response_time) return [];
    
    return metricsData.metrics.response_time.map((metric, index) => ({
      timestamp: new Date(metric.timestamp).getTime(),
      duration: metric.value,
      requests: metricsData.metrics.throughput[index]?.value || 0
    }));
  }, [metricsData]);

  // Calculate derived metrics from API data
  const derivedMetrics = React.useMemo(() => {
    if (!metricsData) return null;
    
    const latestMetrics = {
      response_time: metricsData.metrics.response_time[metricsData.metrics.response_time.length - 1]?.value || 0,
      error_rate: metricsData.metrics.error_rate[metricsData.metrics.error_rate.length - 1]?.value || 0,
      cpu_usage: metricsData.metrics.cpu_usage[metricsData.metrics.cpu_usage.length - 1]?.value || 0,
      memory_usage: metricsData.metrics.memory_usage[metricsData.metrics.memory_usage.length - 1]?.value || 0,
    };
    
    return {
      api: {
        responseTime: latestMetrics.response_time,
        errorRate: latestMetrics.error_rate,
        requestsPerSecond: metricsData.aggregations.total_requests / 7, // Average per day over 7 days
      },
      system: {
        cpuUsage: latestMetrics.cpu_usage,
        memoryUsage: latestMetrics.memory_usage,
      }
    };
  }, [metricsData]);
  
  // Performance score calculation
  const performanceScore = React.useMemo(() => {
    if (!metricsData || !derivedMetrics) return 0;
    
    let score = 100;
    
    // Penalize based on response time
    if (metricsData.aggregations.avg_response_time > 200) score -= 15;
    if (metricsData.aggregations.p95_response_time > 500) score -= 10;
    
    // Penalize based on error rate
    if (derivedMetrics.api.errorRate > 5) score -= 20;
    else if (derivedMetrics.api.errorRate > 2) score -= 10;
    
    // Penalize based on system resources
    if (derivedMetrics.system.cpuUsage > 80) score -= 20;
    else if (derivedMetrics.system.cpuUsage > 60) score -= 10;
    
    if (derivedMetrics.system.memoryUsage > 85) score -= 15;
    else if (derivedMetrics.system.memoryUsage > 70) score -= 5;
    
    return Math.max(0, score);
  }, [metricsData, derivedMetrics]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return COLORS.success;
    if (score >= 60) return COLORS.warning;
    return COLORS.error;
  };

  const getScoreLabel = (score: number) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Poor';
  };

  // Handle error state
  if (isError) {
    const errorInfo = ErrorHandler.handleError(error);
    
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Performance Dashboard</h1>
            <p className="text-gray-600 mt-1">Monitor and optimize system performance</p>
          </div>
        </div>
        
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center text-red-800">
              <AlertTriangle className="h-5 w-5 mr-2" />
              Error Loading Performance Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700 mb-4">
              {ErrorHandler.getUserMessage(errorInfo)}
            </p>
            {ErrorHandler.shouldRetry(errorInfo) && (
              <Button onClick={() => refetch()} variant="outline" className="border-red-300">
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  // Handle loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Performance Dashboard</h1>
            <p className="text-gray-600 mt-1">Monitor and optimize system performance</p>
          </div>
        </div>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center h-64 space-y-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="text-gray-600">Loading performance metrics...</p>
              <Progress value={33} className="w-64" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!metricsData || !derivedMetrics) {
    return (
      <div className="space-y-6">
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="flex items-center text-yellow-800">
              <AlertTriangle className="h-5 w-5 mr-2" />
              No Data Available
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-yellow-700">
              No performance metrics data available for this project.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Performance Dashboard</h1>
          <p className="text-gray-600 mt-1">Monitor and optimize system performance</p>
        </div>
        <div className="flex items-center space-x-4">
          <Button
            onClick={() => refetch()}
            size="sm"
            disabled={isRefetching}
          >
            {isRefetching ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Refreshing...
              </>
            ) : (
              <>
                <TrendingUp className="w-4 h-4 mr-2" />
                Refresh
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Performance Score */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <BarChart3 className="w-5 h-5 mr-2" />
            Overall Performance Score
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-6">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Performance Score</span>
                <span className="text-sm text-gray-600">{performanceScore}/100</span>
              </div>
              <Progress value={performanceScore} className="h-3" />
            </div>
            <div className="text-center">
              <div 
                className="text-3xl font-bold"
                style={{ color: getScoreColor(performanceScore) }}
              >
                {performanceScore}
              </div>
              <div className="text-sm text-gray-600">
                {getScoreLabel(performanceScore)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Metrics */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="api">API</TabsTrigger>
          <TabsTrigger value="database">Database</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">API Response Time</CardTitle>
                <Globe className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {derivedMetrics.api.responseTime.toFixed(0)}ms
                </div>
                <p className="text-xs text-muted-foreground">
                  Target: &lt;200ms
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">P95 Response Time</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metricsData.aggregations.p95_response_time.toFixed(0)}ms
                </div>
                <p className="text-xs text-muted-foreground">
                  Target: &lt;500ms
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {derivedMetrics.api.errorRate.toFixed(1)}%
                </div>
                <p className="text-xs text-muted-foreground">
                  Target: &lt;5%
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">System Load</CardTitle>
                <Cpu className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {derivedMetrics.system.cpuUsage.toFixed(1)}%
                </div>
                <p className="text-xs text-muted-foreground">
                  CPU usage
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Performance Trends Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Performance Trends</CardTitle>
              <CardDescription>Response time over time</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="timestamp" 
                    tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                  />
                  <YAxis />
                  <Tooltip 
                    labelFormatter={(value) => new Date(value).toLocaleString()}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="duration" 
                    stroke={COLORS.primary} 
                    strokeWidth={2}
                    name="Response Time (ms)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Tab */}
        <TabsContent value="api" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Average Response Time</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {metricsData.aggregations.avg_response_time.toFixed(1)}ms
                </div>
                <p className="text-sm text-gray-600">avg response time</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Error Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-red-600">
                  {derivedMetrics.api.errorRate.toFixed(1)}%
                </div>
                <p className="text-sm text-gray-600">4xx/5xx errors</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Total Requests</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {metricsData.aggregations.total_requests}
                </div>
                <p className="text-sm text-gray-600">in time range</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Database Tab */}
        <TabsContent value="database" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">P95 Response Time</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {metricsData.aggregations.p95_response_time.toFixed(0)}ms
                </div>
                <p className="text-sm text-gray-600">95th percentile</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">P99 Response Time</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {metricsData.aggregations.p99_response_time.toFixed(0)}ms
                </div>
                <p className="text-sm text-gray-600">99th percentile</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Total Errors</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {metricsData.aggregations.total_errors}
                </div>
                <p className="text-sm text-gray-600">error count</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* System Tab */}
        <TabsContent value="system" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">CPU Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {derivedMetrics.system.cpuUsage.toFixed(1)}%
                </div>
                <Progress value={derivedMetrics.system.cpuUsage} className="mt-2" />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Memory Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {derivedMetrics.system.memoryUsage.toFixed(1)}%
                </div>
                <Progress value={derivedMetrics.system.memoryUsage} className="mt-2" />
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default PerformanceDashboard;