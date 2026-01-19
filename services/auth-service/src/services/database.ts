import { Pool } from 'pg';
import { config } from '../config';
import { logger } from '../utils/logger';

export class DatabaseService {
  private static pool: Pool;

  static async initialize(): Promise<void> {
    try {
      this.pool = new Pool({
        connectionString: config.database.url,
        max: 20,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 2000,
      });

      // Test the connection
      const client = await this.pool.connect();
      await client.query('SELECT NOW()');
      client.release();

      // Initialize schema
      await this.initializeSchema();

      logger.info('Database connection established successfully');
    } catch (error) {
      logger.error('Failed to initialize database connection:', error);
      throw error;
    }
  }

  static async close(): Promise<void> {
    if (this.pool) {
      await this.pool.end();
      logger.info('Database connection closed');
    }
  }

  static getClient(): Pool {
    if (!this.pool) {
      throw new Error('Database not initialized');
    }
    return this.pool;
  }

  static async query(text: string, params?: unknown[]): Promise<any> {
    if (!this.pool) {
      throw new Error('Database not initialized');
    }
    return this.pool.query(text, params);
  }

  static async healthCheck(): Promise<boolean> {
    try {
      if (!this.pool) {
        return false;
      }
      const result = await this.pool.query('SELECT 1');
      return result.rows.length > 0;
    } catch (error) {
      logger.error('Database health check failed:', error);
      return false;
    }
  }

  private static async initializeSchema(): Promise<void> {
    try {
      logger.info('Initializing database schema...');

      // Create users table
      await this.pool.query(`
        CREATE TABLE IF NOT EXISTS users (
          id VARCHAR(255) PRIMARY KEY,
          email VARCHAR(255) UNIQUE NOT NULL,
          name VARCHAR(255) NOT NULL,
          password_hash VARCHAR(255) NOT NULL,
          roles JSONB NOT NULL DEFAULT '[]',
          preferences JSONB NOT NULL DEFAULT '{}',
          last_login TIMESTAMP WITH TIME ZONE,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
      `);

      // Create indexes for better performance
      await this.pool.query(`
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
      `);

      await this.pool.query(`
        CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login)
      `);

      // Create sessions table for additional session tracking (optional)
      await this.pool.query(`
        CREATE TABLE IF NOT EXISTS user_sessions (
          id VARCHAR(255) PRIMARY KEY,
          user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          token_hash VARCHAR(255) NOT NULL,
          expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
      `);

      await this.pool.query(`
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)
      `);

      await this.pool.query(`
        CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at)
      `);

      // Create audit log table for security events
      await this.pool.query(`
        CREATE TABLE IF NOT EXISTS auth_audit_log (
          id SERIAL PRIMARY KEY,
          user_id VARCHAR(255),
          event_type VARCHAR(100) NOT NULL,
          event_data JSONB,
          ip_address INET,
          user_agent TEXT,
          success BOOLEAN NOT NULL,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
      `);

      await this.pool.query(`
        CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON auth_audit_log(user_id)
      `);

      await this.pool.query(`
        CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON auth_audit_log(event_type)
      `);

      await this.pool.query(`
        CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON auth_audit_log(created_at)
      `);

      logger.info('Database schema initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize database schema:', error);
      throw error;
    }
  }
}