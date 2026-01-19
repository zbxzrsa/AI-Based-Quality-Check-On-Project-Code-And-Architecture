'use client';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Shield,
  FileCheck,
} from 'lucide-react';

interface ComplianceStandard {
  name: string;
  status: 'passed' | 'warning' | 'failed';
  score: number;
  violations: ComplianceViolation[];
}

interface ComplianceViolation {
  id: string;
  rule: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  affectedFiles: string[];
}

interface ComplianceStatusProps {
  iso25010: ComplianceStandard;
  iso23396: ComplianceStandard;
}

export default function ComplianceStatus({
  iso25010,
  iso23396,
}: ComplianceStatusProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'passed':
        return 'bg-green-500';
      case 'warning':
        return 'bg-yellow-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const renderStandard = (standard: ComplianceStandard) => {
    return (
      <Card className="p-6">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {standard.name === 'ISO/IEC 25010' ? (
                <Shield className="h-6 w-6 text-primary" />
              ) : (
                <FileCheck className="h-6 w-6 text-primary" />
              )}
              <div>
                <h3 className="text-lg font-semibold">{standard.name}</h3>
                <p className="text-sm text-muted-foreground">
                  {standard.name === 'ISO/IEC 25010'
                    ? 'Software Product Quality'
                    : 'Software Architecture Evaluation'}
                </p>
              </div>
            </div>
            <Badge className={getStatusColor(standard.status)}>
              {getStatusIcon(standard.status)}
              <span className="ml-2">{standard.status.toUpperCase()}</span>
            </Badge>
          </div>

          {/* Score */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Compliance Score</span>
              <span className="font-bold">{standard.score}%</span>
            </div>
            <Progress value={standard.score} className="h-2" />
          </div>

          {/* Violations */}
          {standard.violations.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                Violations ({standard.violations.length})
              </h4>
              <div className="space-y-2">
                {standard.violations.map((violation) => (
                  <div
                    key={violation.id}
                    className="p-3 rounded-md bg-muted space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge
                            className={getSeverityColor(violation.severity)}
                          >
                            {violation.severity}
                          </Badge>
                          <span className="text-sm font-medium">
                            {violation.rule}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {violation.description}
                        </p>
                      </div>
                    </div>
                    {violation.affectedFiles.length > 0 && (
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium">Affected files:</span>{' '}
                        {violation.affectedFiles.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Violations */}
          {standard.violations.length === 0 && (
            <div className="flex items-center gap-2 p-3 rounded-md bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300">
              <CheckCircle2 className="h-4 w-4" />
              <span className="text-sm">No violations found</span>
            </div>
          )}
        </div>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Shield className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-xl font-bold">Compliance Status</h2>
      </div>

      {renderStandard(iso25010)}
      {renderStandard(iso23396)}
    </div>
  );
}
