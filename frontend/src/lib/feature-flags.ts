/**
 * Feature Flags Service
 * 
 * Manages feature flags for progressive migration and A/B testing.
 * Supports:
 * - Global feature flags
 * - User-based feature flags with percentage rollout
 * - Audit logging of flag changes
 * - Persistence to localStorage
 * 
 * Requirements: 10.1, 10.2, 10.6
 */

interface FeatureFlag {
  key: string;
  enabled: boolean;
  description: string;
  rolloutPercentage?: number;
  abTestVariants?: string[]; // Optional A/B test variant names (e.g., ['control', 'variant-a', 'variant-b'])
}

interface ABTestMetric {
  flagKey: string;
  userId: string;
  variant: string;
  timestamp: string;
  eventType: 'impression' | 'interaction' | 'conversion';
  metadata?: Record<string, unknown>;
}

interface ABTestStats {
  flagKey: string;
  totalUsers: number;
  variantStats: Record<string, {
    userCount: number;
    impressions: number;
    interactions: number;
    conversions: number;
  }>;
}

interface FeatureFlagsConfig {
  flags: Record<string, FeatureFlag>;
}

interface FlagChangeLog {
  timestamp: string;
  flagKey: string;
  oldValue: boolean;
  newValue: boolean;
  userId?: string;
}

class FeatureFlagsService {
  private flags: Map<string, FeatureFlag>;
  private readonly STORAGE_KEY = 'feature-flags';
  private readonly METRICS_STORAGE_KEY = 'feature-flags-metrics';
  private readonly VARIANT_ASSIGNMENTS_KEY = 'feature-flags-variant-assignments';
  
  constructor() {
    this.flags = new Map();
    this.loadFlags();
  }
  
  /**
   * Load feature flags from localStorage
   */
  private loadFlags(): void {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const flags = JSON.parse(stored);
        Object.entries(flags).forEach(([key, flag]) => {
          this.flags.set(key, flag as FeatureFlag);
        });
      }
    } catch (error) {
      console.error('Failed to load feature flags from localStorage:', error);
    }
    
    // Set default flags
    this.setDefaultFlags();
  }
  
  /**
   * Set default feature flags
   */
  private setDefaultFlags(): void {
    const defaults: FeatureFlag[] = [
      {
        key: 'use-production-api',
        enabled: false,
        description: 'Use production environment API',
        rolloutPercentage: 0,
      },
      {
        key: 'architecture-graph-production',
        enabled: false,
        description: 'Architecture graph uses production API',
        rolloutPercentage: 0,
      },
      {
        key: 'dependency-graph-production',
        enabled: false,
        description: 'Dependency graph uses production API',
        rolloutPercentage: 0,
      },
      {
        key: 'neo4j-graph-production',
        enabled: false,
        description: 'Neo4j graph uses production API',
        rolloutPercentage: 0,
      },
      {
        key: 'performance-dashboard-production',
        enabled: false,
        description: 'Performance dashboard uses production API',
        rolloutPercentage: 0,
      },
    ];
    
    defaults.forEach(flag => {
      if (!this.flags.has(flag.key)) {
        this.flags.set(flag.key, flag);
      }
    });
    
    // Save defaults to localStorage
    this.saveFlags();
  }
  
  /**
   * Check if a feature flag is enabled globally
   * @param flagKey - The feature flag key
   * @returns true if the flag is enabled, false otherwise
   */
  isEnabled(flagKey: string): boolean {
    const flag = this.flags.get(flagKey);
    return flag?.enabled ?? false;
  }
  
  /**
   * Check if a feature flag is enabled for a specific user
   * Supports percentage-based rollout using user ID hashing
   * @param flagKey - The feature flag key
   * @param userId - The user ID
   * @returns true if the flag is enabled for this user, false otherwise
   */
  isEnabledForUser(flagKey: string, userId: string): boolean {
    const flag = this.flags.get(flagKey);
    if (!flag) return false;
    
    if (!flag.enabled) return false;
    
    // If rollout percentage is set, use user ID hash to determine eligibility
    if (flag.rolloutPercentage !== undefined && flag.rolloutPercentage < 100) {
      const hash = this.hashUserId(userId);
      return hash < flag.rolloutPercentage;
    }
    
    return true;
  }
  
  /**
   * Get all feature flags
   * @returns Record of all feature flags
   */
  getAllFlags(): Record<string, FeatureFlag> {
    return Object.fromEntries(this.flags);
  }
  
  /**
   * Set a feature flag's enabled state
   * Persists to localStorage and logs the change
   * If the flag doesn't exist, it will be created
   * @param flagKey - The feature flag key
   * @param enabled - The new enabled state
   */
  setFlag(flagKey: string, enabled: boolean): void {
    let flag = this.flags.get(flagKey);
    if (flag) {
      const oldValue = flag.enabled;
      flag.enabled = enabled;
      this.flags.set(flagKey, flag);
      this.saveFlags();
      
      // Log audit trail
      this.logFlagChange(flagKey, oldValue, enabled);
    } else {
      // Create new flag if it doesn't exist
      flag = {
        key: flagKey,
        enabled,
        description: `Feature flag: ${flagKey}`,
        rolloutPercentage: 100,
      };
      this.flags.set(flagKey, flag);
      this.saveFlags();
      
      // Log audit trail
      this.logFlagChange(flagKey, false, enabled);
    }
  }
  
  /**
   * Set the rollout percentage for a feature flag
   * If the flag doesn't exist, it will be created
   * @param flagKey - The feature flag key
   * @param percentage - The rollout percentage (0-100)
   */
  setRolloutPercentage(flagKey: string, percentage: number): void {
    if (percentage < 0 || percentage > 100) {
      console.error('Rollout percentage must be between 0 and 100');
      return;
    }
    
    let flag = this.flags.get(flagKey);
    if (flag) {
      flag.rolloutPercentage = percentage;
      this.flags.set(flagKey, flag);
      this.saveFlags();
    } else {
      // Create new flag if it doesn't exist
      flag = {
        key: flagKey,
        enabled: false,
        description: `Feature flag: ${flagKey}`,
        rolloutPercentage: percentage,
      };
      this.flags.set(flagKey, flag);
      this.saveFlags();
    }
  }
  
  /**
   * Save feature flags to localStorage
   */
  private saveFlags(): void {
    try {
      const flagsObj = Object.fromEntries(this.flags);
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(flagsObj));
    } catch (error) {
      console.error('Failed to save feature flags to localStorage:', error);
    }
  }
  
  /**
   * Log feature flag changes for audit purposes
   * Sends audit log to backend and stores locally
   * @param flagKey - The feature flag key
   * @param oldValue - The previous enabled state
   * @param newValue - The new enabled state
   */
  private logFlagChange(flagKey: string, oldValue: boolean, newValue: boolean): void {
    const log: FlagChangeLog = {
      timestamp: new Date().toISOString(),
      flagKey,
      oldValue,
      newValue,
      userId: this.getCurrentUserId(),
    };
    
    // Store locally
    this.storeAuditLog(log);
    
    // Send to backend (fire and forget)
    this.sendAuditLogToBackend(log).catch(error => {
      console.error('Failed to send audit log to backend:', error);
    });
  }
  
  /**
   * Store audit log locally
   */
  private storeAuditLog(log: FlagChangeLog): void {
    try {
      const logs = this.getAuditLogs();
      logs.push(log);
      
      // Keep only last 100 logs
      if (logs.length > 100) {
        logs.splice(0, logs.length - 100);
      }
      
      localStorage.setItem('feature-flags-audit', JSON.stringify(logs));
    } catch (error) {
      console.error('Failed to store audit log:', error);
    }
  }
  
  /**
   * Get audit logs from localStorage
   */
  getAuditLogs(): FlagChangeLog[] {
    try {
      const stored = localStorage.getItem('feature-flags-audit');
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Failed to load audit logs:', error);
      return [];
    }
  }
  
  /**
   * Send audit log to backend
   */
  private async sendAuditLogToBackend(log: FlagChangeLog): Promise<void> {
    // Only send if we have an API client available
    if (typeof window !== 'undefined' && (window as any).apiClient) {
      const apiClient = (window as any).apiClient;
      await apiClient.post('/api/v1/audit/feature-flags', log);
    }
  }
  
  /**
   * Get current user ID from session/auth context
   */
  private getCurrentUserId(): string | undefined {
    // Try to get user ID from various sources
    try {
      // Check localStorage for user session
      const userSession = localStorage.getItem('user-session');
      if (userSession) {
        const session = JSON.parse(userSession);
        return session.userId || session.id;
      }
      
      // Check if auth context is available
      if (typeof window !== 'undefined' && (window as any).currentUser) {
        return (window as any).currentUser.id;
      }
    } catch (error) {
      console.error('Failed to get current user ID:', error);
    }
    
    return undefined;
  }
  
  /**
   * Hash user ID to a number between 0-99
   * Used for percentage-based rollout
   * @param userId - The user ID to hash
   * @returns A number between 0 and 99
   */
  private hashUserId(userId: string): number {
    let hash = 0;
    for (let i = 0; i < userId.length; i++) {
      hash = ((hash << 5) - hash) + userId.charCodeAt(i);
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash) % 100;
  }
  
  /**
   * Reset all feature flags to defaults
   * Useful for testing or troubleshooting
   */
  resetToDefaults(): void {
    this.flags.clear();
    localStorage.removeItem(this.STORAGE_KEY);
    this.setDefaultFlags();
  }
  
  /**
   * Export feature flags configuration
   * Useful for backup or sharing configuration
   */
  exportConfig(): string {
    return JSON.stringify(Object.fromEntries(this.flags), null, 2);
  }
  
  /**
   * Import feature flags configuration
   * @param config - JSON string of feature flags configuration
   */
  importConfig(config: string): void {
    try {
      const flags = JSON.parse(config);
      Object.entries(flags).forEach(([key, flag]) => {
        this.flags.set(key, flag as FeatureFlag);
      });
      this.saveFlags();
    } catch (error) {
      console.error('Failed to import feature flags configuration:', error);
      throw new Error('Invalid configuration format');
    }
  }
  
  /**
   * Get the A/B test variant for a specific user
   * Uses consistent hashing to ensure the same user always gets the same variant
   * @param flagKey - The feature flag key
   * @param userId - The user ID
   * @returns The variant name (e.g., 'control', 'variant-a') or null if not in A/B test
   */
  getABTestVariant(flagKey: string, userId: string): string | null {
    const flag = this.flags.get(flagKey);
    if (!flag || !flag.abTestVariants || flag.abTestVariants.length === 0) {
      return null;
    }
    
    // Check if user is in the rollout
    if (!this.isEnabledForUser(flagKey, userId)) {
      return null;
    }
    
    // Check if we have a cached assignment
    const cachedVariant = this.getCachedVariantAssignment(flagKey, userId);
    if (cachedVariant) {
      return cachedVariant;
    }
    
    // Assign variant based on user ID hash
    const hash = this.hashUserId(userId);
    const variantIndex = hash % flag.abTestVariants.length;
    const variant = flag.abTestVariants[variantIndex];
    
    // Cache the assignment
    this.cacheVariantAssignment(flagKey, userId, variant);
    
    // Track impression
    this.trackABTestMetric(flagKey, userId, variant, 'impression');
    
    return variant;
  }
  
  /**
   * Track an A/B test metric event
   * @param flagKey - The feature flag key
   * @param userId - The user ID
   * @param variant - The variant name
   * @param eventType - The type of event (impression, interaction, conversion)
   * @param metadata - Optional metadata about the event
   */
  trackABTestMetric(
    flagKey: string,
    userId: string,
    variant: string,
    eventType: 'impression' | 'interaction' | 'conversion',
    metadata?: Record<string, unknown>
  ): void {
    const metric: ABTestMetric = {
      flagKey,
      userId,
      variant,
      timestamp: new Date().toISOString(),
      eventType,
      metadata,
    };
    
    // Store locally
    this.storeABTestMetric(metric);
    
    // Send to backend (fire and forget)
    this.sendABTestMetricToBackend(metric).catch(error => {
      console.error('Failed to send A/B test metric to backend:', error);
    });
  }
  
  /**
   * Get A/B test statistics for a feature flag
   * @param flagKey - The feature flag key
   * @returns Statistics about the A/B test
   */
  getABTestStats(flagKey: string): ABTestStats | null {
    const flag = this.flags.get(flagKey);
    if (!flag || !flag.abTestVariants || flag.abTestVariants.length === 0) {
      return null;
    }
    
    const metrics = this.getABTestMetrics(flagKey);
    const stats: ABTestStats = {
      flagKey,
      totalUsers: 0,
      variantStats: {},
    };
    
    // Initialize variant stats
    flag.abTestVariants.forEach(variant => {
      stats.variantStats[variant] = {
        userCount: 0,
        impressions: 0,
        interactions: 0,
        conversions: 0,
      };
    });
    
    // Count unique users and events
    const uniqueUsers = new Set<string>();
    metrics.forEach(metric => {
      uniqueUsers.add(metric.userId);
      
      const variantStat = stats.variantStats[metric.variant];
      if (variantStat) {
        if (metric.eventType === 'impression') {
          variantStat.impressions++;
        } else if (metric.eventType === 'interaction') {
          variantStat.interactions++;
        } else if (metric.eventType === 'conversion') {
          variantStat.conversions++;
        }
      }
    });
    
    // Count users per variant
    const variantAssignments = this.getVariantAssignments(flagKey);
    Object.values(variantAssignments).forEach(variant => {
      if (stats.variantStats[variant]) {
        stats.variantStats[variant].userCount++;
      }
    });
    
    stats.totalUsers = uniqueUsers.size;
    
    return stats;
  }
  
  /**
   * Set A/B test variants for a feature flag
   * If the flag doesn't exist, it will be created
   * @param flagKey - The feature flag key
   * @param variants - Array of variant names (e.g., ['control', 'variant-a', 'variant-b'])
   */
  setABTestVariants(flagKey: string, variants: string[]): void {
    if (variants.length === 0) {
      console.error('A/B test must have at least one variant');
      return;
    }
    
    let flag = this.flags.get(flagKey);
    if (flag) {
      flag.abTestVariants = variants;
      this.flags.set(flagKey, flag);
      this.saveFlags();
    } else {
      // Create new flag if it doesn't exist
      flag = {
        key: flagKey,
        enabled: false,
        description: `Feature flag: ${flagKey}`,
        rolloutPercentage: 100,
        abTestVariants: variants,
      };
      this.flags.set(flagKey, flag);
      this.saveFlags();
    }
  }
  
  /**
   * Get cached variant assignment for a user
   */
  private getCachedVariantAssignment(flagKey: string, userId: string): string | null {
    try {
      const assignments = this.getVariantAssignments(flagKey);
      return assignments[userId] || null;
    } catch (error) {
      console.error('Failed to get cached variant assignment:', error);
      return null;
    }
  }
  
  /**
   * Cache variant assignment for a user
   */
  private cacheVariantAssignment(flagKey: string, userId: string, variant: string): void {
    try {
      const allAssignments = this.getAllVariantAssignments();
      if (!allAssignments[flagKey]) {
        allAssignments[flagKey] = {};
      }
      allAssignments[flagKey][userId] = variant;
      
      localStorage.setItem(this.VARIANT_ASSIGNMENTS_KEY, JSON.stringify(allAssignments));
    } catch (error) {
      console.error('Failed to cache variant assignment:', error);
    }
  }
  
  /**
   * Get all variant assignments for a flag
   */
  private getVariantAssignments(flagKey: string): Record<string, string> {
    const allAssignments = this.getAllVariantAssignments();
    return allAssignments[flagKey] || {};
  }
  
  /**
   * Get all variant assignments
   */
  private getAllVariantAssignments(): Record<string, Record<string, string>> {
    try {
      const stored = localStorage.getItem(this.VARIANT_ASSIGNMENTS_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch (error) {
      console.error('Failed to load variant assignments:', error);
      return {};
    }
  }
  
  /**
   * Store A/B test metric locally
   */
  private storeABTestMetric(metric: ABTestMetric): void {
    try {
      const metrics = this.getAllABTestMetrics();
      metrics.push(metric);
      
      // Keep only last 1000 metrics
      if (metrics.length > 1000) {
        metrics.splice(0, metrics.length - 1000);
      }
      
      localStorage.setItem(this.METRICS_STORAGE_KEY, JSON.stringify(metrics));
    } catch (error) {
      console.error('Failed to store A/B test metric:', error);
    }
  }
  
  /**
   * Get all A/B test metrics
   */
  private getAllABTestMetrics(): ABTestMetric[] {
    try {
      const stored = localStorage.getItem(this.METRICS_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Failed to load A/B test metrics:', error);
      return [];
    }
  }
  
  /**
   * Get A/B test metrics for a specific flag
   */
  private getABTestMetrics(flagKey: string): ABTestMetric[] {
    const allMetrics = this.getAllABTestMetrics();
    return allMetrics.filter(metric => metric.flagKey === flagKey);
  }
  
  /**
   * Send A/B test metric to backend
   */
  private async sendABTestMetricToBackend(metric: ABTestMetric): Promise<void> {
    // Only send if we have an API client available
    if (typeof window !== 'undefined' && (window as any).apiClient) {
      const apiClient = (window as any).apiClient;
      await apiClient.post('/api/v1/metrics/ab-test', metric);
    }
  }
  
  /**
   * Clear all A/B test metrics
   * Useful for testing or resetting data
   */
  clearABTestMetrics(): void {
    try {
      localStorage.removeItem(this.METRICS_STORAGE_KEY);
      localStorage.removeItem(this.VARIANT_ASSIGNMENTS_KEY);
    } catch (error) {
      console.error('Failed to clear A/B test metrics:', error);
    }
  }
}

// Export singleton instance
export const featureFlagsService = new FeatureFlagsService();

// Export types
export type { FeatureFlag, FeatureFlagsConfig, FlagChangeLog, ABTestMetric, ABTestStats };
