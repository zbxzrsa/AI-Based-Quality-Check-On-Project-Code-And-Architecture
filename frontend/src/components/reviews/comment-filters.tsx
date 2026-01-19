'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Filter, X } from 'lucide-react';

export interface CommentFilters {
  severity: string[];
  category: string[];
  status: string[];
}

interface CommentFiltersProps {
  filters: CommentFilters;
  onFiltersChange: (filters: CommentFilters) => void;
  availableCategories: string[];
}

export default function CommentFiltersComponent({
  filters,
  onFiltersChange,
  availableCategories,
}: CommentFiltersProps) {
  const severityOptions = ['critical', 'high', 'medium', 'low'];
  const statusOptions = ['open', 'resolved', 'wont_fix'];

  const toggleFilter = (
    type: keyof CommentFilters,
    value: string
  ) => {
    const currentValues = filters[type];
    const newValues = currentValues.includes(value)
      ? currentValues.filter((v) => v !== value)
      : [...currentValues, value];

    onFiltersChange({
      ...filters,
      [type]: newValues,
    });
  };

  const clearAllFilters = () => {
    onFiltersChange({
      severity: [],
      category: [],
      status: [],
    });
  };

  const hasActiveFilters =
    filters.severity.length > 0 ||
    filters.category.length > 0 ||
    filters.status.length > 0;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500 hover:bg-red-600';
      case 'high':
        return 'bg-orange-500 hover:bg-orange-600';
      case 'medium':
        return 'bg-yellow-500 hover:bg-yellow-600';
      case 'low':
        return 'bg-blue-500 hover:bg-blue-600';
      default:
        return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-yellow-500 hover:bg-yellow-600';
      case 'resolved':
        return 'bg-green-500 hover:bg-green-600';
      case 'wont_fix':
        return 'bg-gray-500 hover:bg-gray-600';
      default:
        return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">Filters</h3>
        </div>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearAllFilters}
            className="h-8 text-xs"
          >
            <X className="h-3 w-3 mr-1" />
            Clear All
          </Button>
        )}
      </div>

      {/* Severity Filter */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-muted-foreground">
          Severity
        </label>
        <div className="flex flex-wrap gap-2">
          {severityOptions.map((severity) => (
            <Badge
              key={severity}
              className={`cursor-pointer ${
                filters.severity.includes(severity)
                  ? getSeverityColor(severity)
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
              onClick={() => toggleFilter('severity', severity)}
            >
              {severity}
            </Badge>
          ))}
        </div>
      </div>

      {/* Category Filter */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-muted-foreground">
          Category
        </label>
        <div className="flex flex-wrap gap-2">
          {availableCategories.map((category) => (
            <Badge
              key={category}
              variant={
                filters.category.includes(category) ? 'default' : 'outline'
              }
              className="cursor-pointer"
              onClick={() => toggleFilter('category', category)}
            >
              {category}
            </Badge>
          ))}
        </div>
      </div>

      {/* Status Filter */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-muted-foreground">
          Status
        </label>
        <div className="flex flex-wrap gap-2">
          {statusOptions.map((status) => (
            <Badge
              key={status}
              className={`cursor-pointer ${
                filters.status.includes(status)
                  ? getStatusColor(status)
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
              onClick={() => toggleFilter('status', status)}
            >
              {status.replace('_', ' ')}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
}
