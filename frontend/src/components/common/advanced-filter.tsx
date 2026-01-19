'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Filter, X, Save, Plus } from 'lucide-react';

export interface FilterCriteria {
  field: string;
  operator: string;
  value: string;
}

export interface FilterPreset {
  id: string;
  name: string;
  criteria: FilterCriteria[];
}

interface AdvancedFilterProps {
  availableFields: { value: string; label: string }[];
  onApplyFilters: (criteria: FilterCriteria[]) => void;
  presets?: FilterPreset[];
  onSavePreset?: (name: string, criteria: FilterCriteria[]) => void;
}

export default function AdvancedFilter({
  availableFields,
  onApplyFilters,
  presets = [],
  onSavePreset,
}: AdvancedFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [criteria, setCriteria] = useState<FilterCriteria[]>([
    { field: '', operator: 'equals', value: '' },
  ]);
  const [isSavePresetOpen, setIsSavePresetOpen] = useState(false);
  const [presetName, setPresetName] = useState('');

  const operators = [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not Equals' },
    { value: 'contains', label: 'Contains' },
    { value: 'not_contains', label: 'Does Not Contain' },
    { value: 'starts_with', label: 'Starts With' },
    { value: 'ends_with', label: 'Ends With' },
    { value: 'greater_than', label: 'Greater Than' },
    { value: 'less_than', label: 'Less Than' },
  ];

  const addCriteria = () => {
    setCriteria([...criteria, { field: '', operator: 'equals', value: '' }]);
  };

  const removeCriteria = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const updateCriteria = (
    index: number,
    field: keyof FilterCriteria,
    value: string
  ) => {
    const newCriteria = [...criteria];
    newCriteria[index][field] = value;
    setCriteria(newCriteria);
  };

  const applyFilters = () => {
    const validCriteria = criteria.filter(
      (c) => c.field && c.operator && c.value
    );
    onApplyFilters(validCriteria);
    setIsOpen(false);
  };

  const clearFilters = () => {
    setCriteria([{ field: '', operator: 'equals', value: '' }]);
    onApplyFilters([]);
  };

  const loadPreset = (preset: FilterPreset) => {
    setCriteria(preset.criteria);
    onApplyFilters(preset.criteria);
    setIsOpen(false);
  };

  const savePreset = () => {
    if (presetName && onSavePreset) {
      const validCriteria = criteria.filter(
        (c) => c.field && c.operator && c.value
      );
      onSavePreset(presetName, validCriteria);
      setPresetName('');
      setIsSavePresetOpen(false);
    }
  };

  const activeCriteriaCount = criteria.filter(
    (c) => c.field && c.operator && c.value
  ).length;

  return (
    <div className="flex items-center gap-2">
      {/* Presets */}
      {presets.length > 0 && (
        <div className="flex gap-2">
          {presets.map((preset) => (
            <Badge
              key={preset.id}
              variant="outline"
              className="cursor-pointer hover:bg-muted"
              onClick={() => loadPreset(preset)}
            >
              {preset.name}
            </Badge>
          ))}
        </div>
      )}

      {/* Filter Button */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" className="relative">
            <Filter className="h-4 w-4 mr-2" />
            Advanced Filters
            {activeCriteriaCount > 0 && (
              <Badge className="ml-2 bg-primary">{activeCriteriaCount}</Badge>
            )}
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Advanced Filters</DialogTitle>
            <DialogDescription>
              Build complex filters with multiple criteria
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {criteria.map((criterion, index) => (
              <Card key={index} className="p-4">
                <div className="flex items-end gap-4">
                  <div className="flex-1 space-y-2">
                    <Label htmlFor={`field-${index}`}>Field</Label>
                    <Select
                      value={criterion.field}
                      onValueChange={(value) =>
                        updateCriteria(index, 'field', value)
                      }
                    >
                      <SelectTrigger id={`field-${index}`}>
                        <SelectValue placeholder="Select field" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableFields.map((field) => (
                          <SelectItem key={field.value} value={field.value}>
                            {field.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex-1 space-y-2">
                    <Label htmlFor={`operator-${index}`}>Operator</Label>
                    <Select
                      value={criterion.operator}
                      onValueChange={(value) =>
                        updateCriteria(index, 'operator', value)
                      }
                    >
                      <SelectTrigger id={`operator-${index}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {operators.map((op) => (
                          <SelectItem key={op.value} value={op.value}>
                            {op.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex-1 space-y-2">
                    <Label htmlFor={`value-${index}`}>Value</Label>
                    <Input
                      id={`value-${index}`}
                      value={criterion.value}
                      onChange={(e) =>
                        updateCriteria(index, 'value', e.target.value)
                      }
                      placeholder="Enter value"
                    />
                  </div>

                  {criteria.length > 1 && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeCriteria(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </Card>
            ))}

            <Button
              variant="outline"
              onClick={addCriteria}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Criteria
            </Button>
          </div>

          <DialogFooter className="flex justify-between">
            <div className="flex gap-2">
              <Button variant="outline" onClick={clearFilters}>
                Clear All
              </Button>
              {onSavePreset && (
                <Dialog
                  open={isSavePresetOpen}
                  onOpenChange={setIsSavePresetOpen}
                >
                  <DialogTrigger asChild>
                    <Button variant="outline">
                      <Save className="h-4 w-4 mr-2" />
                      Save Preset
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Save Filter Preset</DialogTitle>
                      <DialogDescription>
                        Give your filter preset a name
                      </DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                      <Label htmlFor="preset-name">Preset Name</Label>
                      <Input
                        id="preset-name"
                        value={presetName}
                        onChange={(e) => setPresetName(e.target.value)}
                        placeholder="e.g., Critical Issues"
                        className="mt-2"
                      />
                    </div>
                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setIsSavePresetOpen(false)}
                      >
                        Cancel
                      </Button>
                      <Button onClick={savePreset}>Save</Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              )}
            </div>
            <Button onClick={applyFilters}>Apply Filters</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
