/**
 * taskAutoRetryScheduler
 * 
 * 实现failuretask的自动retry机制
 * - retry延迟: 5min、15min、30min
 * - 最多retry3times
 * 
 * verifyRequirement: 5.2
 */

import { AnalysisTask } from '../types/AnalysisQueue';

/**
 * retry延迟config（ms）
 */
export const RETRY_DELAYS = [
  5 * 60 * 1000,  // 5min
  15 * 60 * 1000, // 15min
  30 * 60 * 1000, // 30min
];

/**
 * retry调度info
 */
export interface RetrySchedule {
  /** taskID */
  taskId: string;
  /** 当前retrytimes数 */
  retryCount: number;
  /** 下timesretry时间 */
  nextRetryTime: Date;
  /** retry延迟（ms） */
  retryDelay: number;
}

/**
 * taskretry调度器
 */
export class TaskRetryScheduler {
  private retrySchedules: Map<string, RetrySchedule> = new Map();
  private retryTimers: Map<string, NodeJS.Timeout> = new Map();
  private onRetryCallback?: (taskId: string) => void;

  /**
   * setretry回调function
   * 
   * @param callback - 当taskneedretry时调用的回调function
   */
  setRetryCallback(callback: (taskId: string) => void): void {
    this.onRetryCallback = callback;
  }

  /**
   * 调度failuretask的retry
   * 
   * @param task - failure的task
   * @returns retry调度info，如果不shouldretry则returnnull
   */
  scheduleRetry(task: AnalysisTask): RetrySchedule | null {
    // check是否已达到最大retrytimes数
    if (task.retryCount >= task.maxRetries) {
      return null;
    }

    // checktaskstatus是否为failure
    if (task.status !== 'failed') {
      return null;
    }

    // 计算retry延迟
    const retryDelay = this.getRetryDelay(task.retryCount);
    const nextRetryTime = new Date(Date.now() + retryDelay);

    // createretry调度info
    const schedule: RetrySchedule = {
      taskId: task.id,
      retryCount: task.retryCount,
      nextRetryTime,
      retryDelay,
    };

    // save调度info
    this.retrySchedules.set(task.id, schedule);

    // 清除旧的定时器（如果存在）
    this.clearRetryTimer(task.id);

    // set新的retry定时器
    const timer = setTimeout(() => {
      this.executeRetry(task.id);
    }, retryDelay);

    this.retryTimers.set(task.id, timer);

    return schedule;
  }

  /**
   * getretry延迟
   * 
   * @param retryCount - 当前retrytimes数
   * @returns retry延迟（ms）
   */
  getRetryDelay(retryCount: number): number {
    // use预定义的retry延迟
    if (retryCount < RETRY_DELAYS.length) {
      return RETRY_DELAYS[retryCount];
    }
    // 如果超出预定义延迟，use最后一item延迟
    return RETRY_DELAYS[RETRY_DELAYS.length - 1];
  }

  /**
   * executeretry
   * 
   * @param taskId - taskID
   */
  private executeRetry(taskId: string): void {
    // 移除调度infoand定时器
    this.retrySchedules.delete(taskId);
    this.retryTimers.delete(taskId);

    // 调用retry回调
    if (this.onRetryCallback) {
      this.onRetryCallback(taskId);
    }
  }

  /**
   * 清除task的retry定时器
   * 
   * @param taskId - taskID
   */
  clearRetryTimer(taskId: string): void {
    const timer = this.retryTimers.get(taskId);
    if (timer) {
      clearTimeout(timer);
      this.retryTimers.delete(taskId);
    }
  }

  /**
   * canceltask的retry调度
   * 
   * @param taskId - taskID
   */
  cancelRetry(taskId: string): void {
    this.clearRetryTimer(taskId);
    this.retrySchedules.delete(taskId);
  }

  /**
   * gettask的retry调度info
   * 
   * @param taskId - taskID
   * @returns retry调度info，如果不存在则returnnull
   */
  getRetrySchedule(taskId: string): RetrySchedule | null {
    return this.retrySchedules.get(taskId) || null;
  }

  /**
   * get所有retry调度info
   * 
   * @returns 所有retry调度info的数组
   */
  getAllRetrySchedules(): RetrySchedule[] {
    return Array.from(this.retrySchedules.values());
  }

  /**
   * checktask是否已调度retry
   * 
   * @param taskId - taskID
   * @returns 是否已调度retry
   */
  isScheduled(taskId: string): boolean {
    return this.retrySchedules.has(taskId);
  }

  /**
   * get距离下timesretry的剩余时间
   * 
   * @param taskId - taskID
   * @returns 剩余时间（ms），如果未调度则returnnull
   */
  getTimeUntilRetry(taskId: string): number | null {
    const schedule = this.retrySchedules.get(taskId);
    if (!schedule) {
      return null;
    }

    const now = Date.now();
    const retryTime = schedule.nextRetryTime.getTime();
    return Math.max(0, retryTime - now);
  }

  /**
   * format化retry延迟为可读字符串
   * 
   * @param delayMs - 延迟时间（ms）
   * @returns format化的字符串
   */
  formatRetryDelay(delayMs: number): string {
    const minutes = Math.floor(delayMs / (60 * 1000));
    if (minutes < 60) {
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    }
    const hours = Math.floor(minutes / 60);
    return `${hours} hour${hours !== 1 ? 's' : ''}`;
  }

  /**
   * cleanup所有retry调度
   */
  clearAll(): void {
    // 清除所有定时器
    for (const timer of this.retryTimers.values()) {
      clearTimeout(timer);
    }
    this.retryTimers.clear();
    this.retrySchedules.clear();
  }

  /**
   * getretrystatus描述
   * 
   * @param task - task
   * @returns retrystatus描述
   */
  getRetryStatusText(task: AnalysisTask): string {
    if (task.status !== 'failed') {
      return '';
    }

    if (task.retryCount >= task.maxRetries) {
      return 'Max retries reached';
    }

    const schedule = this.getRetrySchedule(task.id);
    if (schedule) {
      const timeUntil = this.getTimeUntilRetry(task.id);
      if (timeUntil !== null) {
        const minutes = Math.ceil(timeUntil / (60 * 1000));
        return `Retry in ${minutes} minute${minutes !== 1 ? 's' : ''}`;
      }
    }

    return 'Retry scheduled';
  }
}

/**
 * createtaskretry调度器instance
 * 
 * @returns taskretry调度器instance
 */
export function createTaskRetryScheduler(): TaskRetryScheduler {
  return new TaskRetryScheduler();
}
