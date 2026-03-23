import React from 'react';
import { AnalysisTask, ScheduleResult, RetrySchedule } from '../../types/AnalysisQueue';
import {
  getTaskTypeText,
  getStatusColor,
  getStatusText,
  getPriorityText,
  getPriorityColor,
  formatTime,
  formatDuration,
  calculateEstimatedCompletion,
  formatEstimatedCompletion,
} from '../../utils/analysisQueueUtils';
import { styles } from './AnalysisQueue.styles';

interface TaskItemProps {
  task: AnalysisTask;
  isSelected: boolean;
  isScheduledToExecute: boolean;
  retrySchedule?: RetrySchedule;
  retryStatusText?: string;
  onSelect: (taskId: string) => void;
  onIncreasePriority: (taskId: string, currentPriority: number) => void;
  onDecreasePriority: (taskId: string, currentPriority: number) => void;
  onPriorityChange: (taskId: string, newPriority: number) => void;
}

export const TaskItem: React.FC<TaskItemProps> = ({
  task,
  isSelected,
  isScheduledToExecute,
  retrySchedule,
  retryStatusText,
  onSelect,
  onIncreasePriority,
  onDecreasePriority,
  onPriorityChange,
}) => {
  const canAdjustPriority = task.status === 'pending' || task.status === 'failed';
  const estimatedCompletion = calculateEstimatedCompletion(task);

  return (
    <div
      style={{
        ...styles.taskItem,
        ...(isSelected ? styles.taskItemSelected : {}),
      }}
      onClick={() => onSelect(task.id)}
      data-testid={`task-item-${task.id}`}
    >
      <div style={styles.taskHeader}>
        <div style={styles.taskTitle}>
          <span style={styles.taskName}>{task.name}</span>
          <span style={styles.taskType}>{getTaskTypeText(task.type)}</span>
        </div>
        <div style={styles.taskMeta}>
          <span
            style={{
              ...styles.priorityBadge,
              backgroundColor: getPriorityColor(task.priority),
            }}
          >
            {getPriorityText(task.priority)} ({task.priority})
          </span>
          <span
            style={{
              ...styles.statusBadge,
              backgroundColor: getStatusColor(task.status),
            }}
            data-testid={`task-status-${task.id}`}
          >
            {getStatusText(task.status)}
          </span>
          {isScheduledToExecute && task.status === 'pending' && (
            <span style={styles.scheduledBadge}>
              ⏱️ Scheduled
            </span>
          )}
          {retrySchedule && (
            <span style={styles.retryBadge}>
              🔄 Retry {task.retryCount + 1}/{task.maxRetries}
            </span>
          )}
        </div>
      </div>

      {canAdjustPriority && (
        <div style={styles.priorityControls}>
          <span style={styles.priorityControlsLabel}>Adjust Priority:</span>
          <div style={styles.priorityButtons}>
            <button
              style={{
                ...styles.priorityButton,
                ...(task.priority >= 10 ? styles.priorityButtonDisabled : {}),
              }}
              onClick={(e) => {
                e.stopPropagation();
                onIncreasePriority(task.id, task.priority);
              }}
              disabled={task.priority >= 10}
              data-testid={`increase-priority-${task.id}`}
              title="Increase priority"
            >
              ▲
            </button>
            <span style={styles.priorityValue}>{task.priority}</span>
            <button
              style={{
                ...styles.priorityButton,
                ...(task.priority <= 1 ? styles.priorityButtonDisabled : {}),
              }}
              onClick={(e) => {
                e.stopPropagation();
                onDecreasePriority(task.id, task.priority);
              }}
              disabled={task.priority <= 1}
              data-testid={`decrease-priority-${task.id}`}
              title="Decrease priority"
            >
              ▼
            </button>
          </div>
          <input
            type="range"
            min="1"
            max="10"
            value={task.priority}
            onChange={(e) => {
              e.stopPropagation();
              const newPriority = parseInt(e.target.value, 10);
              onPriorityChange(task.id, newPriority);
            }}
            style={styles.prioritySlider}
            data-testid={`priority-slider-${task.id}`}
            title={`Set priority (1-10): ${task.priority}`}
          />
        </div>
      )}

      {task.status === 'running' && (
        <>
          <div style={styles.progressContainer}>
            <div
              style={{
                ...styles.progressBar,
                width: `${task.progress}%`,
              }}
              data-testid={`task-progress-${task.id}`}
            />
            <span style={styles.progressText}>{task.progress}%</span>
          </div>
          {estimatedCompletion && (
            <div style={styles.estimatedCompletionContainer}>
              <span style={styles.estimatedCompletionLabel}>⏱️ Est. completion:</span>
              <span 
                style={styles.estimatedCompletionValue}
                data-testid={`task-estimated-completion-${task.id}`}
              >
                {formatEstimatedCompletion(estimatedCompletion)}
              </span>
              <span style={styles.estimatedCompletionTime}>
                ({estimatedCompletion.toLocaleTimeString()})
              </span>
            </div>
          )}
        </>
      )}

      {retrySchedule && retryStatusText && (
        <div style={styles.retryInfo}>
          <span style={styles.retryIcon}>🔄</span>
          <span style={styles.retryText}>{retryStatusText}</span>
        </div>
      )}

      <div style={styles.taskDetails}>
        <div style={styles.taskDetailItem}>
          <span style={styles.taskDetailLabel}>Created:</span>
          <span style={styles.taskDetailValue}>{formatTime(task.createdAt)}</span>
        </div>
        {task.startedAt && (
          <div style={styles.taskDetailItem}>
            <span style={styles.taskDetailLabel}>Started:</span>
            <span style={styles.taskDetailValue}>{formatTime(task.startedAt)}</span>
          </div>
        )}
        {task.estimatedDuration && (
          <div style={styles.taskDetailItem}>
            <span style={styles.taskDetailLabel}>Est. Duration:</span>
            <span style={styles.taskDetailValue}>{formatDuration(task.estimatedDuration)}</span>
          </div>
        )}
        {task.retryCount > 0 && (
          <div style={styles.taskDetailItem}>
            <span style={styles.taskDetailLabel}>Retries:</span>
            <span style={styles.taskDetailValue}>
              {task.retryCount} / {task.maxRetries}
            </span>
          </div>
        )}
      </div>

      {task.error && (
        <div style={styles.errorInfo}>
          <span style={styles.errorIcon}>⚠️</span>
          <span style={styles.errorMessage}>{task.error.message}</span>
        </div>
      )}
    </div>
  );
};
