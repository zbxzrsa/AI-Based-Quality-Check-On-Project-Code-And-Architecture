'use client';

import MainLayout from '@/components/layout/main-layout';
import LineChart from '@/components/charts/line-chart';
import BarChart from '@/components/charts/bar-chart';
import AreaChart from '@/components/charts/area-chart';
import GaugeChart from '@/components/charts/gauge-chart';
import { Card } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { TrendingUp, Download } from 'lucide-react';

export default function MetricsPage() {
  // Mock data
  const codeQualityData = [
    { date: 'Jan 1', quality: 75, security: 80, maintainability: 70 },
    { date: 'Jan 8', quality: 78, security: 82, maintainability: 73 },
    { date: 'Jan 15', quality: 82, security: 85, maintainability: 78 },
    { date: 'Jan 22', quality: 85, security: 87, maintainability: 82 },
    { date: 'Jan 29', quality: 88, security: 90, maintainability: 85 },
  ];

  const architectureHealthData = [
    { date: 'Week 1', health: 72, coupling: 65, cohesion: 78 },
    { date: 'Week 2', health: 75, coupling: 68, cohesion: 80 },
    { date: 'Week 3', health: 78, coupling: 70, cohesion: 82 },
    { date: 'Week 4', health: 82, coupling: 75, cohesion: 85 },
  ];

  const reviewCompletionData = [
    { month: 'Sep', completed: 45, pending: 12 },
    { month: 'Oct', completed: 52, pending: 8 },
    { month: 'Nov', completed: 58, pending: 10 },
    { month: 'Dec', completed: 65, pending: 7 },
    { month: 'Jan', completed: 72, pending: 5 },
  ];

  const teamProductivityData = [
    { week: 'Week 1', prs: 15, reviews: 28, issues: 8 },
    { week: 'Week 2', prs: 18, reviews: 32, issues: 6 },
    { week: 'Week 3', prs: 22, reviews: 38, issues: 5 },
    { week: 'Week 4', prs: 20, reviews: 35, issues: 7 },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <TrendingUp className="h-8 w-8" />
              Metrics Dashboard
            </h1>
            <p className="text-muted-foreground mt-1">
              Track code quality, architecture health, and team productivity
            </p>
          </div>
          <div className="flex gap-2">
            <Select defaultValue="30days">
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7days">Last 7 days</SelectItem>
                <SelectItem value="30days">Last 30 days</SelectItem>
                <SelectItem value="90days">Last 90 days</SelectItem>
                <SelectItem value="1year">Last year</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

        {/* Overview Gauges */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <GaugeChart
            value={88}
            title="Code Quality"
            subtitle="Overall quality score"
          />
          <GaugeChart
            value={82}
            title="Architecture Health"
            subtitle="System health score"
          />
          <GaugeChart
            value={92}
            title="Security Score"
            subtitle="Security compliance"
          />
          <GaugeChart
            value={75}
            title="Team Velocity"
            subtitle="Sprint completion rate"
          />
        </div>

        {/* Code Quality Trends */}
        <LineChart
          data={codeQualityData}
          title="Code Quality Trends"
          xAxisKey="date"
          lines={[
            { dataKey: 'quality', stroke: '#3b82f6', name: 'Quality' },
            { dataKey: 'security', stroke: '#22c55e', name: 'Security' },
            {
              dataKey: 'maintainability',
              stroke: '#f59e0b',
              name: 'Maintainability',
            },
          ]}
          height={350}
        />

        {/* Architecture Health */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AreaChart
            data={architectureHealthData}
            title="Architecture Health Metrics"
            xAxisKey="date"
            areas={[
              {
                dataKey: 'health',
                fill: '#3b82f680',
                stroke: '#3b82f6',
                name: 'Health',
              },
              {
                dataKey: 'coupling',
                fill: '#f59e0b80',
                stroke: '#f59e0b',
                name: 'Coupling',
              },
              {
                dataKey: 'cohesion',
                fill: '#22c55e80',
                stroke: '#22c55e',
                name: 'Cohesion',
              },
            ]}
          />

          <BarChart
            data={reviewCompletionData}
            title="Review Completion Rates"
            xAxisKey="month"
            bars={[
              { dataKey: 'completed', fill: '#22c55e', name: 'Completed' },
              { dataKey: 'pending', fill: '#f59e0b', name: 'Pending' },
            ]}
          />
        </div>

        {/* Team Productivity */}
        <BarChart
          data={teamProductivityData}
          title="Team Productivity Metrics"
          xAxisKey="week"
          bars={[
            { dataKey: 'prs', fill: '#3b82f6', name: 'Pull Requests' },
            { dataKey: 'reviews', fill: '#8b5cf6', name: 'Reviews' },
            { dataKey: 'issues', fill: '#ef4444', name: 'Issues' },
          ]}
          height={350}
        />

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Average Review Time
            </h3>
            <p className="text-3xl font-bold">2.5 hrs</p>
            <p className="text-sm text-green-600 mt-2">↓ 15% from last month</p>
          </Card>

          <Card className="p-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Critical Issues Resolved
            </h3>
            <p className="text-3xl font-bold">94%</p>
            <p className="text-sm text-green-600 mt-2">↑ 8% from last month</p>
          </Card>

          <Card className="p-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Code Coverage
            </h3>
            <p className="text-3xl font-bold">87%</p>
            <p className="text-sm text-green-600 mt-2">↑ 3% from last month</p>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
