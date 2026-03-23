/**
 * Dashboard Modal Component
 * 
 * Modal for creating and editing custom dashboards
 */

import React, { useState, useEffect } from 'react';
import { DashboardFormData, TimeRange } from '../types/dashboard';

interface DashboardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: DashboardFormData) => void;
  initialData?: Partial<DashboardFormData>;
  availableMetrics: Array<{ id: string; name: string }>;
  mode: 'create' | 'edit';
}

/**
 * Dashboard creation and editing modal
 */
export const DashboardModal: React.FC<DashboardModalProps> = ({
  isOpen,
  onClose,
  onSave,
  initialData,
  availableMetrics,
  mode
}) => {
  const [formData, setFormData] = useState<DashboardFormData>({
    name: '',
    description: '',
    metrics: [],
    timeRange: {
      type: 'relative',
      value: 7,
      unit: 'day'
    },
    refreshInterval: 30,
    shared: false,
    ...initialData
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (initialData) {
      setFormData({
        name: '',
        description: '',
        metrics: [],
        timeRange: {
          type: 'relative',
          value: 7,
          unit: 'day'
        },
        refreshInterval: 30,
        shared: false,
        ...initialData
      });
    }
  }, [initialData]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Dashboard name is required';
    }

    if (formData.metrics.length === 0) {
      newErrors.metrics = 'Select at least one metric';
    }

    if (formData.refreshInterval < 5) {
      newErrors.refreshInterval = 'Refresh interval must be at least 5 seconds';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (validate()) {
      onSave(formData);
      onClose();
    }
  };

  const handleMetricToggle = (metricId: string) => {
    setFormData(prev => ({
      ...prev,
      metrics: prev.metrics.includes(metricId)
        ? prev.metrics.filter(id => id !== metricId)
        : [...prev.metrics, metricId]
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
          {/* Header */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {mode === 'create' ? 'Create Dashboard' : 'Edit Dashboard'}
            </h2>
            <p className="text-gray-600 mt-1">
              Configure your custom metrics dashboard
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            {/* Name */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Dashboard Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.name ? 'border-red-500' : 'border-gray-300'
                }`}
                placeholder="My Dashboard"
              />
              {errors.name && (
                <p className="text-red-500 text-sm mt-1">{errors.name}</p>
              )}
            </div>

            {/* Description */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Optional description"
                rows={3}
              />
            </div>

            {/* Metrics Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Metrics *
              </label>
              <div className="border border-gray-300 rounded-lg p-3 max-h-48 overflow-y-auto">
                {availableMetrics.map((metric) => (
                  <label key={metric.id} className="flex items-center py-2 cursor-pointer hover:bg-gray-50">
                    <input
                      type="checkbox"
                      checked={formData.metrics.includes(metric.id)}
                      onChange={() => handleMetricToggle(metric.id)}
                      className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="text-gray-700">{metric.name}</span>
                  </label>
                ))}
              </div>
              {errors.metrics && (
                <p className="text-red-500 text-sm mt-1">{errors.metrics}</p>
              )}
            </div>

            {/* Time Range */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Default Time Range
              </label>
              <div className="grid grid-cols-2 gap-3">
                <select
                  value={formData.timeRange.value || 7}
                  onChange={(e) => setFormData({
                    ...formData,
                    timeRange: { ...formData.timeRange, value: parseInt(e.target.value) }
                  })}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={1}>1</option>
                  <option value={7}>7</option>
                  <option value={14}>14</option>
                  <option value={30}>30</option>
                </select>
                <select
                  value={formData.timeRange.unit || 'day'}
                  onChange={(e) => setFormData({
                    ...formData,
                    timeRange: { ...formData.timeRange, unit: e.target.value as any }
                  })}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="hour">Hours</option>
                  <option value="day">Days</option>
                  <option value="week">Weeks</option>
                  <option value="month">Months</option>
                </select>
              </div>
            </div>

            {/* Refresh Interval */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Refresh Interval (seconds)
              </label>
              <input
                type="number"
                min="5"
                value={formData.refreshInterval}
                onChange={(e) => setFormData({ ...formData, refreshInterval: parseInt(e.target.value) })}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.refreshInterval ? 'border-red-500' : 'border-gray-300'
                }`}
              />
              {errors.refreshInterval && (
                <p className="text-red-500 text-sm mt-1">{errors.refreshInterval}</p>
              )}
            </div>

            {/* Shared */}
            <div className="mb-6">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.shared}
                  onChange={(e) => setFormData({ ...formData, shared: e.target.checked })}
                  className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700">Share this dashboard with others</span>
              </label>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              >
                {mode === 'create' ? 'Create Dashboard' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
