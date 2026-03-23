/**
 * AnalysisQueue页面component
 * 
 * feature:
 * - 展示analyzetaskqueue
 * - useVirtualListsupport50+task的高性能render
 * - showtaskstatus、进度and优先级
 * - supporttask优先级调整and手动操作
 * 
 * verifyRequirement: 5.5
 */

import React, { Component } from 'react';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { LoadingState } from '../components/LoadingState';
import { VirtualList } from '../components/VirtualList';
import { getApiClient } from '../lib/api-client';
import { TaskScheduler, ScheduleResult } from '../utils/taskScheduler';
import { TaskRetryScheduler, RetrySchedule } from '../utils/taskRetryScheduler';
import { AnalysisQueueProps, AnalysisTask } from '../types/AnalysisQueue';
import { TaskItem } from '../components/analysis-queue/TaskItem';
import { TaskStats } from '../components/analysis-queue/TaskStats';
import { ScheduleInfo } from '../components/analysis-queue/ScheduleInfo';
import { styles } from '../components/analysis-queue/AnalysisQueue.styles';
import { countTasksByStatus } from '../utils/analysisQueueUtils';
import '../styles/responsive.css';

interface AnalysisQueueState {
  tasks: AnalysisTask[];
  loading: boolean;
  error: Error | null;
  lastUpdate: Date | null;
  selectedTaskId: string | null;
  scheduleResult: ScheduleResult | null;
  retrySchedules: Map<string, RetrySchedule>;
}

export class AnalysisQueueComponent extends Component<AnalysisQueueProps, AnalysisQueueState> {
  private refreshTimer: NodeJS.Timeout | null = null;
  private mounted = false;
  private abortController: AbortController | null = null;
  private scheduler: TaskScheduler;
  private retryScheduler: TaskRetryScheduler;

  static defaultProps: Partial<AnalysisQueueProps> = {
    refreshInterval: 10000,
    listHeight: 600,
    maxConcurrent: 3,
  };

  constructor(props: AnalysisQueueProps) {
    super(props);
    this.state = {
      tasks: [],
      loading: true,
      error: null,
      lastUpdate: null,
      selectedTaskId: null,
      scheduleResult: null,
      retrySchedules: new Map(),
    };
    
    this.scheduler = new TaskScheduler({ 
      maxConcurrent: props.maxConcurrent || 3,
    });

    this.retryScheduler = new TaskRetryScheduler();
    this.retryScheduler.setRetryCallback(this.handleTaskRetry);
  }

  async componentDidMount(): Promise<void> {
    this.mounted = true;
    await this.fetchTasks();

    if (this.props.refreshInterval && this.props.refreshInterval > 0) {
      this.refreshTimer = setInterval(() => {
        this.fetchTasks();
      }, this.props.refreshInterval);
    }
  }

  componentWillUnmount(): void {
    this.mounted = false;
    
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    this.retryScheduler.clearAll();
  }

  fetchTasks = async (): Promise<void> => {
    if (!this.mounted) {
      return;
    }

    this.abortController = new AbortController();

    try {
      if (this.state.tasks.length === 0) {
        this.setState({ loading: true, error: null });
      }

      const apiClient = getApiClient();
      const tasks = await apiClient.get<AnalysisTask[]>('/analysis/queue');

      if (this.mounted) {
        const scheduleResult = this.scheduler.schedule(tasks);
        this.scheduleRetriesForFailedTasks(tasks);

        const retrySchedules = new Map(
          this.retryScheduler.getAllRetrySchedules().map(s => [s.taskId, s])
        );
        
        this.setState({
          tasks,
          loading: false,
          error: null,
          lastUpdate: new Date(),
          scheduleResult,
          retrySchedules,
        });
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }

      if (this.mounted) {
        this.setState({
          loading: false,
          error: error instanceof Error ? error : new Error('Failed to fetch tasks'),
        });
      }
    }
  };

  handleRefresh = (): void => {
    this.fetchTasks();
  };

  handleSelectTask = (taskId: string): void => {
    this.setState({ selectedTaskId: taskId });
  };

  handlePriorityChange = async (taskId: string, newPriority: number): Promise<void> => {
    try {
      const apiClient = getApiClient();
      await apiClient.put(`/analysis/queue/${taskId}/priority`, { priority: newPriority });
      
      this.setState(prevState => {
        const updatedTasks = prevState.tasks.map(task =>
          task.id === taskId ? { ...task, priority: newPriority } : task
        );
        
        const scheduleResult = this.scheduler.schedule(updatedTasks);
        
        return {
          tasks: updatedTasks,
          scheduleResult,
        };
      });
      
      await this.fetchTasks();
    } catch (error) {
      console.error('Failed to update task priority:', error);
    }
  };

  handleIncreasePriority = (taskId: string, currentPriority: number): void => {
    const newPriority = Math.min(10, currentPriority + 1);
    if (newPriority !== currentPriority) {
      this.handlePriorityChange(taskId, newPriority);
    }
  };

  handleDecreasePriority = (taskId: string, currentPriority: number): void => {
    const newPriority = Math.max(1, currentPriority - 1);
    if (newPriority !== currentPriority) {
      this.handlePriorityChange(taskId, newPriority);
    }
  };

  scheduleRetriesForFailedTasks = (tasks: AnalysisTask[]): void => {
    tasks.forEach(task => {
      if (task.status === 'failed' && task.retryCount < task.maxRetries) {
        if (!this.retryScheduler.isScheduled(task.id)) {
          this.retryScheduler.scheduleRetry(task);
        }
      } else if (task.status !== 'failed') {
        this.retryScheduler.cancelRetry(task.id);
      }
    });
  };

  handleTaskRetry = async (taskId: string): Promise<void> => {
    try {
      const apiClient = getApiClient();
      await apiClient.post(`/analysis/queue/${taskId}/retry`, {});
      await this.fetchTasks();
    } catch (error) {
      console.error('Failed to retry task:', error);
    }
  };

  getSortedTasks = (): AnalysisTask[] => {
    return this.scheduler.sortByPriority(this.state.tasks);
  };

  renderTaskItem = (task: AnalysisTask): React.ReactNode => {
    const isSelected = this.state.selectedTaskId === task.id;
    const { scheduleResult, retrySchedules } = this.state;
    
    const isScheduledToExecute = scheduleResult?.tasksToExecute.some(t => t.id === task.id) || false;
    const retrySchedule = retrySchedules.get(task.id);
    const retryStatusText = this.retryScheduler.getRetryStatusText(task);

    return (
      <TaskItem
        task={task}
        isSelected={isSelected}
        isScheduledToExecute={isScheduledToExecute}
        retrySchedule={retrySchedule}
        retryStatusText={retryStatusText}
        onSelect={this.handleSelectTask}
        onIncreasePriority={this.handleIncreasePriority}
        onDecreasePriority={this.handleDecreasePriority}
        onPriorityChange={this.handlePriorityChange}
      />
    );
  };

  render(): React.ReactNode {
    const { loading, error, tasks, lastUpdate, scheduleResult } = this.state;
    const { listHeight } = this.props;

    if (loading && tasks.length === 0) {
      return (
        <LoadingState
          variant="spinner"
          size="large"
          text="Loading analysis queue..."
          fullscreen={false}
        />
      );
    }

    if (error && tasks.length === 0) {
      return (
        <div style={styles.errorContainer}>
          <div style={styles.errorIcon}>⚠️</div>
          <h2 style={styles.errorTitle}>Failed to Load Analysis Queue</h2>
          <p style={styles.errorMessage}>{error.message}</p>
          <button onClick={this.handleRefresh} style={styles.retryButton}>
            Retry
          </button>
        </div>
      );
    }

    const statusCounts = countTasksByStatus(tasks);
    const sortedTasks = this.getSortedTasks();

    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h1 style={styles.title}>Analysis Queue</h1>
          <div style={styles.headerActions}>
            {lastUpdate && (
              <span style={styles.lastUpdate}>
                Last updated: {lastUpdate.toLocaleTimeString()}
              </span>
            )}
            <button onClick={this.handleRefresh} style={styles.refreshButton}>
              🔄 Refresh
            </button>
          </div>
        </div>

        <TaskStats
          total={tasks.length}
          pending={statusCounts.pending}
          running={statusCounts.running}
          completed={statusCounts.completed}
          failed={statusCounts.failed}
        />

        {scheduleResult && (
          <ScheduleInfo
            scheduleResult={scheduleResult}
            maxConcurrent={this.scheduler.getConfig().maxConcurrent}
          />
        )}

        <div style={styles.listContainer}>
          <div style={styles.listHeader}>
            <h2 style={styles.listTitle}>Tasks ({tasks.length}) - Sorted by Priority</h2>
          </div>

          {tasks.length === 0 ? (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>📋</div>
              <p style={styles.emptyText}>No tasks in the queue</p>
            </div>
          ) : (
            <VirtualList
              items={sortedTasks}
              height={listHeight!}
              itemHeight={220}
              renderItem={this.renderTaskItem}
              className="analysis-queue-list"
            />
          )}
        </div>

        {error && tasks.length > 0 && (
          <div style={styles.backgroundErrorBanner}>
            ⚠️ Failed to refresh data: {error.message}
          </div>
        )}
      </div>
    );
  }
}

export const AnalysisQueue: React.FC<AnalysisQueueProps> = (props) => {
  return (
    <ErrorBoundary>
      <AnalysisQueueComponent {...props} />
    </ErrorBoundary>
  );
};

export default AnalysisQueue;
