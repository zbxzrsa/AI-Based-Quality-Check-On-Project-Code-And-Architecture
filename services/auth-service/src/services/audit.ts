import { DatabaseService } from './database';
import { logger } from '../utils/logger';

export interface AuditEvent {
  userId?: string;
  eventType: string;
  eventData?: Record<string, unknown>;
  ipAddress?: string;
  userAgent?: string;
  success: boolean;
}

export class AuditService {
  /**
   * Log an authentication event
   */
  static async logAuthEvent(event: AuditEvent): Promise<void> {
    try {
      await DatabaseService.query(
        `INSERT INTO auth_audit_log (user_id, event_type, event_data, ip_address, user_agent, success)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [
          event.userId || null,
          event.eventType,
          event.eventData ? JSON.stringify(event.eventData) : null,
          event.ipAddress || null,
          event.userAgent || null,
          event.success,
        ]
      );

      logger.info('Audit event logged:', {
        eventType: event.eventType,
        userId: event.userId,
        success: event.success,
      });
    } catch (error) {
      logger.error('Failed to log audit event:', error);
      // Don't throw error to avoid breaking the main flow
    }
  }

  /**
   * Log successful login
   */
  static async logSuccessfulLogin(
    userId: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<void> {
    const event: AuditEvent = {
      userId,
      eventType: 'LOGIN_SUCCESS',
      success: true,
    };
    if (ipAddress) event.ipAddress = ipAddress;
    if (userAgent) event.userAgent = userAgent;
    
    await this.logAuthEvent(event);
  }

  /**
   * Log failed login attempt
   */
  static async logFailedLogin(
    email: string,
    reason: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<void> {
    const event: AuditEvent = {
      eventType: 'LOGIN_FAILED',
      eventData: { email, reason },
      success: false,
    };
    if (ipAddress) event.ipAddress = ipAddress;
    if (userAgent) event.userAgent = userAgent;
    
    await this.logAuthEvent(event);
  }

  /**
   * Log token refresh
   */
  static async logTokenRefresh(
    userId: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<void> {
    const event: AuditEvent = {
      userId,
      eventType: 'TOKEN_REFRESH',
      success: true,
    };
    if (ipAddress) event.ipAddress = ipAddress;
    if (userAgent) event.userAgent = userAgent;
    
    await this.logAuthEvent(event);
  }

  /**
   * Log logout
   */
  static async logLogout(
    userId: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<void> {
    const event: AuditEvent = {
      userId,
      eventType: 'LOGOUT',
      success: true,
    };
    if (ipAddress) event.ipAddress = ipAddress;
    if (userAgent) event.userAgent = userAgent;
    
    await this.logAuthEvent(event);
  }

  /**
   * Log authorization failure
   */
  static async logAuthorizationFailure(
    userId: string,
    resource: string,
    action: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<void> {
    const event: AuditEvent = {
      userId,
      eventType: 'AUTHORIZATION_DENIED',
      eventData: { resource, action },
      success: false,
    };
    if (ipAddress) event.ipAddress = ipAddress;
    if (userAgent) event.userAgent = userAgent;
    
    await this.logAuthEvent(event);
  }

  /**
   * Log password change
   */
  static async logPasswordChange(
    userId: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<void> {
    const event: AuditEvent = {
      userId,
      eventType: 'PASSWORD_CHANGE',
      success: true,
    };
    if (ipAddress) event.ipAddress = ipAddress;
    if (userAgent) event.userAgent = userAgent;
    
    await this.logAuthEvent(event);
  }

  /**
   * Log account creation
   */
  static async logAccountCreation(
    userId: string,
    email: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<void> {
    const event: AuditEvent = {
      userId,
      eventType: 'ACCOUNT_CREATED',
      eventData: { email },
      success: true,
    };
    if (ipAddress) event.ipAddress = ipAddress;
    if (userAgent) event.userAgent = userAgent;
    
    await this.logAuthEvent(event);
  }

  /**
   * Log role change
   */
  static async logRoleChange(
    userId: string,
    oldRoles: string[],
    newRoles: string[],
    changedBy: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<void> {
    const event: AuditEvent = {
      userId,
      eventType: 'ROLE_CHANGE',
      eventData: { oldRoles, newRoles, changedBy },
      success: true,
    };
    if (ipAddress) event.ipAddress = ipAddress;
    if (userAgent) event.userAgent = userAgent;
    
    await this.logAuthEvent(event);
  }

  /**
   * Get audit logs for a user
   */
  static async getUserAuditLogs(
    userId: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<any[]> {
    try {
      const result = await DatabaseService.query(
        `SELECT * FROM auth_audit_log 
         WHERE user_id = $1 
         ORDER BY created_at DESC 
         LIMIT $2 OFFSET $3`,
        [userId, limit, offset]
      );

      return result.rows;
    } catch (error) {
      logger.error('Failed to get user audit logs:', error);
      throw new Error('Failed to retrieve audit logs');
    }
  }

  /**
   * Get recent security events
   */
  static async getRecentSecurityEvents(
    eventTypes: string[] = ['LOGIN_FAILED', 'AUTHORIZATION_DENIED'],
    limit: number = 100
  ): Promise<any[]> {
    try {
      const result = await DatabaseService.query(
        `SELECT * FROM auth_audit_log 
         WHERE event_type = ANY($1) AND success = false
         ORDER BY created_at DESC 
         LIMIT $2`,
        [eventTypes, limit]
      );

      return result.rows;
    } catch (error) {
      logger.error('Failed to get recent security events:', error);
      throw new Error('Failed to retrieve security events');
    }
  }

  /**
   * Clean up old audit logs (for maintenance)
   */
  static async cleanupOldLogs(daysToKeep: number = 90): Promise<number> {
    try {
      const result = await DatabaseService.query(
        `DELETE FROM auth_audit_log 
         WHERE created_at < NOW() - INTERVAL '${daysToKeep} days'`
      );

      const deletedCount = result.rowCount || 0;
      logger.info(`Cleaned up ${deletedCount} old audit log entries`);
      return deletedCount;
    } catch (error) {
      logger.error('Failed to cleanup old audit logs:', error);
      throw new Error('Failed to cleanup audit logs');
    }
  }
}