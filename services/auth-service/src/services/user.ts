import { User, UserPreferences } from '@shared/types';
import { DatabaseService } from './database';
import { PermissionService } from './permissions';
import { PasswordService } from '../utils/password';
import { logger } from '../utils/logger';

export interface CreateUserRequest {
  email: string;
  name: string;
  password: string;
  roles?: string[];
}

export interface UpdateUserRequest {
  name?: string;
  preferences?: Partial<UserPreferences>;
  roles?: string[];
}

export class UserService {
  /**
   * Create a new user
   */
  static async createUser(request: CreateUserRequest): Promise<User> {
    logger.info('Creating new user:', request.email);

    // Validate password strength
    const passwordValidation = PasswordService.validatePasswordStrength(request.password);
    if (!passwordValidation.isValid) {
      throw new Error(`Password validation failed: ${passwordValidation.errors.join(', ')}`);
    }

    // Hash password
    const hashedPassword = await PasswordService.hashPassword(request.password);

    // Create default roles if none specified
    const roleNames = request.roles || ['programmer'];
    const roles = roleNames.map(roleName => 
      PermissionService.createRole(roleName as 'administrator' | 'programmer' | 'visitor')
    );

    // Create default preferences
    const defaultPreferences: UserPreferences = {
      theme: 'light',
      notifications: {
        email: true,
        inApp: true,
        webhooks: false,
      },
      analysisSettings: {
        enabledRules: [],
        qualityThresholds: [],
        preferredAIModel: 'gpt-4',
      },
    };

    const user: User = {
      id: this.generateUserId(),
      email: request.email,
      name: request.name,
      roles,
      preferences: defaultPreferences,
      lastLogin: new Date(),
    };

    // Store user in database
    await this.storeUser(user, hashedPassword);

    logger.info('User created successfully:', user.id);
    return user;
  }

  /**
   * Get user by ID
   */
  static async getUserById(userId: string): Promise<User | null> {
    logger.debug('Getting user by ID:', userId);

    try {
      const db = DatabaseService.getClient();
      const result = await db.query(
        'SELECT * FROM users WHERE id = $1',
        [userId]
      );

      if (result.rows.length === 0) {
        return null;
      }

      const userData = result.rows[0];
      return this.mapDatabaseRowToUser(userData);
    } catch (error) {
      logger.error('Failed to get user by ID:', error);
      throw new Error('Failed to retrieve user');
    }
  }

  /**
   * Get user by email
   */
  static async getUserByEmail(email: string): Promise<User | null> {
    logger.debug('Getting user by email:', email);

    try {
      const db = DatabaseService.getClient();
      const result = await db.query(
        'SELECT * FROM users WHERE email = $1',
        [email]
      );

      if (result.rows.length === 0) {
        return null;
      }

      const userData = result.rows[0];
      return this.mapDatabaseRowToUser(userData);
    } catch (error) {
      logger.error('Failed to get user by email:', error);
      throw new Error('Failed to retrieve user');
    }
  }

  /**
   * Verify user credentials
   */
  static async verifyCredentials(email: string, password: string): Promise<User | null> {
    logger.debug('Verifying credentials for:', email);

    try {
      const db = DatabaseService.getClient();
      const result = await db.query(
        'SELECT * FROM users WHERE email = $1',
        [email]
      );

      if (result.rows.length === 0) {
        logger.debug('User not found:', email);
        return null;
      }

      const userData = result.rows[0];
      const isPasswordValid = await PasswordService.verifyPassword(password, userData.password_hash);

      if (!isPasswordValid) {
        logger.debug('Invalid password for user:', email);
        return null;
      }

      // Update last login
      await this.updateLastLogin(userData.id);

      return this.mapDatabaseRowToUser(userData);
    } catch (error) {
      logger.error('Failed to verify credentials:', error);
      throw new Error('Failed to verify credentials');
    }
  }

  /**
   * Update user information
   */
  static async updateUser(userId: string, updates: UpdateUserRequest): Promise<User> {
    logger.info('Updating user:', userId);

    const user = await this.getUserById(userId);
    if (!user) {
      throw new Error('User not found');
    }

    // Update roles if provided
    if (updates.roles) {
      user.roles = updates.roles.map(roleName => 
        PermissionService.createRole(roleName as 'administrator' | 'programmer' | 'visitor')
      );
    }

    // Update name if provided
    if (updates.name) {
      user.name = updates.name;
    }

    // Update preferences if provided
    if (updates.preferences) {
      user.preferences = { ...user.preferences, ...updates.preferences };
    }

    // Store updated user
    await this.storeUser(user);

    logger.info('User updated successfully:', userId);
    return user;
  }

  /**
   * Delete user
   */
  static async deleteUser(userId: string): Promise<void> {
    logger.info('Deleting user:', userId);

    try {
      const db = DatabaseService.getClient();
      await db.query('DELETE FROM users WHERE id = $1', [userId]);
      logger.info('User deleted successfully:', userId);
    } catch (error) {
      logger.error('Failed to delete user:', error);
      throw new Error('Failed to delete user');
    }
  }

  /**
   * Store user in database
   */
  private static async storeUser(user: User, passwordHash?: string): Promise<void> {
    try {
      const db = DatabaseService.getClient();
      
      if (passwordHash) {
        // Insert new user
        await db.query(
          `INSERT INTO users (id, email, name, roles, preferences, password_hash, last_login, created_at, updated_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
           ON CONFLICT (id) DO UPDATE SET
           name = $3, roles = $4, preferences = $5, updated_at = NOW()`,
          [
            user.id,
            user.email,
            user.name,
            JSON.stringify(user.roles),
            JSON.stringify(user.preferences),
            passwordHash,
            user.lastLogin,
          ]
        );
      } else {
        // Update existing user
        await db.query(
          `UPDATE users SET name = $2, roles = $3, preferences = $4, updated_at = NOW()
           WHERE id = $1`,
          [
            user.id,
            user.name,
            JSON.stringify(user.roles),
            JSON.stringify(user.preferences),
          ]
        );
      }
    } catch (error) {
      logger.error('Failed to store user:', error);
      throw new Error('Failed to store user');
    }
  }

  /**
   * Update last login timestamp
   */
  private static async updateLastLogin(userId: string): Promise<void> {
    try {
      const db = DatabaseService.getClient();
      await db.query(
        'UPDATE users SET last_login = NOW() WHERE id = $1',
        [userId]
      );
    } catch (error) {
      logger.error('Failed to update last login:', error);
      // Don't throw error for this non-critical operation
    }
  }

  /**
   * Map database row to User object
   */
  private static mapDatabaseRowToUser(row: any): User {
    return {
      id: row.id,
      email: row.email,
      name: row.name,
      roles: JSON.parse(row.roles),
      preferences: JSON.parse(row.preferences),
      lastLogin: new Date(row.last_login),
    };
  }

  /**
   * Generate a unique user ID
   */
  private static generateUserId(): string {
    return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}