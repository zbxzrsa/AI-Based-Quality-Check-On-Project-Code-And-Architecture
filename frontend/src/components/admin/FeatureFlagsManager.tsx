/**
 * Feature Flags Manager Component
 * 
 * Admin interface for managing feature flags.
 * Provides UI to:
 * - Display all feature flags and their status
 * - Enable/disable features
 * - Control rollout percentage
 * - View audit logs
 * 
 * Requirements: 10.3
 */

'use client';

import React, { useState, useEffect } from 'react';
import { featureFlagsService, FeatureFlag, FlagChangeLog } from '@/lib/feature-flags';

interface FeatureFlagsManagerProps {
  className?: string;
}

export function FeatureFlagsManager({ className = '' }: FeatureFlagsManagerProps) {
  const [flags, setFlags] = useState<Record<string, FeatureFlag>>({});
  const [auditLogs, setAuditLogs] = useState<FlagChangeLog[]>([]);
  const [showAuditLogs, setShowAuditLogs] = useState(false);
  const [editingRollout, setEditingRollout] = useState<string | null>(null);
  const [rolloutValue, setRolloutValue] = useState<number>(0);

  // Load flags on mount
  useEffect(() => {
    loadFlags();
    loadAuditLogs();
  }, []);

  const loadFlags = () => {
    const allFlags = featureFlagsService.getAllFlags();
    setFlags(allFlags);
  };

  const loadAuditLogs = () => {
    const logs = featureFlagsService.getAuditLogs();
    setAuditLogs(logs);
  };

  const handleToggleFlag = (flagKey: string) => {
    const flag = flags[flagKey];
    if (flag) {
      featureFlagsService.setFlag(flagKey, !flag.enabled);
      loadFlags();
      loadAuditLogs();
    }
  };

  const handleStartEditRollout = (flagKey: string) => {
    const flag = flags[flagKey];
    if (flag) {
      setEditingRollout(flagKey);
      setRolloutValue(flag.rolloutPercentage ?? 0);
    }
  };

  const handleSaveRollout = (flagKey: string) => {
    featureFlagsService.setRolloutPercentage(flagKey, rolloutValue);
    setEditingRollout(null);
    loadFlags();
  };

  const handleCancelEditRollout = () => {
    setEditingRollout(null);
    setRolloutValue(0);
  };

  const handleResetToDefaults = () => {
    if (confirm('Are you sure you want to reset all feature flags to defaults? This cannot be undone.')) {
      featureFlagsService.resetToDefaults();
      loadFlags();
      loadAuditLogs();
    }
  };

  const handleExportConfig = () => {
    const config = featureFlagsService.exportConfig();
    const blob = new Blob([config], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feature-flags-${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportConfig = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          try {
            const config = event.target?.result as string;
            featureFlagsService.importConfig(config);
            loadFlags();
            alert('Configuration imported successfully');
          } catch (error) {
            alert('Failed to import configuration: ' + (error as Error).message);
          }
        };
        reader.readAsText(file);
      }
    };
    input.click();
  };

  const getStatusColor = (enabled: boolean) => {
    return enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800';
  };

  const getStatusText = (enabled: boolean) => {
    return enabled ? 'Enabled' : 'Disabled';
  };

  return (
    <div className={`feature-flags-manager ${className}`}>
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Feature Flags Manager</h2>
        <p className="text-gray-600">
          Manage feature flags for progressive migration and A/B testing
        </p>
      </div>

      {/* Action Buttons */}
      <div className="mb-6 flex gap-3 flex-wrap">
        <button
          onClick={handleResetToDefaults}
          className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 transition-colors"
        >
          Reset to Defaults
        </button>
        <button
          onClick={handleExportConfig}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Export Configuration
        </button>
        <button
          onClick={handleImportConfig}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Import Configuration
        </button>
        <button
          onClick={() => setShowAuditLogs(!showAuditLogs)}
          className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
        >
          {showAuditLogs ? 'Hide' : 'Show'} Audit Logs
        </button>
      </div>

      {/* Feature Flags Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Feature Flag
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rollout %
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {Object.entries(flags).map(([key, flag]) => (
              <tr key={key} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{flag.key}</div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-600">{flag.description}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(
                      flag.enabled
                    )}`}
                  >
                    {getStatusText(flag.enabled)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {editingRollout === key ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={rolloutValue}
                        onChange={(e) => setRolloutValue(Number(e.target.value))}
                        className="w-20 px-2 py-1 border border-gray-300 rounded-md text-sm"
                      />
                      <button
                        onClick={() => handleSaveRollout(key)}
                        className="text-green-600 hover:text-green-800 text-sm font-medium"
                      >
                        Save
                      </button>
                      <button
                        onClick={handleCancelEditRollout}
                        className="text-gray-600 hover:text-gray-800 text-sm font-medium"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-900">
                        {flag.rolloutPercentage ?? 0}%
                      </span>
                      <button
                        onClick={() => handleStartEditRollout(key)}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        Edit
                      </button>
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <button
                    onClick={() => handleToggleFlag(key)}
                    className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                      flag.enabled
                        ? 'bg-red-100 text-red-700 hover:bg-red-200'
                        : 'bg-green-100 text-green-700 hover:bg-green-200'
                    }`}
                  >
                    {flag.enabled ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Audit Logs */}
      {showAuditLogs && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Audit Logs</h3>
            <p className="text-sm text-gray-600 mt-1">
              Recent feature flag changes (last 100 entries)
            </p>
          </div>
          <div className="overflow-x-auto">
            {auditLogs.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500">
                No audit logs available
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Timestamp
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Flag Key
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Change
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      User ID
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {auditLogs.slice().reverse().map((log, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {log.flagKey}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={getStatusColor(log.oldValue)}>
                          {getStatusText(log.oldValue)}
                        </span>
                        <span className="mx-2 text-gray-400">→</span>
                        <span className={getStatusColor(log.newValue)}>
                          {getStatusText(log.newValue)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {log.userId || 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
