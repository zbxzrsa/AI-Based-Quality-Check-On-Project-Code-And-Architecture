'use client';

import { useState } from 'react';
import MainLayout from '@/components/layout/main-layout';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import {
  Clock,
  Activity,
  CheckCircle2,
  XCircle,
  AlertCircle,
  PlayCircle,
  RotateCw,
  Trash2,
  Eye,
} from 'lucide-react';

interface QueueTask {
  id: string;
  projectName: string;
  prNumber: number;
  status: 'queued' | 'in_progress' | 'completed' | 'failed';
  priority: 'high' | 'medium' | 'low';
  submittedTime: string;
  estimatedCompletion?: string;
  progress?: number;
}

export default function QueuePage() {
  const [statusFilter, setStatusFilter] = useState('all');
  const [projectFilter, setProjectFilter] = useState('all');

  // Mock data
  const queueStats = {
    totalQueued: 12,
    inProgress: 3,
    avgWaitTime: '5 min',
    estimatedCompletion: '15 min',
  };

  const mockTasks: QueueTask[] = [
    {
      id: '1',
      projectName: 'AI Code Review Platform',
      prNumber: 123,
      status: 'in_progress',
      priority: 'high',
      submittedTime: '2026-01-19T10:30:00Z',
      estimatedCompletion: '2026-01-19T10:45:00Z',
      progress: 65,
    },
    {
      id: '2',
      projectName: 'E-commerce API',
      prNumber: 456,
      status: 'queued',
      priority: 'medium',
      submittedTime: '2026-01-19T10:35:00Z',
      estimatedCompletion: '2026-01-19T10:50:00Z',
    },
    {
      id: '3',
      projectName: 'Analytics Dashboard',
      prNumber: 789,
      status: 'completed',
      priority: 'low',
      submittedTime: '2026-01-19T10:00:00Z',
    },
    {
      id: '4',
      projectName: 'AI Code Review Platform',
      prNumber: 124,
      status: 'failed',
      priority: 'high',
      submittedTime: '2026-01-19T09:45:00Z',
    },
    {
      id: '5',
      projectName: 'Mobile App Backend',
      prNumber: 234,
      status: 'queued',
      priority: 'medium',
      submittedTime: '2026-01-19T10:40:00Z',
      estimatedCompletion: '2026-01-19T11:00:00Z',
    },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'in_progress':
        return <PlayCircle className="h-4 w-4 text-blue-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'queued':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'in_progress':
        return 'bg-blue-500';
      case 'failed':
        return 'bg-red-500';
      case 'queued':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredTasks = mockTasks.filter((task) => {
    if (statusFilter !== 'all' && task.status !== statusFilter) return false;
    if (projectFilter !== 'all' && task.projectName !== projectFilter)
      return false;
    return true;
  });

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Activity className="h-8 w-8" />
            Analysis Queue
          </h1>
          <p className="text-muted-foreground mt-1">
            Monitor and manage analysis tasks
          </p>
        </div>

        {/* Queue Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Queued</p>
                <p className="text-3xl font-bold mt-2">
                  {queueStats.totalQueued}
                </p>
              </div>
              <Clock className="h-8 w-8 text-yellow-500" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">In Progress</p>
                <p className="text-3xl font-bold mt-2">
                  {queueStats.inProgress}
                </p>
              </div>
              <PlayCircle className="h-8 w-8 text-blue-500" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Wait Time</p>
                <p className="text-3xl font-bold mt-2">
                  {queueStats.avgWaitTime}
                </p>
              </div>
              <Clock className="h-8 w-8 text-muted-foreground" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Est. Completion</p>
                <p className="text-3xl font-bold mt-2">
                  {queueStats.estimatedCompletion}
                </p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
          </Card>
        </div>

        {/* Filters */}
        <Card className="p-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block">
                Filter by Status
              </label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="queued">Queued</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block">
                Filter by Project
              </label>
              <Select value={projectFilter} onValueChange={setProjectFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Projects</SelectItem>
                  <SelectItem value="AI Code Review Platform">
                    AI Code Review Platform
                  </SelectItem>
                  <SelectItem value="E-commerce API">E-commerce API</SelectItem>
                  <SelectItem value="Analytics Dashboard">
                    Analytics Dashboard
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </Card>

        {/* Task List Table */}
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Project</TableHead>
                <TableHead>PR #</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Submitted</TableHead>
                <TableHead>Est. Completion</TableHead>
                <TableHead>Progress</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell className="font-medium">
                    {task.projectName}
                  </TableCell>
                  <TableCell>#{task.prNumber}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(task.status)}>
                      {getStatusIcon(task.status)}
                      <span className="ml-2 capitalize">
                        {task.status.replace('_', ' ')}
                      </span>
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={getPriorityColor(task.priority)}>
                      {task.priority}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatTime(task.submittedTime)}</TableCell>
                  <TableCell>
                    {task.estimatedCompletion
                      ? formatTime(task.estimatedCompletion)
                      : '-'}
                  </TableCell>
                  <TableCell>
                    {task.progress !== undefined ? (
                      <div className="flex items-center gap-2">
                        <Progress value={task.progress} className="w-20" />
                        <span className="text-sm text-muted-foreground">
                          {task.progress}%
                        </span>
                      </div>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                      {task.status === 'failed' && (
                        <Button variant="ghost" size="sm">
                          <RotateCw className="h-4 w-4" />
                        </Button>
                      )}
                      {task.status === 'queued' && (
                        <Button variant="ghost" size="sm">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </MainLayout>
  );
}
