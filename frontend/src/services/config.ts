/**
 * ConfigService - Environment Configuration Management System
 * 
 * Loads, validates, and provides access to environment-specific configuration.
 * Supports development, test, and production environments.
 * 
 * Requirements: 8.1, 8.2, 8.3, 8.5, 20.1, 20.2, 20.5
 */

export interface AppConfig {
  apiBaseUrl: string;
  environment: 'development' | 'test' | 'production';
  enableDebugMode: boolean;
  sentryDsn?: string;
  cdnUrl?: string;
  features: {
    enablePWA: boolean;
    enableOfflineMode: boolean;
    enablePerformanceMonitoring: boolean;
  };
}

export interface ValidationError {
  field: string;
  message: string;
  line?: number;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

class ConfigService {
  private static instance: ConfigService;
  private config: AppConfig | null = null;

  private constructor() {}

  /**
   * Get singleton instance
   */
  static getInstance(): ConfigService {
    if (!ConfigService.instance) {
      ConfigService.instance = new ConfigService();
    }
    return ConfigService.instance;
  }

  /**
   * Load configuration based on current environment
   * Requirements: 8.1, 8.2, 20.1
   */
  static load(): AppConfig {
    const instance = ConfigService.getInstance();
    
    if (instance.config) {
      return instance.config;
    }

    // Check required environment variables first
    ConfigService.checkRequiredEnvVars();

    // Determine environment
    const env = (process.env.NODE_ENV || 'development') as AppConfig['environment'];
    
    // Load environment-specific configuration
    const config: AppConfig = {
      apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
      environment: env,
      enableDebugMode: env === 'development',
      sentryDsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
      cdnUrl: process.env.NEXT_PUBLIC_CDN_URL,
      features: {
        enablePWA: process.env.NEXT_PUBLIC_ENABLE_PWA === 'true',
        enableOfflineMode: process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE === 'true',
        enablePerformanceMonitoring: process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING === 'true',
      },
    };

    // Validate configuration
    const validationResult = ConfigService.validate(config);
    if (!validationResult.valid) {
      const errorMessages = validationResult.errors
        .map(err => `${err.field}: ${err.message}`)
        .join('\n');
      throw new Error(
        `Configuration validation failed:\n${errorMessages}\n\nApplication cannot start with invalid configuration.`
      );
    }

    instance.config = config;
    return config;
  }

  /**
   * Validate configuration object
   * Requirements: 8.5, 20.2, 20.5
   */
  static validate(config: Partial<AppConfig>): ValidationResult {
    const errors: ValidationError[] = [];

    // Validate required fields
    if (!config.apiBaseUrl) {
      errors.push({
        field: 'apiBaseUrl',
        message: 'API base URL is required',
      });
    } else if (!ConfigService.isValidUrl(config.apiBaseUrl)) {
      errors.push({
        field: 'apiBaseUrl',
        message: 'API base URL must be a valid URL',
      });
    }

    if (!config.environment) {
      errors.push({
        field: 'environment',
        message: 'Environment is required',
      });
    } else if (!['development', 'test', 'production'].includes(config.environment)) {
      errors.push({
        field: 'environment',
        message: 'Environment must be one of: development, test, production',
      });
    }

    if (typeof config.enableDebugMode !== 'boolean') {
      errors.push({
        field: 'enableDebugMode',
        message: 'enableDebugMode must be a boolean',
      });
    }

    // Validate optional fields if present
    if (config.sentryDsn && !ConfigService.isValidUrl(config.sentryDsn)) {
      errors.push({
        field: 'sentryDsn',
        message: 'Sentry DSN must be a valid URL',
      });
    }

    if (config.cdnUrl && !ConfigService.isValidUrl(config.cdnUrl)) {
      errors.push({
        field: 'cdnUrl',
        message: 'CDN URL must be a valid URL',
      });
    }

    // Validate features object
    if (!config.features) {
      errors.push({
        field: 'features',
        message: 'Features configuration is required',
      });
    } else {
      if (typeof config.features.enablePWA !== 'boolean') {
        errors.push({
          field: 'features.enablePWA',
          message: 'features.enablePWA must be a boolean',
        });
      }
      if (typeof config.features.enableOfflineMode !== 'boolean') {
        errors.push({
          field: 'features.enableOfflineMode',
          message: 'features.enableOfflineMode must be a boolean',
        });
      }
      if (typeof config.features.enablePerformanceMonitoring !== 'boolean') {
        errors.push({
          field: 'features.enablePerformanceMonitoring',
          message: 'features.enablePerformanceMonitoring must be a boolean',
        });
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Get configuration value by key
   */
  static get<K extends keyof AppConfig>(key: K): AppConfig[K] {
    const instance = ConfigService.getInstance();
    
    if (!instance.config) {
      instance.config = ConfigService.load();
    }

    return instance.config[key];
  }

  /**
   * Check that all required environment variables are set
   * Requirements: 8.3, 8.5
   */
  static checkRequiredEnvVars(): void {
    const requiredVars = [
      'NEXT_PUBLIC_API_BASE_URL',
    ];

    const missing: string[] = [];

    for (const varName of requiredVars) {
      if (!process.env[varName]) {
        missing.push(varName);
      }
    }

    if (missing.length > 0) {
      throw new Error(
        `Missing required environment variables:\n${missing.join('\n')}\n\n` +
        `Please set these variables in your .env file or environment.\n` +
        `Application cannot start without required configuration.`
      );
    }
  }

  /**
   * Helper to validate URL format
   */
  private static isValidUrl(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Parse configuration from string format (for testing/tooling)
   * Requirements: 20.1
   */
  static parseConfig(configString: string): AppConfig {
    try {
      const parsed = JSON.parse(configString);
      const validationResult = ConfigService.validate(parsed);
      
      if (!validationResult.valid) {
        throw new Error(
          `Invalid configuration format:\n${validationResult.errors
            .map(err => `Line ${err.line || '?'}: ${err.field} - ${err.message}`)
            .join('\n')}`
        );
      }
      
      return parsed as AppConfig;
    } catch (error) {
      if (error instanceof SyntaxError) {
        throw new Error(
          `Configuration file format is invalid:\nLine ${(error as any).lineNumber || '?'}: ${error.message}`
        );
      }
      throw error;
    }
  }

  /**
   * Format configuration object to string
   * Requirements: 20.3
   */
  static formatConfig(config: AppConfig): string {
    return JSON.stringify(config, null, 2);
  }

  /**
   * Reset configuration (useful for testing)
   */
  static reset(): void {
    const instance = ConfigService.getInstance();
    instance.config = null;
  }
}

export default ConfigService;
