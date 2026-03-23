/**
 * ErrorMonitorservice
 * 
 * feature:
 * - integrationSentry或class似监控service
 * - 实现error捕获and上报
 * - 实现error率监控（5min窗口，10%threshold）
 * - 实现告警触发机制
 * 
 * verifyRequirement: 9.1, 9.4, 9.5
 */

export interface MonitorConfig {
  dsn?: string;
  environment: 'development' | 'test' | 'production';
  enableDebugMode?: boolean;
  sampleRate?: number;
  beforeSend?: (error: ErrorReport) => ErrorReport | null;
}

export interface ErrorContext {
  userId?: string;
  url: string;
  userAgent: string;
  timestamp: Date;
  additionalData?: Record<string, any>;
}

export interface ErrorReport {
  id: string;
  type: 'network' | 'validation' | 'authorization' | 'server' | 'client' | 'unknown';
  message: string;
  stack?: string;
  context: ErrorContext;
  timestamp: Date;
}

export interface User {
  id: string;
  email?: string;
  username?: string;
}

type LogLevel = 'info' | 'warning' | 'error';

interface ErrorRateWindow {
  startTime: number;
  errorCount: number;
  totalRequests: number;
  alertTriggered: boolean;
}

/**
 * ErrorMonitorclass
 * 负责error监控、上报and告警
 */
export class ErrorMonitor {
  private config: MonitorConfig;
  private initialized = false;
  private currentUser?: User;
  private errorRateWindow: ErrorRateWindow;
  private readonly WINDOW_SIZE = 5 * 60 * 1000; // 5min
  private readonly ERROR_RATE_THRESHOLD = 0.1; // 10%
  private alertCallbacks: Array<(message: string) => void> = [];

  constructor(config: MonitorConfig) {
    this.config = config;
    this.errorRateWindow = {
      startTime: Date.now(),
      errorCount: 0,
      totalRequests: 0,
      alertTriggered: false,
    };
  }

  /**
   * 初始化监控service
   */
  initialize(config?: Partial<MonitorConfig>): void {
    if (config) {
      this.config = { ...this.config, ...config };
    }

    // 在prodenv中，这里会初始化Sentry或其他监控service
    // if (this.config.dsn && typeof window !== 'undefined') {
    //   Sentry.init({
    //     dsn: this.config.dsn,
    //     environment: this.config.environment,
    //     sampleRate: this.config.sampleRate || 1.0,
    //     beforeSend: (event) => {
    //       if (this.config.beforeSend) {
    //         return this.config.beforeSend(event as any);
    //       }
    //       return event;
    //     },
    //   });
    // }

    this.initialized = true;

    // set全局errorhandle器
    if (typeof window !== 'undefined') {
      window.addEventListener('error', this.handleGlobalError.bind(this));
      window.addEventListener('unhandledrejection', this.handleUnhandledRejection.bind(this));
    }
  }

  /**
   * 捕获error并上报
   */
  captureError(error: Error, context: Partial<ErrorContext> = {}): void {
    if (!this.initialized) {
      console.warn('ErrorMonitor not initialized');
      return;
    }

    const errorReport: ErrorReport = {
      id: this.generateErrorId(),
      type: this.classifyError(error),
      message: error.message,
      stack: error.stack,
      context: this.buildErrorContext(context),
      timestamp: new Date(),
    };

    // 应用beforeSend钩子
    const processedReport = this.config.beforeSend
      ? this.config.beforeSend(errorReport)
      : errorReport;

    if (!processedReport) {
      return; // beforeSendreturnnull表示不上报
    }

    // 在prodenv中，这里会发送到Sentry
    // if (this.config.dsn) {
    //   Sentry.captureException(error, {
    //     contexts: {
    //       custom: processedReport.context,
    //     },
    //   });
    // }

    // devenv下output到控制台
    if (this.config.enableDebugMode) {
      console.error('[ErrorMonitor]', processedReport);
    }

    // updateerror率统计
    this.updateErrorRate(true);
  }

  /**
   * 捕获消息
   */
  captureMessage(message: string, level: LogLevel = 'info'): void {
    if (!this.initialized) {
      console.warn('ErrorMonitor not initialized');
      return;
    }

    // 在prodenv中，这里会发送到Sentry
    // if (this.config.dsn) {
    //   Sentry.captureMessage(message, level);
    // }

    if (this.config.enableDebugMode) {
      console.log(`[ErrorMonitor] ${level.toUpperCase()}: ${message}`);
    }
  }

  /**
   * setuser上下文
   */
  setUser(user: User | null): void {
    if (!this.initialized) {
      console.warn('ErrorMonitor not initialized');
      return;
    }

    this.currentUser = user || undefined;

    // 在prodenv中，这里会setSentryuser上下文
    // if (this.config.dsn) {
    //   Sentry.setUser(user);
    // }
  }

  /**
   * recordAPIrequest（用于error率计算）
   */
  recordRequest(success: boolean): void {
    if (!this.initialized) {
      return;
    }
    this.updateErrorRate(!success);
  }

  /**
   * 注册告警回调
   */
  onAlert(callback: (message: string) => void): void {
    this.alertCallbacks.push(callback);
  }

  /**
   * 清除所有告警回调
   */
  clearAlertCallbacks(): void {
    this.alertCallbacks = [];
  }

  /**
   * get当前error率
   */
  getErrorRate(): number {
    this.resetWindowIfExpired();
    if (this.errorRateWindow.totalRequests === 0) {
      return 0;
    }
    return this.errorRateWindow.errorCount / this.errorRateWindow.totalRequests;
  }

  /**
   * geterror统计
   */
  getErrorStats(): ErrorRateWindow {
    this.resetWindowIfExpired();
    return { ...this.errorRateWindow };
  }

  /**
   * handle全局error
   */
  private handleGlobalError(event: ErrorEvent): void {
    const error = event.error || new Error(event.message);
    this.captureError(error, {
      url: event.filename || window.location.href,
      additionalData: {
        lineno: event.lineno,
        colno: event.colno,
      },
    });
  }

  /**
   * handle未捕获的Promise拒绝
   */
  private handleUnhandledRejection(event: PromiseRejectionEvent): void {
    const error = event.reason instanceof Error
      ? event.reason
      : new Error(String(event.reason));
    
    this.captureError(error, {
      url: window.location.href,
      additionalData: {
        type: 'unhandledRejection',
      },
    });
  }

  /**
   * updateerror率统计
   */
  private updateErrorRate(isError: boolean): void {
    this.resetWindowIfExpired();

    this.errorRateWindow.totalRequests++;
    if (isError) {
      this.errorRateWindow.errorCount++;
    }

    this.checkErrorRate();
  }

  /**
   * checkerror率是否超过threshold
   */
  private checkErrorRate(): void {
    const errorRate = this.getErrorRate();
    
    // 只在error率超过threshold、有足够样本且未触发过告警时触发
    if (errorRate > this.ERROR_RATE_THRESHOLD && 
        this.errorRateWindow.totalRequests >= 10 &&
        !this.errorRateWindow.alertTriggered) {
      const message = `Error rate exceeded ${this.ERROR_RATE_THRESHOLD * 100}% in 5 minutes: ${(errorRate * 100).toFixed(2)}% (${this.errorRateWindow.errorCount}/${this.errorRateWindow.totalRequests})`;
      this.errorRateWindow.alertTriggered = true;
      this.triggerAlert(message);
    }
  }

  /**
   * 触发告警
   */
  private triggerAlert(message: string): void {
    // 在prodenv中，这里会发送告警通知（邮件、Slack等）
    if (this.config.enableDebugMode) {
      console.error('[ErrorMonitor ALERT]', message);
    }

    // 调用所有注册的告警回调
    this.alertCallbacks.forEach(callback => {
      try {
        callback(message);
      } catch (error) {
        console.error('Error in alert callback:', error);
      }
    });

    // note：不立即reset窗口，让调用者可以query当前error率
    // 窗口会在下timescheck时自然过期或在5min后reset
  }

  /**
   * reset过期的时间窗口
   */
  private resetWindowIfExpired(): void {
    const now = Date.now();
    if (now - this.errorRateWindow.startTime > this.WINDOW_SIZE) {
      this.errorRateWindow = {
        startTime: now,
        errorCount: 0,
        totalRequests: 0,
        alertTriggered: false,
      };
    }
  }

  /**
   * 构建error上下文
   */
  private buildErrorContext(context: Partial<ErrorContext>): ErrorContext {
    return {
      userId: context.userId || this.currentUser?.id,
      url: context.url || (typeof window !== 'undefined' ? window.location.href : ''),
      userAgent: context.userAgent || (typeof navigator !== 'undefined' ? navigator.userAgent : ''),
      timestamp: context.timestamp || new Date(),
      additionalData: context.additionalData,
    };
  }

  /**
   * 分classerrortype
   */
  private classifyError(error: Error): ErrorReport['type'] {
    const message = error.message.toLowerCase();
    
    if (message.includes('network') || message.includes('fetch') || message.includes('timeout')) {
      return 'network';
    }
    if (message.includes('validation') || message.includes('invalid')) {
      return 'validation';
    }
    if (message.includes('unauthorized') || message.includes('forbidden') || message.includes('401') || message.includes('403')) {
      return 'authorization';
    }
    if (message.includes('500') || message.includes('server')) {
      return 'server';
    }
    if (error.name === 'TypeError' || error.name === 'ReferenceError') {
      return 'client';
    }
    
    return 'unknown';
  }

  /**
   * generateerrorID
   */
  private generateErrorId(): string {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// export单例instance
let errorMonitorInstance: ErrorMonitor | null = null;

export function getErrorMonitor(config?: MonitorConfig): ErrorMonitor {
  if (!errorMonitorInstance) {
    if (!config) {
      throw new Error('ErrorMonitor config is required for first initialization');
    }
    errorMonitorInstance = new ErrorMonitor(config);
  }
  return errorMonitorInstance;
}

export function resetErrorMonitor(): void {
  errorMonitorInstance = null;
}
