/**
 * Loggerpropertytest
 * 
 * Feature: frontend-production-optimization
 * Property 37: APIrequestlogrecord
 * 
 * **Validates: Requirements 9.2**
 * 
 * testCoverage:
 * - 对于任何APIrequest，shouldrecordcontainresponse时间andstatus码的log
 */

import fc from 'fast-check';
import { Logger, LoggerConfig, ApiRequestLog, UserActionLog } from '../Logger';

describe('Property 37: APIrequestlogrecord', () => {
  let consoleLogSpy: jest.SpyInstance;
  let consoleDebugSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();
  });

  afterEach(() => {
    consoleLogSpy.mockRestore();
    consoleDebugSpy.mockRestore();
  });

  // customGenerator：generateHTTPmethod
  const httpMethodArbitrary = () =>
    fc.constantFrom('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS');

  // customGenerator：generateHTTPstatus码
  const httpStatusArbitrary = () =>
    fc.constantFrom(
      200, 201, 204, 301, 302, 304, 400, 401, 403, 404, 422, 429, 500, 502, 503, 504
    );

  // customGenerator：generateresponse时间（ms）
  const durationArbitrary = () =>
    fc.integer({ min: 1, max: 10000 });

  // customGenerator：generateURL
  const urlArbitrary = () =>
    fc.oneof(
      fc.webUrl(),
      fc.string({ minLength: 1, maxLength: 100 }).map(path => `/api/${path}`),
      fc.string({ minLength: 1, maxLength: 50 }).map(path => `/v1/${path}`)
    );

  // customGenerator：generateLoggerconfig
  const loggerConfigArbitrary = () =>
    fc.record({
      level: fc.constantFrom('debug', 'info', 'warn', 'error'),
      environment: fc.constantFrom('development', 'test', 'production'),
      enableConsole: fc.boolean(),
      batchSize: fc.integer({ min: 10, max: 100 }),
      flushInterval: fc.integer({ min: 1000, max: 60000 }),
    });

  it('should为所有APIrequestrecordcontainresponse时间andstatus码的log', () => {
    fc.assert(
      fc.property(
        loggerConfigArbitrary(),
        urlArbitrary(),
        httpMethodArbitrary(),
        durationArbitrary(),
        httpStatusArbitrary(),
        (config, url, method, duration, status) => {
          // createLoggerinstance
          const logger = new Logger({
            ...config,
            enableConsole: true, // 强制启用控制台output以便verify
          });

          // recordAPIrequest
          logger.logApiRequest(url, method, duration, status);

          // get缓冲区status
          const bufferStatus = logger.getBufferStatus();

          // verifyAPIlog被add到缓冲区（requirement9.2）
          expect(bufferStatus.apiLogs).toBeGreaterThan(0);

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should为所有APIrequestgeneratecontain必需field的log条目', () => {
    fc.assert(
      fc.property(
        urlArbitrary(),
        httpMethodArbitrary(),
        durationArbitrary(),
        httpStatusArbitrary(),
        (url, method, duration, status) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          // recordAPIrequest
          logger.logApiRequest(url, method, duration, status);

          // 通过反射访问私有缓冲区来verifylogcontent
          const apiLogBuffer = (logger as any).apiLogBuffer as ApiRequestLog[];
          expect(apiLogBuffer.length).toBeGreaterThan(0);

          const lastLog = apiLogBuffer[apiLogBuffer.length - 1];

          // verifylogcontain所有必需field（requirement9.2）
          expect(lastLog).toMatchObject({
            id: expect.stringMatching(/^log_\d+_[a-z0-9]+$/),
            method: method.toUpperCase(),
            url: url,
            status: status,
            duration: duration,
            timestamp: expect.any(Date),
          });

          // verifyresponse时间andstatus码被正确record
          expect(lastLog.duration).toBe(duration);
          expect(lastLog.status).toBe(status);

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should为所有APIrequestgenerate唯一的logID', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            url: urlArbitrary(),
            method: httpMethodArbitrary(),
            duration: durationArbitrary(),
            status: httpStatusArbitrary(),
          }),
          { minLength: 2, maxLength: 20 }
        ),
        (requests) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 1000,
          });

          // record所有APIrequest
          requests.forEach(({ url, method, duration, status }) => {
            logger.logApiRequest(url, method, duration, status);
          });

          // get所有logID
          const apiLogBuffer = (logger as any).apiLogBuffer as ApiRequestLog[];
          const logIds = apiLogBuffer.map(log => log.id);

          // verify所有ID都是唯一的
          const uniqueIds = new Set(logIds);
          expect(uniqueIds.size).toBe(logIds.length);

          // verify所有ID都符合format
          logIds.forEach(id => {
            expect(id).toMatch(/^log_\d+_[a-z0-9]+$/);
          });

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should正确recordHTTPmethod（转换为大写）', () => {
    fc.assert(
      fc.property(
        urlArbitrary(),
        fc.constantFrom('get', 'post', 'put', 'delete', 'patch', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH'),
        durationArbitrary(),
        httpStatusArbitrary(),
        (url, method, duration, status) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          logger.logApiRequest(url, method, duration, status);

          const apiLogBuffer = (logger as any).apiLogBuffer as ApiRequestLog[];
          const lastLog = apiLogBuffer[apiLogBuffer.length - 1];

          // verifymethod被转换为大写
          expect(lastLog.method).toBe(method.toUpperCase());

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldBeAtAPIlog中contain可选的requestandresponse大小', () => {
    fc.assert(
      fc.property(
        urlArbitrary(),
        httpMethodArbitrary(),
        durationArbitrary(),
        httpStatusArbitrary(),
        fc.option(fc.integer({ min: 0, max: 1000000 }), { nil: undefined }),
        fc.option(fc.integer({ min: 0, max: 10000000 }), { nil: undefined }),
        (url, method, duration, status, requestSize, responseSize) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          logger.logApiRequest(url, method, duration, status, {
            requestSize,
            responseSize,
          });

          const apiLogBuffer = (logger as any).apiLogBuffer as ApiRequestLog[];
          const lastLog = apiLogBuffer[apiLogBuffer.length - 1];

          // verify可选field被正确record
          if (requestSize !== undefined) {
            expect(lastLog.requestSize).toBe(requestSize);
          }
          if (responseSize !== undefined) {
            expect(lastLog.responseSize).toBe(responseSize);
          }

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldBeAtAPIlog中containerrorinfo（如果provide）', () => {
    fc.assert(
      fc.property(
        urlArbitrary(),
        httpMethodArbitrary(),
        durationArbitrary(),
        fc.constantFrom(400, 401, 403, 404, 500, 502, 503),
        fc.option(fc.string({ minLength: 1, maxLength: 200 }), { nil: undefined }),
        (url, method, duration, status, errorMessage) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          logger.logApiRequest(url, method, duration, status, {
            error: errorMessage,
          });

          const apiLogBuffer = (logger as any).apiLogBuffer as ApiRequestLog[];
          const lastLog = apiLogBuffer[apiLogBuffer.length - 1];

          // verifyerrorinfo被正确record
          if (errorMessage !== undefined) {
            expect(lastLog.error).toBe(errorMessage);
          }

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldBeAtAPIlog中contain当前userID（如果已set）', () => {
    fc.assert(
      fc.property(
        fc.option(fc.string({ minLength: 1, maxLength: 50 }), { nil: undefined }),
        urlArbitrary(),
        httpMethodArbitrary(),
        durationArbitrary(),
        httpStatusArbitrary(),
        (userId, url, method, duration, status) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          // setuserID（如果provide）
          if (userId !== undefined) {
            logger.setUserId(userId);
          }

          logger.logApiRequest(url, method, duration, status);

          const apiLogBuffer = (logger as any).apiLogBuffer as ApiRequestLog[];
          const lastLog = apiLogBuffer[apiLogBuffer.length - 1];

          // verifyuserID被contain在log中
          if (userId !== undefined) {
            expect(lastLog.userId).toBe(userId);
          } else {
            expect(lastLog.userId).toBeUndefined();
          }

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldBeAt达到批量大hour触发logrefresh', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 5, max: 20 }),
        (batchSize) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: batchSize,
            flushInterval: 60000, // 长时间间隔，避免自动refresh
          });

          // record足够多的APIrequest以触发refresh
          for (let i = 0; i < batchSize; i++) {
            logger.logApiRequest(`/api/test/${i}`, 'GET', 100, 200);
          }

          // verify缓冲区在达到批量大小后被清空
          const bufferStatus = logger.getBufferStatus();
          expect(bufferStatus.total).toBeLessThan(batchSize);

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should为所有APIrequestrecord时间戳', () => {
    fc.assert(
      fc.property(
        urlArbitrary(),
        httpMethodArbitrary(),
        durationArbitrary(),
        httpStatusArbitrary(),
        (url, method, duration, status) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          const beforeTimestamp = new Date();
          logger.logApiRequest(url, method, duration, status);
          const afterTimestamp = new Date();

          const apiLogBuffer = (logger as any).apiLogBuffer as ApiRequestLog[];
          const lastLog = apiLogBuffer[apiLogBuffer.length - 1];

          // verify时间戳在合理范围内
          expect(lastLog.timestamp).toBeInstanceOf(Date);
          expect(lastLog.timestamp.getTime()).toBeGreaterThanOrEqual(beforeTimestamp.getTime());
          expect(lastLog.timestamp.getTime()).toBeLessThanOrEqual(afterTimestamp.getTime());

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldBeAtdevenv中outputAPIrequestlog到控制台', () => {
    fc.assert(
      fc.property(
        urlArbitrary(),
        httpMethodArbitrary(),
        durationArbitrary(),
        httpStatusArbitrary(),
        (url, method, duration, status) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'development',
            enableConsole: true,
            batchSize: 100,
          });

          logger.logApiRequest(url, method, duration, status);

          // verify控制台output被调用
          expect(consoleLogSpy).toHaveBeenCalled();

          // verifyoutputcontain关键info
          const logCall = consoleLogSpy.mock.calls.find(call => 
            call[0].includes('[API]') && 
            call[0].includes(method.toUpperCase()) &&
            call[0].includes(url)
          );
          expect(logCall).toBeDefined();

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });
});


/**
 * Loggerpropertytest - user操作log
 * 
 * Feature: frontend-production-optimization
 * Property 38: user操作logrecord
 * 
 * **Validates: Requirements 9.3**
 * 
 * testCoverage:
 * - 对于任何关键user操作，shouldrecordcontainuserID、时间戳and操作type的log
 */

describe('Property 38: user操作logrecord', () => {
  let consoleLogSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
  });

  afterEach(() => {
    consoleLogSpy.mockRestore();
  });

  // customGenerator：generateuserID
  const userIdArbitrary = () =>
    fc.oneof(
      fc.uuid(),
      fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0),
      fc.integer({ min: 1, max: 999999 }).map(n => `user_${n}`)
    );

  // customGenerator：generate操作type
  const actionArbitrary = () =>
    fc.oneof(
      fc.constantFrom(
        'login',
        'logout',
        'create_project',
        'delete_project',
        'update_project',
        'approve_pr',
        'reject_pr',
        'submit_analysis',
        'export_data',
        'change_settings'
      ),
      fc.string({ minLength: 1, maxLength: 100 }).filter(s => s.trim().length > 0)
    );

  // customGenerator：generate操作detail
  const detailsArbitrary = () =>
    fc.option(
      fc.record({
        projectId: fc.option(fc.uuid(), { nil: undefined }),
        prId: fc.option(fc.integer({ min: 1, max: 10000 }), { nil: undefined }),
        targetId: fc.option(fc.string({ minLength: 1, maxLength: 50 }), { nil: undefined }),
        metadata: fc.option(fc.object(), { nil: undefined }),
      }),
      { nil: undefined }
    );

  it('should为所有user操作recordcontainuserID、时间戳and操作type的log', () => {
    fc.assert(
      fc.property(
        userIdArbitrary(),
        actionArbitrary(),
        detailsArbitrary(),
        (userId, action, details) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          // recorduser操作
          logger.logUserAction(action, userId, details);

          // 通过反射访问私有缓冲区来verifylogcontent
          const userActionBuffer = (logger as any).userActionBuffer as UserActionLog[];
          expect(userActionBuffer.length).toBeGreaterThan(0);

          const lastLog = userActionBuffer[userActionBuffer.length - 1];

          // verifylogcontain所有必需field（requirement9.3）
          expect(lastLog).toMatchObject({
            id: expect.stringMatching(/^log_\d+_[a-z0-9]+$/),
            action: action,
            userId: userId,
            timestamp: expect.any(Date),
          });

          // verifyuserID、时间戳and操作type被正确record
          expect(lastLog.userId).toBe(userId);
          expect(lastLog.action).toBe(action);
          expect(lastLog.timestamp).toBeInstanceOf(Date);

          // verifydetail被正确record（如果provide）
          if (details !== undefined) {
            expect(lastLog.details).toEqual(details);
          }

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should为所有user操作generate唯一的logID', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            userId: userIdArbitrary(),
            action: actionArbitrary(),
            details: detailsArbitrary(),
          }),
          { minLength: 2, maxLength: 20 }
        ),
        (userActions) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 1000,
          });

          // record所有user操作
          userActions.forEach(({ userId, action, details }) => {
            logger.logUserAction(action, userId, details);
          });

          // get所有logID
          const userActionBuffer = (logger as any).userActionBuffer as UserActionLog[];
          const logIds = userActionBuffer.map(log => log.id);

          // verify所有ID都是唯一的
          const uniqueIds = new Set(logIds);
          expect(uniqueIds.size).toBe(logIds.length);

          // verify所有ID都符合format
          logIds.forEach(id => {
            expect(id).toMatch(/^log_\d+_[a-z0-9]+$/);
          });

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should为所有user操作record时间戳', () => {
    fc.assert(
      fc.property(
        userIdArbitrary(),
        actionArbitrary(),
        detailsArbitrary(),
        (userId, action, details) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          const beforeTimestamp = new Date();
          logger.logUserAction(action, userId, details);
          const afterTimestamp = new Date();

          const userActionBuffer = (logger as any).userActionBuffer as UserActionLog[];
          const lastLog = userActionBuffer[userActionBuffer.length - 1];

          // verify时间戳在合理范围内
          expect(lastLog.timestamp).toBeInstanceOf(Date);
          expect(lastLog.timestamp.getTime()).toBeGreaterThanOrEqual(beforeTimestamp.getTime());
          expect(lastLog.timestamp.getTime()).toBeLessThanOrEqual(afterTimestamp.getTime());

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldBeAtuser操作log中contain当前页面path', () => {
    fc.assert(
      fc.property(
        userIdArbitrary(),
        actionArbitrary(),
        detailsArbitrary(),
        (userId, action, details) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          logger.logUserAction(action, userId, details);

          const userActionBuffer = (logger as any).userActionBuffer as UserActionLog[];
          const lastLog = userActionBuffer[userActionBuffer.length - 1];

          // verify页面path被record（在testenv中可能为空字符串）
          expect(lastLog.page).toBeDefined();
          expect(typeof lastLog.page).toBe('string');

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldBeAtdevenv中outputuser操作log到控制台', () => {
    fc.assert(
      fc.property(
        userIdArbitrary(),
        actionArbitrary(),
        detailsArbitrary(),
        (userId, action, details) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'development',
            enableConsole: true,
            batchSize: 100,
          });

          logger.logUserAction(action, userId, details);

          // verify控制台output被调用
          expect(consoleLogSpy).toHaveBeenCalled();

          // verifyoutputcontain关键info
          const logCall = consoleLogSpy.mock.calls.find(call => 
            call[0].includes('[USER ACTION]') && 
            call[0].includes(action) &&
            call[0].includes(userId)
          );
          expect(logCall).toBeDefined();

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldBeAt达到批量大hour触发user操作logrefresh', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 5, max: 20 }),
        (batchSize) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: batchSize,
            flushInterval: 60000, // 长时间间隔，避免自动refresh
          });

          // record足够多的user操作以触发refresh
          for (let i = 0; i < batchSize; i++) {
            logger.logUserAction(`action_${i}`, `user_${i}`);
          }

          // verify缓冲区在达到批量大小后被清空
          const bufferStatus = logger.getBufferStatus();
          expect(bufferStatus.total).toBeLessThan(batchSize);

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should正确handlecontain特殊字符的userIDand操作type', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        fc.string({ minLength: 1, maxLength: 100 }),
        (userId, action) => {
          // skip空白字符串
          if (userId.trim().length === 0 || action.trim().length === 0) {
            return true;
          }

          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          logger.logUserAction(action, userId);

          const userActionBuffer = (logger as any).userActionBuffer as UserActionLog[];
          const lastLog = userActionBuffer[userActionBuffer.length - 1];

          // verify特殊字符被正确save
          expect(lastLog.userId).toBe(userId);
          expect(lastLog.action).toBe(action);

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldsupport在user操作log中contain复杂的detailobject', () => {
    fc.assert(
      fc.property(
        userIdArbitrary(),
        actionArbitrary(),
        fc.object({ maxDepth: 2 }),
        (userId, action, details) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 100,
          });

          logger.logUserAction(action, userId, details);

          const userActionBuffer = (logger as any).userActionBuffer as UserActionLog[];
          const lastLog = userActionBuffer[userActionBuffer.length - 1];

          // verifydetailobject被正确record
          expect(lastLog.details).toEqual(details);

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should为不同user的相同操作create独立的log条目', () => {
    fc.assert(
      fc.property(
        fc.array(userIdArbitrary(), { minLength: 2, maxLength: 10 }),
        actionArbitrary(),
        (userIds, action) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 1000,
          });

          // 多itemuserexecute相同操作
          userIds.forEach(userId => {
            logger.logUserAction(action, userId);
          });

          const userActionBuffer = (logger as any).userActionBuffer as UserActionLog[];

          // verify为每itemusercreate了独立的log条目
          expect(userActionBuffer.length).toBe(userIds.length);

          // verify每itemlog条目的userID正确
          userActionBuffer.forEach((log, index) => {
            expect(log.userId).toBe(userIds[index]);
            expect(log.action).toBe(action);
          });

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('shouldBeAt混合logtype时正确维护user操作log缓冲区', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.oneof(
            fc.record({
              type: fc.constant('userAction' as const),
              userId: userIdArbitrary(),
              action: actionArbitrary(),
            }),
            fc.record({
              type: fc.constant('apiRequest' as const),
              url: fc.webUrl(),
              method: fc.constantFrom('GET', 'POST', 'PUT', 'DELETE'),
              duration: fc.integer({ min: 1, max: 5000 }),
              status: fc.integer({ min: 200, max: 599 }),
            })
          ),
          { minLength: 5, maxLength: 20 }
        ),
        (logs) => {
          const logger = new Logger({
            level: 'debug',
            environment: 'test',
            enableConsole: false,
            batchSize: 1000,
          });

          // record混合type的log
          logs.forEach(log => {
            if (log.type === 'userAction') {
              logger.logUserAction(log.action, log.userId);
            } else {
              logger.logApiRequest(log.url, log.method, log.duration, log.status);
            }
          });

          // verifyuser操作log数量正确
          const userActionBuffer = (logger as any).userActionBuffer as UserActionLog[];
          const expectedUserActionCount = logs.filter(l => l.type === 'userAction').length;
          expect(userActionBuffer.length).toBe(expectedUserActionCount);

          // verify所有user操作log都contain必需field
          userActionBuffer.forEach(log => {
            expect(log.id).toMatch(/^log_\d+_[a-z0-9]+$/);
            expect(log.userId).toBeDefined();
            expect(log.action).toBeDefined();
            expect(log.timestamp).toBeInstanceOf(Date);
          });

          // cleanup
          logger.stopFlushTimer();
        }
      ),
      { numRuns: 100 }
    );
  });
});
