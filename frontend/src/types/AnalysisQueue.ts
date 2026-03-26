export interface AnalysisQueueProps {
  refreshInterval?: number;
  listHeight?: number;
  maxConcurrent?: number;
}

export interface AnalysisTask {
  id: string;
  name: string;
  type: 'code_analysis' | 'security_scan' | 'performance_test' | 'dependency_check';
  priority: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  projectId: string;
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  retryCount: number;
  maxRetries: number;
  estimatedDuration?: number;
  error?: {
    code: string;
    message: string;
    timestamp: Date;
  };
}

export interface AnalysisQueueState {
  tasks: AnalysisTask[];
  loading: boolean;
  error: Error | null;
  lastUpdate: Date | null;
  selectedTaskId: string | null;
  scheduleResult: ScheduleResult | null;
  retrySchedules: Map<string, RetrySchedule>;
}

export interface ScheduleResult {
  availableSlots: number;
  tasksToExecute: AnalysisTask[];
  waitingTasks: AnalysisTask[];
}

export interface RetrySchedule {
  taskId: string;
  retryCount: number;
  nextRetryTime: Date;
  retryDelay: number;
}
