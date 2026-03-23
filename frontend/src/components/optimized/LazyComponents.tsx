/**
 * Lazy-loaded Components for Performance Optimization
 * 
 * This file implements lazy loading for heavy components to improve
 * initial bundle size and loading performance.
 */

import { lazy, Suspense } from 'react';
import { Skeleton } from '@/components/ui/skeleton';

// Lazy load heavy visualization components
export const ArchitectureGraph = lazy(() => 
  import('@/components/visualizations/ArchitectureGraph')
);

export const DependencyGraph = lazy(() => 
  import('@/components/visualizations/DependencyGraph')
);

export const Neo4jGraphVisualization = lazy(() => 
  import('@/components/visualizations/Neo4jGraphVisualization')
);

export const PerformanceDashboard = lazy(() => 
  import('@/components/performance/PerformanceDashboard')
);

export const ProjectAnalysisDashboard = lazy(() => 
  import('@/components/ProjectAnalysisDashboard')
);

// Loading fallback components
export const VisualizationSkeleton = () => (
  <div className="space-y-4">
    <Skeleton className="h-8 w-64" />
    <Skeleton className="h-64 w-full" />
    <div className="grid grid-cols-3 gap-4">
      <Skeleton className="h-32" />
      <Skeleton className="h-32" />
      <Skeleton className="h-32" />
    </div>
  </div>
);

export const DashboardSkeleton = () => (
  <div className="space-y-6">
    <div className="grid grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-24" />
      ))}
    </div>
    <Skeleton className="h-64 w-full" />
    <div className="grid grid-cols-2 gap-4">
      <Skeleton className="h-48" />
      <Skeleton className="h-48" />
    </div>
  </div>
);

// Wrapper components with suspense
export const LazyArchitectureGraph = (props: any) => (
  <Suspense fallback={<VisualizationSkeleton />}>
    <ArchitectureGraph {...props} />
  </Suspense>
);

export const LazyDependencyGraph = (props: any) => (
  <Suspense fallback={<VisualizationSkeleton />}>
    <DependencyGraph {...props} />
  </Suspense>
);

export const LazyNeo4jGraphVisualization = (props: any) => (
  <Suspense fallback={<VisualizationSkeleton />}>
    <Neo4jGraphVisualization {...props} />
  </Suspense>
);

export const LazyPerformanceDashboard = (props: any) => (
  <Suspense fallback={<DashboardSkeleton />}>
    <PerformanceDashboard {...props} />
  </Suspense>
);

export const LazyProjectAnalysisDashboard = (props: any) => (
  <Suspense fallback={<DashboardSkeleton />}>
    <ProjectAnalysisDashboard {...props} />
  </Suspense>
);