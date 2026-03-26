/**
 * task优先级调度器
 * 
 * 实现基于优先级and资源可用性的task调度算法
 * 
 * verifyRequirement: 5.1
 */

import { AnalysisTask } from '../types/AnalysisQueue';

/**
 * 调度器config
 */
export interface SchedulerConfig {
  /** 最大并发task数 */
  maxConcurrent: number;
  /** 资源可用性checkfunction（可选） */
  checkResourceAvailability?: () => boolean;
}

/**
 * 调度result
 */
export interface ScheduleResult {
  /** shouldexecute的task列表（按优先级sort） */
  tasksToExecute: AnalysisTask[];
  /** wait中的task列表 */
  waitingTasks: AnalysisTask[];
  /** 当前run的task数 */
  runningCount: number;
  /** 可用的execute槽位数 */
  availableSlots: number;
}

/**
 * task优先级调度器class
 * 
 * 根据task优先级and资源可用性调度taskexecute
 */
export class TaskScheduler {
  private config: SchedulerConfig;

  constructor(config: SchedulerConfig) {
    this.config = config;
  }

  /**
   * 调度task
   * 
   * @param tasks - 所有task列表
   * @returns 调度result
   */
  schedule(tasks: AnalysisTask[]): ScheduleResult {
    // 统计当前run的task数
    const runningTasks = tasks.filter(t => t.status === 'running');
    const runningCount = runningTasks.length;

    // 计算可用的execute槽位
    const availableSlots = Math.max(0, this.config.maxConcurrent - runningCount);

    // get待handle的task（pendingstatus）
    const pendingTasks = tasks.filter(t => t.status === 'pending');

    // 按优先级sort（高优先级在前）
    const sortedPendingTasks = this.sortByPriority(pendingTasks);

    // check资源可用性
    const resourcesAvailable = this.config.checkResourceAvailability
      ? this.config.checkResourceAvailability()
      : true;

    // 如果没有可用槽位或资源不可用，所有task都wait
    if (availableSlots === 0 || !resourcesAvailable) {
      return {
        tasksToExecute: [],
        waitingTasks: sortedPendingTasks,
        runningCount,
        availableSlots: 0,
      };
    }

    // 选择shouldexecute的task（取前Nitem高优先级task）
    const tasksToExecute = sortedPendingTasks.slice(0, availableSlots);
    const waitingTasks = sortedPendingTasks.slice(availableSlots);

    return {
      tasksToExecute,
      waitingTasks,
      runningCount,
      availableSlots,
    };
  }

  /**
   * 按优先级sorttask
   * 
   * sort规则：
   * 1. 优先级高的在前（priority降序）
   * 2. 优先级相同时，create时间早的在前（FIFO）
   * 
   * @param tasks - 待sort的task列表
   * @returns sort后的task列表
   */
  sortByPriority(tasks: AnalysisTask[]): AnalysisTask[] {
    return [...tasks].sort((a, b) => {
      // 首先按优先级降序sort（高优先级在前）
      if (a.priority !== b.priority) {
        return b.priority - a.priority;
      }

      // 优先级相同时，按create时间升序sort（早create的在前）
      const timeA = new Date(a.createdAt).getTime();
      const timeB = new Date(b.createdAt).getTime();
      return timeA - timeB;
    });
  }

  /**
   * get下一itemshouldexecute的task
   * 
   * @param tasks - 所有task列表
   * @returns 下一itemshouldexecute的task，如果没有则returnnull
   */
  getNextTask(tasks: AnalysisTask[]): AnalysisTask | null {
    const result = this.schedule(tasks);
    return result.tasksToExecute.length > 0 ? result.tasksToExecute[0] : null;
  }

  /**
   * update调度器config
   * 
   * @param config - 新的config（部分update）
   */
  updateConfig(config: Partial<SchedulerConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * get当前config
   * 
   * @returns 当前调度器config
   */
  getConfig(): SchedulerConfig {
    return { ...this.config };
  }
}

/**
 * create默认的task调度器
 * 
 * @param maxConcurrent - 最大并发task数，默认为3
 * @returns task调度器instance
 */
export function createTaskScheduler(maxConcurrent: number = 3): TaskScheduler {
  return new TaskScheduler({ maxConcurrent });
}
