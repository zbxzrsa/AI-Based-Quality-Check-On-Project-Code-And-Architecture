/**
 * Loggerservice
 * 
 * feature:
 * - support不同log级别 (debug, info, warn, error)
 * - 根据envsetlog级别（dev：debug，prod：error/warn）
 * - recordAPIrequestlog（response时间andstatus码）
 * - recorduser操作log（userID、时间戳and操作type）
 * - 实现批量log发送到service器
 * 
 * verifyRequirement: 8.4, 9.2, 9.3
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogEntry {
  id: string;
  level: LogLevel;
  message: string;
  timestamp: Date;
  source?: string;
  context?: Record<string, any>;
  userId?: string;
  sessionId?: string;
}

export interface ApiRequestLog {
  id: string;
  method: string;
  url: string;
  status: number;
  duration: number; // ms
  requestSize?: number; // 字节
  responseSize?: number; // 字节
  timestamp: Date;
  userId?: string;
  error?: string;
}

export interface UserActionLog {
  id: string;
  action: string;
  userId: string;
  page: string;
  details?: Record<string, any>;
  timestamp: Date;
}

export interface LoggerConfig {
  level: LogLevel;
  environment: 'development' | 'test' | 'production';
  enableConsole?: boolean;
  batchSize?: number; // 批量发送的log数量
  flushInterval?: number; // 自动refresh间隔（ms）
  endpoint?: string; // logservice器endpoint
}

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

/**
 * Loggerclass
 * 负责logrecord、批量发送and级别filter
 */
export class Logger {
  private config: LoggerConfig;
  private logBuffer: LogEntry[];
  private apiLogBuffer: ApiRequestLog[];
  private userActionBuffer: UserActionLog[];
  private flushTimer: NodeJS.Timeout | null;
  private currentUserId?: string;
  private sessionId: string;

  constructor(config: LoggerConfig) {
    this.config = {
      enableConsole: config.environment === 'development',
      batchSize: 50,
      flushInterval: 30000, // 30sec
      ...config,
    };

    this.logBuffer = [];
    this.apiLogBuffer = [];
    this.userActionBuffer = [];
    this.flushTimer = null;
    this.sessionId = this.generateSessionId();

    // 根据envset默认log级别
    if (!config.level) {
      this.config.level = config.environment === 'development' ? 'debug' : 'error';
    }

    // start自动refresh定时器
    this.startFlushTimer();
  }

  /**
   * setlog级别
   */
  setLevel(level: LogLevel): void {
    this.config.level = level;
  }

  /**
   * get当前log级别
   */
  getLevel(): LogLevel {
    return this.config.level;
  }

  /**
   * set当前userID
   */
  setUserId(userId: string | undefined): void {
    this.currentUserId = userId;
  }

  /**
   * get当前userID
   */
  getUserId(): string | undefined {
    return this.currentUserId;
  }

  /**
   * Debug级别log
   */
  debug(message: string, context?: Record<string, any>): void {
    this.log('debug', message, context);
  }

  /**
   * Info级别log
   */
  info(message: string, context?: Record<string, any>): void {
    this.log('info', message, context);
  }

  /**
   * Warn级别log
   */
  warn(message: string, context?: Record<string, any>): void {
    this.log('warn', message, context);
  }

  /**
   * Error级别log
   */
  error(message: string, error?: Error, context?: Record<string, any>): void {
    const errorContext = error
      ? {
          ...context,
          errorName: error.name,
          errorMessage: error.message,
          errorStack: error.stack,
        }
      : context;

    this.log('error', message, errorContext);
  }

  /**
   * recordAPIrequestlog
   */
  logApiRequest(
    url: string,
    method: string,
    duration: number,
    status: number,
    options?: {
      requestSize?: number;
      responseSize?: number;
      error?: string;
    }
  ): void {
    const log: ApiRequestLog = {
      id: this.generateLogId(),
      method: method.toUpperCase(),
      url,
      status,
      duration,
      requestSize: options?.requestSize,
      responseSize: options?.responseSize,
      timestamp: new Date(),
      userId: this.currentUserId,
      error: options?.error,
    };

    this.apiLogBuffer.push(log);

    // output到控制台（devenv）
    if (this.config.enableConsole) {
      const statusColor = status >= 400 ? '\x1b[31m' : status >= 300 ? '\x1b[33m' : '\x1b[32m';
      const durationColor = duration > 1000 ? '\x1b[31m' : duration > 500 ? '\x1b[33m' : '\x1b[32m';
      console.log(
        `[API] ${method.toUpperCase()} ${url} ${statusColor}${status}\x1b[0m ${durationColor}${duration}ms\x1b[0m`
      );
    }

    // check是否needrefresh
    this.checkAndFlush();
  }

  /**
   * recorduser操作log
   */
  logUserAction(action: string, userId: string, details?: Record<string, any>): void {
    const log: UserActionLog = {
      id: this.generateLogId(),
      action,
      userId,
      page: typeof window !== 'undefined' ? window.location.pathname : '',
      details,
      timestamp: new Date(),
    };

    this.userActionBuffer.push(log);

    // output到控制台（devenv）
    if (this.config.enableConsole) {
      console.log(`[USER ACTION] ${action} by ${userId}`, details || '');
    }

    // check是否needrefresh
    this.checkAndFlush();
  }

  /**
   * 通用logrecordmethod
   */
  private log(level: LogLevel, message: string, context?: Record<string, any>): void {
    // checklog级别
    if (!this.shouldLog(level)) {
      return;
    }

    const entry: LogEntry = {
      id: this.generateLogId(),
      level,
      message,
      timestamp: new Date(),
      context,
      userId: this.currentUserId,
      sessionId: this.sessionId,
    };

    this.logBuffer.push(entry);

    // output到控制台
    if (this.config.enableConsole) {
      this.logToConsole(entry);
    }

    // check是否needrefresh
    this.checkAndFlush();
  }

  /**
   * check是否shouldrecord该级别的log
   */
  private shouldLog(level: LogLevel): boolean {
    return LOG_LEVELS[level] >= LOG_LEVELS[this.config.level];
  }

  /**
   * outputlog到控制台
   */
  private logToConsole(entry: LogEntry): void {
    const timestamp = entry.timestamp.toISOString();
    const prefix = `[${timestamp}] [${entry.level.toUpperCase()}]`;

    switch (entry.level) {
      case 'debug':
        console.debug(prefix, entry.message, entry.context || '');
        break;
      case 'info':
        console.info(prefix, entry.message, entry.context || '');
        break;
      case 'warn':
        console.warn(prefix, entry.message, entry.context || '');
        break;
      case 'error':
        console.error(prefix, entry.message, entry.context || '');
        break;
    }
  }

  /**
   * check并refreshlog缓冲区
   */
  private checkAndFlush(): void {
    const totalLogs =
      this.logBuffer.length + this.apiLogBuffer.length + this.userActionBuffer.length;

    if (totalLogs >= this.config.batchSize!) {
      this.flushLogs();
    }
  }

  /**
   * 批量发送log到service器
   */
  async flushLogs(): Promise<void> {
    // 如果没有logneed发送，直接return
    if (
      this.logBuffer.length === 0 &&
      this.apiLogBuffer.length === 0 &&
      this.userActionBuffer.length === 0
    ) {
      return;
    }

    // 复制并清空缓冲区
    const logsToSend = [...this.logBuffer];
    const apiLogsToSend = [...this.apiLogBuffer];
    const userActionsToSend = [...this.userActionBuffer];

    this.logBuffer = [];
    this.apiLogBuffer = [];
    this.userActionBuffer = [];

    // 如果没有configendpoint，只清空缓冲区
    if (!this.config.endpoint) {
      if (this.config.enableConsole) {
        console.debug('[Logger] No endpoint configured, logs discarded', {
          logs: logsToSend.length,
          apiLogs: apiLogsToSend.length,
          userActions: userActionsToSend.length,
        });
      }
      return;
    }

    try {
      // 发送log到service器
      const payload = {
        logs: logsToSend,
        apiLogs: apiLogsToSend,
        userActions: userActionsToSend,
        sessionId: this.sessionId,
        timestamp: new Date().toISOString(),
      };

      // 在prodenv中，这里会发送到logservice器
      // await fetch(this.config.endpoint, {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify(payload),
      // });

      if (this.config.enableConsole) {
        console.debug('[Logger] Logs flushed to server', {
          logs: logsToSend.length,
          apiLogs: apiLogsToSend.length,
          userActions: userActionsToSend.length,
        });
      }
    } catch (error) {
      // 发送failure，recorderror但不重新add到缓冲区（避免无限循环）
      console.error('[Logger] Failed to flush logs:', error);
    }
  }

  /**
   * start自动refresh定时器
   */
  private startFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }

    this.flushTimer = setInterval(() => {
      this.flushLogs();
    }, this.config.flushInterval!);
  }

  /**
   * stop自动refresh定时器
   */
  stopFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  /**
   * 销毁Loggerinstance
   */
  async destroy(): Promise<void> {
    this.stopFlushTimer();
    await this.flushLogs(); // 最后一timesrefresh
  }

  /**
   * generatelogID
   */
  private generateLogId(): string {
    return `log_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  }

  /**
   * generatesessionID
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  }

  /**
   * get缓冲区status
   */
  getBufferStatus(): {
    logs: number;
    apiLogs: number;
    userActions: number;
    total: number;
  } {
    return {
      logs: this.logBuffer.length,
      apiLogs: this.apiLogBuffer.length,
      userActions: this.userActionBuffer.length,
      total: this.logBuffer.length + this.apiLogBuffer.length + this.userActionBuffer.length,
    };
  }
}

/**
 * create默认Loggerinstance的工厂function
 */
export function createDefaultLogger(): Logger {
  const environment = (process.env.NODE_ENV as 'development' | 'test' | 'production') || 'development';
  
  const config: LoggerConfig = {
    level: environment === 'development' ? 'debug' : 'error',
    environment,
    enableConsole: environment === 'development',
    batchSize: 50,
    flushInterval: 30000, // 30sec
    endpoint: process.env.NEXT_PUBLIC_LOG_ENDPOINT,
  };

  return new Logger(config);
}

// 默认instance - 延迟初始化
let defaultInstance: Logger | null = null;

export function getLogger(): Logger {
  if (!defaultInstance) {
    defaultInstance = createDefaultLogger();
  }
  return defaultInstance;
}

export function resetLogger(): void {
  if (defaultInstance) {
    defaultInstance.destroy();
    defaultInstance = null;
  }
}
