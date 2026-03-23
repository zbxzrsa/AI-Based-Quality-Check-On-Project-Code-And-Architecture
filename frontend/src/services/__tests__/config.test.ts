/**
 * Unit tests for ConfigService
 * Tests specific examples and edge cases for configuration management
 */

import fc from 'fast-check';
import ConfigService, { AppConfig } from '../config';

describe('ConfigService', () => {
  // Store original env
  const originalEnv = { ...process.env };

  beforeEach(() => {
    // Reset config before each test
    ConfigService.reset();
    
    // Reset environment variables
    jest.resetModules();
    Object.keys(process.env).forEach(key => {
      if (key.startsWith('NEXT_PUBLIC_')) {
        delete process.env[key];
      }
    });
    Object.assign(process.env, originalEnv);
  });

  afterAll(() => {
    // Restore original env
    Object.keys(process.env).forEach(key => {
      if (key.startsWith('NEXT_PUBLIC_')) {
        delete process.env[key];
      }
    });
    Object.assign(process.env, originalEnv);
  });

  describe('load', () => {
    it('should load valid configuration from environment variables', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
      process.env.NEXT_PUBLIC_ENABLE_PWA = 'false';
      process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE = 'false';
      process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING = 'true';

      const config = ConfigService.load();

      expect(config.apiBaseUrl).toBe('http://localhost:8000');
      expect(config.environment).toBe('test'); // Jest sets NODE_ENV to 'test'
      expect(config.enableDebugMode).toBe(false); // test environment has debug mode off
      expect(config.features.enablePWA).toBe(false);
      expect(config.features.enablePerformanceMonitoring).toBe(true);
    });

    it('should throw error when required environment variables are missing', () => {
      delete process.env.NEXT_PUBLIC_API_BASE_URL;

      expect(() => ConfigService.load()).toThrow(
        /Missing required environment variables/
      );
    });

    it('should throw error when configuration validation fails', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'invalid-url';

      expect(() => ConfigService.load()).toThrow(
        /Configuration validation failed/
      );
    });

    it('should return cached configuration on subsequent calls', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
      process.env.NEXT_PUBLIC_ENABLE_PWA = 'false';
      process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE = 'false';
      process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING = 'true';

      const config1 = ConfigService.load();
      const config2 = ConfigService.load();

      expect(config1).toBe(config2); // Same instance
    });

    it('should set enableDebugMode to true in development', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
      process.env.NEXT_PUBLIC_ENABLE_PWA = 'false';
      process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE = 'false';
      process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING = 'true';

      // Mock NODE_ENV for this test
      const originalNodeEnv = process.env.NODE_ENV;
      (process.env as any).NODE_ENV = 'development';

      const config = ConfigService.load();

      expect(config.enableDebugMode).toBe(true);

      // Restore
      (process.env as any).NODE_ENV = originalNodeEnv;
      ConfigService.reset();
    });

    it('should set enableDebugMode to false in production', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
      process.env.NEXT_PUBLIC_ENABLE_PWA = 'true';
      process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE = 'true';
      process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING = 'true';

      // Mock NODE_ENV for this test
      const originalNodeEnv = process.env.NODE_ENV;
      (process.env as any).NODE_ENV = 'production';

      const config = ConfigService.load();

      expect(config.enableDebugMode).toBe(false);

      // Restore
      (process.env as any).NODE_ENV = originalNodeEnv;
      ConfigService.reset();
    });

    it('should load optional configuration when provided', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
      process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://sentry.io/123';
      process.env.NEXT_PUBLIC_CDN_URL = 'https://cdn.example.com';
      process.env.NEXT_PUBLIC_ENABLE_PWA = 'true';
      process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE = 'true';
      process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING = 'true';

      const config = ConfigService.load();

      expect(config.sentryDsn).toBe('https://sentry.io/123');
      expect(config.cdnUrl).toBe('https://cdn.example.com');
    });
  });

  describe('validate', () => {
    it('should validate a complete valid configuration', () => {
      const config: AppConfig = {
        apiBaseUrl: 'http://localhost:8000',
        environment: 'development',
        enableDebugMode: true,
        features: {
          enablePWA: false,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      };

      const result = ConfigService.validate(config);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should return error for missing apiBaseUrl', () => {
      const config = {
        environment: 'development',
        enableDebugMode: true,
        features: {
          enablePWA: false,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      } as Partial<AppConfig>;

      const result = ConfigService.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContainEqual({
        field: 'apiBaseUrl',
        message: 'API base URL is required',
      });
    });

    it('should return error for invalid apiBaseUrl', () => {
      const config = {
        apiBaseUrl: 'not-a-valid-url',
        environment: 'development',
        enableDebugMode: true,
        features: {
          enablePWA: false,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      } as Partial<AppConfig>;

      const result = ConfigService.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContainEqual({
        field: 'apiBaseUrl',
        message: 'API base URL must be a valid URL',
      });
    });

    it('should return error for invalid environment', () => {
      const config = {
        apiBaseUrl: 'http://localhost:8000',
        environment: 'invalid' as 'development' | 'test' | 'production',
        enableDebugMode: true,
        features: {
          enablePWA: false,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      };

      const result = ConfigService.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContainEqual({
        field: 'environment',
        message: 'Environment must be one of: development, test, production',
      });
    });

    it('should return error for non-boolean enableDebugMode', () => {
      const config = {
        apiBaseUrl: 'http://localhost:8000',
        environment: 'development' as const,
        enableDebugMode: 'true' as any,
        features: {
          enablePWA: false,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      };

      const result = ConfigService.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContainEqual({
        field: 'enableDebugMode',
        message: 'enableDebugMode must be a boolean',
      });
    });

    it('should return error for missing features', () => {
      const config = {
        apiBaseUrl: 'http://localhost:8000',
        environment: 'development',
        enableDebugMode: true,
      } as Partial<AppConfig>;

      const result = ConfigService.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContainEqual({
        field: 'features',
        message: 'Features configuration is required',
      });
    });

    it('should return error for non-boolean feature flags', () => {
      const config = {
        apiBaseUrl: 'http://localhost:8000',
        environment: 'development' as const,
        enableDebugMode: true,
        features: {
          enablePWA: 'false' as any,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      };

      const result = ConfigService.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContainEqual({
        field: 'features.enablePWA',
        message: 'features.enablePWA must be a boolean',
      });
    });

    it('should return error for invalid optional sentryDsn', () => {
      const config = {
        apiBaseUrl: 'http://localhost:8000',
        environment: 'production',
        enableDebugMode: false,
        sentryDsn: 'not-a-valid-url',
        features: {
          enablePWA: true,
          enableOfflineMode: true,
          enablePerformanceMonitoring: true,
        },
      } as Partial<AppConfig>;

      const result = ConfigService.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContainEqual({
        field: 'sentryDsn',
        message: 'Sentry DSN must be a valid URL',
      });
    });

    it('should return multiple errors for multiple invalid fields', () => {
      const config = {
        apiBaseUrl: 'invalid-url',
        environment: 'invalid' as any,
        enableDebugMode: 'true' as any,
        features: {
          enablePWA: 'false' as any,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      };

      const result = ConfigService.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(1);
    });
  });

  describe('get', () => {
    it('should return configuration value by key', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
      process.env.NEXT_PUBLIC_ENABLE_PWA = 'false';
      process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE = 'false';
      process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING = 'true';

      const apiBaseUrl = ConfigService.get('apiBaseUrl');
      const environment = ConfigService.get('environment');
      const features = ConfigService.get('features');

      expect(apiBaseUrl).toBe('http://localhost:8000');
      expect(environment).toBe('test'); // Jest sets NODE_ENV to 'test'
      expect(features.enablePerformanceMonitoring).toBe(true);
    });

    it('should load configuration if not already loaded', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
      process.env.NEXT_PUBLIC_ENABLE_PWA = 'false';
      process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE = 'false';
      process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING = 'true';

      // Don't call load() first
      const apiBaseUrl = ConfigService.get('apiBaseUrl');

      expect(apiBaseUrl).toBe('http://localhost:8000');
    });
  });

  describe('checkRequiredEnvVars', () => {
    it('should not throw when all required variables are set', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';

      expect(() => ConfigService.checkRequiredEnvVars()).not.toThrow();
    });

    it('should throw when required variables are missing', () => {
      delete process.env.NEXT_PUBLIC_API_BASE_URL;

      expect(() => ConfigService.checkRequiredEnvVars()).toThrow(
        /Missing required environment variables/
      );
    });

    it('should list all missing variables in error message', () => {
      delete process.env.NEXT_PUBLIC_API_BASE_URL;

      expect(() => ConfigService.checkRequiredEnvVars()).toThrow(
        /NEXT_PUBLIC_API_BASE_URL/
      );
    });
  });

  describe('parseConfig', () => {
    it('should parse valid JSON configuration', () => {
      const configString = JSON.stringify({
        apiBaseUrl: 'http://localhost:8000',
        environment: 'development',
        enableDebugMode: true,
        features: {
          enablePWA: false,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      });

      const config = ConfigService.parseConfig(configString);

      expect(config.apiBaseUrl).toBe('http://localhost:8000');
      expect(config.environment).toBe('development');
    });

    it('should throw error for invalid JSON', () => {
      const configString = '{ invalid json }';

      expect(() => ConfigService.parseConfig(configString)).toThrow(
        /Configuration file format is invalid/
      );
    });

    it('should throw error for invalid configuration structure', () => {
      const configString = JSON.stringify({
        apiBaseUrl: 'invalid-url',
        environment: 'development',
        enableDebugMode: true,
        features: {
          enablePWA: false,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      });

      expect(() => ConfigService.parseConfig(configString)).toThrow(
        /Invalid configuration format/
      );
    });
  });

  describe('formatConfig', () => {
    it('should format configuration to JSON string', () => {
      const config: AppConfig = {
        apiBaseUrl: 'http://localhost:8000',
        environment: 'development',
        enableDebugMode: true,
        features: {
          enablePWA: false,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      };

      const formatted = ConfigService.formatConfig(config);
      const parsed = JSON.parse(formatted);

      expect(parsed).toEqual(config);
    });

    it('should format with proper indentation', () => {
      const config: AppConfig = {
        apiBaseUrl: 'http://localhost:8000',
        environment: 'development',
        enableDebugMode: true,
        features: {
          enablePWA: false,
          enableOfflineMode: false,
          enablePerformanceMonitoring: true,
        },
      };

      const formatted = ConfigService.formatConfig(config);

      expect(formatted).toContain('\n');
      expect(formatted).toContain('  ');
    });
  });

  describe('reset', () => {
    it('should clear cached configuration', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
      process.env.NEXT_PUBLIC_ENABLE_PWA = 'false';
      process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE = 'false';
      process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING = 'true';

      const config1 = ConfigService.load();
      ConfigService.reset();
      const config2 = ConfigService.load();

      expect(config1).not.toBe(config2); // Different instances
      expect(config1).toEqual(config2); // But same values
    });
  });

  describe('edge cases', () => {
    it('should handle empty string environment variables', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = '';

      expect(() => ConfigService.load()).toThrow();
    });

    it('should handle whitespace-only environment variables', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = '   ';

      expect(() => ConfigService.load()).toThrow();
    });

    it('should handle case-sensitive boolean strings', () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
      process.env.NEXT_PUBLIC_ENABLE_PWA = 'TRUE'; // uppercase
      process.env.NEXT_PUBLIC_ENABLE_OFFLINE_MODE = 'false';
      process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING = 'true';

      const config = ConfigService.load();

      // 'TRUE' !== 'true', so should be false
      expect(config.features.enablePWA).toBe(false);
    });
  });
});


/**
 * Property-Based Tests for ConfigService
 * Tests universal properties that should hold for all valid inputs
 */

/**
 * Custom arbitrary for generating valid AppConfig objects
 */
function configArbitrary(): fc.Arbitrary<AppConfig> {
  return fc.record({
    apiBaseUrl: fc.webUrl(),
    environment: fc.constantFrom('development' as const, 'test' as const, 'production' as const),
    enableDebugMode: fc.boolean(),
    sentryDsn: fc.option(fc.webUrl(), { nil: undefined }),
    cdnUrl: fc.option(fc.webUrl(), { nil: undefined }),
    features: fc.record({
      enablePWA: fc.boolean(),
      enableOfflineMode: fc.boolean(),
      enablePerformanceMonitoring: fc.boolean(),
    }),
  });
}

describe('Property-Based Tests', () => {
  beforeEach(() => {
    ConfigService.reset();
  });

  /**
   * Feature: frontend-production-optimization, Property 35: config往返一致性
   * **Validates: Requirements 20.4**
   * 
   * For any valid Configuration object, performing parse → format → parse again
   * should produce an equivalent object.
   */
  describe('Property 35: Configuration Round-Trip Consistency', () => {
    it('should maintain equivalence after parse → format → parse cycle for any valid configuration', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (originalConfig) => {
            // Step 1: Format the original config to string
            const formatted = ConfigService.formatConfig(originalConfig);
            
            // Step 2: Parse the formatted string back to object
            const parsed = ConfigService.parseConfig(formatted);
            
            // Step 3: Format again
            const reformatted = ConfigService.formatConfig(parsed);
            
            // Step 4: Parse again
            const reparsed = ConfigService.parseConfig(reformatted);
            
            // Verify: The reparsed object should be equivalent to the original
            expect(reparsed).toEqual(originalConfig);
            
            // Also verify the intermediate parsed object matches
            expect(parsed).toEqual(originalConfig);
            
            // Verify the formatted strings are identical (stable formatting)
            expect(reformatted).toBe(formatted);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should preserve all required fields through round-trip', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            const formatted = ConfigService.formatConfig(config);
            const parsed = ConfigService.parseConfig(formatted);
            const reformatted = ConfigService.formatConfig(parsed);
            const reparsed = ConfigService.parseConfig(reformatted);
            
            // Verify all required fields are preserved
            expect(reparsed.apiBaseUrl).toBe(config.apiBaseUrl);
            expect(reparsed.environment).toBe(config.environment);
            expect(reparsed.enableDebugMode).toBe(config.enableDebugMode);
            expect(reparsed.features.enablePWA).toBe(config.features.enablePWA);
            expect(reparsed.features.enableOfflineMode).toBe(config.features.enableOfflineMode);
            expect(reparsed.features.enablePerformanceMonitoring).toBe(config.features.enablePerformanceMonitoring);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should preserve optional fields through round-trip when present', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            const formatted = ConfigService.formatConfig(config);
            const parsed = ConfigService.parseConfig(formatted);
            const reformatted = ConfigService.formatConfig(parsed);
            const reparsed = ConfigService.parseConfig(reformatted);
            
            // Verify optional fields are preserved when present
            expect(reparsed.sentryDsn).toBe(config.sentryDsn);
            expect(reparsed.cdnUrl).toBe(config.cdnUrl);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should maintain type correctness through round-trip', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            const formatted = ConfigService.formatConfig(config);
            const parsed = ConfigService.parseConfig(formatted);
            const reformatted = ConfigService.formatConfig(parsed);
            const reparsed = ConfigService.parseConfig(reformatted);
            
            // Verify types are preserved
            expect(typeof reparsed.apiBaseUrl).toBe('string');
            expect(typeof reparsed.environment).toBe('string');
            expect(typeof reparsed.enableDebugMode).toBe('boolean');
            expect(typeof reparsed.features.enablePWA).toBe('boolean');
            expect(typeof reparsed.features.enableOfflineMode).toBe('boolean');
            expect(typeof reparsed.features.enablePerformanceMonitoring).toBe('boolean');
            
            if (reparsed.sentryDsn !== undefined) {
              expect(typeof reparsed.sentryDsn).toBe('string');
            }
            if (reparsed.cdnUrl !== undefined) {
              expect(typeof reparsed.cdnUrl).toBe('string');
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should produce idempotent formatting after first round-trip', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            // First round-trip
            const formatted1 = ConfigService.formatConfig(config);
            const parsed1 = ConfigService.parseConfig(formatted1);
            
            // Second round-trip
            const formatted2 = ConfigService.formatConfig(parsed1);
            const parsed2 = ConfigService.parseConfig(formatted2);
            
            // Third round-trip
            const formatted3 = ConfigService.formatConfig(parsed2);
            const parsed3 = ConfigService.parseConfig(formatted3);
            
            // All formatted strings should be identical
            expect(formatted2).toBe(formatted1);
            expect(formatted3).toBe(formatted1);
            
            // All parsed objects should be equivalent
            expect(parsed2).toEqual(parsed1);
            expect(parsed3).toEqual(parsed1);
            expect(parsed3).toEqual(config);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Feature: frontend-production-optimization, Property 36: configformat化正确性
   * **Validates: Requirements 20.3**
   * 
   * For any Configuration object, the formatting tool should be able to convert it
   * back to a valid configuration file format.
   */
  describe('Property 36: Configuration Formatting Correctness', () => {
    it('should format any valid Configuration object to valid JSON string', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            // Format the config to a string
            const formatted = ConfigService.formatConfig(config);
            
            // Verify it's valid JSON by parsing it
            let parsed;
            expect(() => {
              parsed = JSON.parse(formatted);
            }).not.toThrow();
            
            // Verify the parsed object matches the original config
            expect(parsed).toEqual(config);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should format configuration with proper JSON structure', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            const formatted = ConfigService.formatConfig(config);
            
            // Verify it's a string
            expect(typeof formatted).toBe('string');
            
            // Verify it's not empty
            expect(formatted.length).toBeGreaterThan(0);
            
            // Verify it contains valid JSON structure markers
            expect(formatted).toMatch(/^\{/); // Starts with {
            expect(formatted).toMatch(/\}$/); // Ends with }
            
            // Verify it's parseable
            const parsed = JSON.parse(formatted);
            expect(typeof parsed).toBe('object');
            expect(parsed).not.toBeNull();
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should format configuration with all required fields present in output', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            const formatted = ConfigService.formatConfig(config);
            
            // Verify all required fields are present in the formatted string
            expect(formatted).toContain('apiBaseUrl');
            expect(formatted).toContain('environment');
            expect(formatted).toContain('enableDebugMode');
            expect(formatted).toContain('features');
            expect(formatted).toContain('enablePWA');
            expect(formatted).toContain('enableOfflineMode');
            expect(formatted).toContain('enablePerformanceMonitoring');
            
            // Verify the formatted string can be parsed and validated
            const parsed = JSON.parse(formatted);
            const validationResult = ConfigService.validate(parsed);
            expect(validationResult.valid).toBe(true);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should format configuration preserving optional fields when present', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            const formatted = ConfigService.formatConfig(config);
            const parsed = JSON.parse(formatted);
            
            // Verify optional fields are preserved when present
            if (config.sentryDsn !== undefined) {
              expect(formatted).toContain('sentryDsn');
              expect(parsed.sentryDsn).toBe(config.sentryDsn);
            }
            
            if (config.cdnUrl !== undefined) {
              expect(formatted).toContain('cdnUrl');
              expect(parsed.cdnUrl).toBe(config.cdnUrl);
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should format configuration with consistent indentation', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            const formatted = ConfigService.formatConfig(config);
            
            // Verify the output has proper indentation (2 spaces as per implementation)
            expect(formatted).toContain('\n');
            expect(formatted).toContain('  '); // Should have 2-space indentation
            
            // Verify it's human-readable (not minified)
            const lines = formatted.split('\n');
            expect(lines.length).toBeGreaterThan(1);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should format configuration that can be used with parseConfig', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            // Format the config
            const formatted = ConfigService.formatConfig(config);
            
            // Verify parseConfig can successfully parse the formatted output
            let parsed: AppConfig | undefined;
            expect(() => {
              parsed = ConfigService.parseConfig(formatted);
            }).not.toThrow();
            
            // Verify the parsed config is valid
            const validationResult = ConfigService.validate(parsed!);
            expect(validationResult.valid).toBe(true);
            expect(validationResult.errors).toHaveLength(0);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should format configuration preserving data types', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            const formatted = ConfigService.formatConfig(config);
            const parsed = JSON.parse(formatted);
            
            // Verify boolean types are preserved (not converted to strings)
            expect(typeof parsed.enableDebugMode).toBe('boolean');
            expect(typeof parsed.features.enablePWA).toBe('boolean');
            expect(typeof parsed.features.enableOfflineMode).toBe('boolean');
            expect(typeof parsed.features.enablePerformanceMonitoring).toBe('boolean');
            
            // Verify string types are preserved
            expect(typeof parsed.apiBaseUrl).toBe('string');
            expect(typeof parsed.environment).toBe('string');
            
            // Verify object structure is preserved
            expect(typeof parsed.features).toBe('object');
            expect(parsed.features).not.toBeNull();
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Feature: frontend-production-optimization, Property 34: config解析正确性
   * **Validates: Requirements 20.1**
   * 
   * For any valid configuration file, it should be correctly parsed into a Configuration object,
   * and all field values should match the configuration file.
   */
  describe('Property 34: Configuration Parsing Correctness', () => {
    it('should correctly parse any valid configuration string into Configuration object with matching field values', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            // Format the config to a string (simulating a configuration file)
            const configString = ConfigService.formatConfig(config);
            
            // Parse the string back to a Configuration object
            const parsed = ConfigService.parseConfig(configString);
            
            // Verify all fields match exactly
            expect(parsed.apiBaseUrl).toBe(config.apiBaseUrl);
            expect(parsed.environment).toBe(config.environment);
            expect(parsed.enableDebugMode).toBe(config.enableDebugMode);
            expect(parsed.sentryDsn).toBe(config.sentryDsn);
            expect(parsed.cdnUrl).toBe(config.cdnUrl);
            expect(parsed.features.enablePWA).toBe(config.features.enablePWA);
            expect(parsed.features.enableOfflineMode).toBe(config.features.enableOfflineMode);
            expect(parsed.features.enablePerformanceMonitoring).toBe(config.features.enablePerformanceMonitoring);
            
            // Verify the entire object structure matches
            expect(parsed).toEqual(config);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should correctly parse configuration with only required fields', () => {
      fc.assert(
        fc.property(
          fc.record({
            apiBaseUrl: fc.webUrl(),
            environment: fc.constantFrom('development' as const, 'test' as const, 'production' as const),
            enableDebugMode: fc.boolean(),
            features: fc.record({
              enablePWA: fc.boolean(),
              enableOfflineMode: fc.boolean(),
              enablePerformanceMonitoring: fc.boolean(),
            }),
          }),
          (config) => {
            const configString = ConfigService.formatConfig(config as AppConfig);
            const parsed = ConfigService.parseConfig(configString);
            
            // Verify required fields are present and correct
            expect(parsed.apiBaseUrl).toBe(config.apiBaseUrl);
            expect(parsed.environment).toBe(config.environment);
            expect(parsed.enableDebugMode).toBe(config.enableDebugMode);
            expect(parsed.features).toEqual(config.features);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should correctly parse configuration with optional fields', () => {
      fc.assert(
        fc.property(
          configArbitrary(),
          (config) => {
            // Only test when optional fields are present
            if (config.sentryDsn || config.cdnUrl) {
              const configString = ConfigService.formatConfig(config);
              const parsed = ConfigService.parseConfig(configString);
              
              // Verify optional fields are preserved correctly
              if (config.sentryDsn) {
                expect(parsed.sentryDsn).toBe(config.sentryDsn);
              }
              if (config.cdnUrl) {
                expect(parsed.cdnUrl).toBe(config.cdnUrl);
              }
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should correctly parse configuration for all environment types', () => {
      fc.assert(
        fc.property(
          fc.constantFrom('development' as const, 'test' as const, 'production' as const),
          fc.webUrl(),
          fc.boolean(),
          fc.boolean(),
          fc.boolean(),
          fc.boolean(),
          (environment, apiBaseUrl, enableDebugMode, enablePWA, enableOfflineMode, enablePerformanceMonitoring) => {
            const config: AppConfig = {
              apiBaseUrl,
              environment,
              enableDebugMode,
              features: {
                enablePWA,
                enableOfflineMode,
                enablePerformanceMonitoring,
              },
            };
            
            const configString = ConfigService.formatConfig(config);
            const parsed = ConfigService.parseConfig(configString);
            
            // Verify environment is correctly parsed
            expect(parsed.environment).toBe(environment);
            expect(['development', 'test', 'production']).toContain(parsed.environment);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should correctly parse configuration with all boolean combinations for features', () => {
      fc.assert(
        fc.property(
          fc.webUrl(),
          fc.boolean(),
          fc.boolean(),
          fc.boolean(),
          fc.boolean(),
          (apiBaseUrl, enablePWA, enableOfflineMode, enablePerformanceMonitoring, enableDebugMode) => {
            const config: AppConfig = {
              apiBaseUrl,
              environment: 'development',
              enableDebugMode,
              features: {
                enablePWA,
                enableOfflineMode,
                enablePerformanceMonitoring,
              },
            };
            
            const configString = ConfigService.formatConfig(config);
            const parsed = ConfigService.parseConfig(configString);
            
            // Verify all boolean values are correctly parsed
            expect(parsed.features.enablePWA).toBe(enablePWA);
            expect(parsed.features.enableOfflineMode).toBe(enableOfflineMode);
            expect(parsed.features.enablePerformanceMonitoring).toBe(enablePerformanceMonitoring);
            expect(parsed.enableDebugMode).toBe(enableDebugMode);
            
            // Verify types are boolean, not strings
            expect(typeof parsed.features.enablePWA).toBe('boolean');
            expect(typeof parsed.features.enableOfflineMode).toBe('boolean');
            expect(typeof parsed.features.enablePerformanceMonitoring).toBe('boolean');
            expect(typeof parsed.enableDebugMode).toBe('boolean');
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
