import React from 'react';

interface QualityGradeDisplayProps {
  project_id: string;
  quality_grade: string;
  grade_score: number;
  total_vulnerabilities: number;
  critical_vulnerabilities: number;
  high_vulnerabilities: number;
  compliance_score: number;
  frameworks_compliant: string[];
  last_scan_date?: string;
  recent_scan?: {
    timestamp: string;
    tool: string;
    total_issues: number;
    critical_issues: number;
    high_issues: number;
  };
  vulnerability_trend?: Array<{
    scan_number: number;
    total_issues: number;
    critical_issues: number;
    high_issues: number;
    timestamp: string;
  }>;
  className?: string;
}

const QualityGradeDisplay: React.FC<QualityGradeDisplayProps> = ({
  project_id,
  quality_grade,
  grade_score,
  total_vulnerabilities,
  critical_vulnerabilities,
  high_vulnerabilities,
  compliance_score,
  frameworks_compliant,
  last_scan_date,
  recent_scan,
  vulnerability_trend,
  className
}) => {
  // Determine grade color and icon
  const getGradeConfig = (grade: string) => {
    switch (grade) {
      case 'A+':
        return { color: 'text-green-600', bg: 'bg-green-100', icon: '🛡️' };
      case 'A':
        return { color: 'text-green-600', bg: 'bg-green-100', icon: '🛡️' };
      case 'B':
        return { color: 'text-blue-600', bg: 'bg-blue-100', icon: '🛡️' };
      case 'C':
        return { color: 'text-yellow-600', bg: 'bg-yellow-100', icon: '⚠️' };
      case 'D':
        return { color: 'text-orange-600', bg: 'bg-orange-100', icon: '⚠️' };
      case 'F':
        return { color: 'text-red-600', bg: 'bg-red-100', icon: '⚠️' };
      default:
        return { color: 'text-gray-600', bg: 'bg-gray-100', icon: '🛡️' };
    }
  };

  const gradeConfig = getGradeConfig(quality_grade);

  // Calculate trend direction
  const getTrendDirection = () => {
    if (!vulnerability_trend || vulnerability_trend.length < 2) {
      return 'neutral';
    }
    
    const latest = vulnerability_trend[0];
    const previous = vulnerability_trend[1];
    
    if (latest.total_issues < previous.total_issues) return 'improving';
    if (latest.total_issues > previous.total_issues) return 'declining';
    return 'stable';
  };

  const trendDirection = getTrendDirection();

  // Format date
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'No recent scans';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className={`overflow-hidden rounded-lg border shadow-sm ${className}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-full ${gradeConfig.bg}`}>
              <span className="text-2xl">{gradeConfig.icon}</span>
            </div>
            <div>
              <h3 className="text-lg font-semibold">
                Security Quality Grade
              </h3>
              <p className="text-sm text-gray-600">
                Project: {project_id}
              </p>
            </div>
          </div>
          
          {/* Grade Display */}
          <div className="text-right">
            <div className="text-3xl font-bold font-mono">
              {quality_grade}
            </div>
            <div className="text-sm text-gray-500">
              Score: {grade_score}/100
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Main Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          
          {/* Total Vulnerabilities */}
          <div className="border-l-4 border-red-400 bg-white rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Issues</p>
                <p className="text-2xl font-bold text-red-600">{total_vulnerabilities}</p>
              </div>
              <div className="p-2 bg-red-100 rounded-full">
                <span className="text-red-600">⚠️</span>
              </div>
            </div>
          </div>

          {/* Critical Vulnerabilities */}
          <div className="border-l-4 border-red-500 bg-white rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Critical</p>
                <p className="text-2xl font-bold text-red-600">{critical_vulnerabilities}</p>
              </div>
              <div className="p-2 bg-red-100 rounded-full">
                <span className="text-red-600">❌</span>
              </div>
            </div>
          </div>

          {/* High Vulnerabilities */}
          <div className="border-l-4 border-orange-400 bg-white rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">High</p>
                <p className="text-2xl font-bold text-orange-600">{high_vulnerabilities}</p>
              </div>
              <div className="p-2 bg-orange-100 rounded-full">
                <span className="text-orange-600">⚠️</span>
              </div>
            </div>
          </div>

          {/* Compliance Score */}
          <div className="border-l-4 border-green-400 bg-white rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Compliance</p>
                <p className="text-2xl font-bold text-green-600">{compliance_score}%</p>
              </div>
              <div className="p-2 bg-green-100 rounded-full">
                <span className="text-green-600">✅</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Scan Information */}
        {recent_scan && (
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-gray-800">Recent Scan</h4>
              <div className="flex items-center space-x-2 bg-white px-2 py-1 rounded text-sm">
                <span>⏰</span>
                <span>{recent_scan.tool}</span>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Date:</span>
                <span className="ml-2 font-medium">{formatDate(recent_scan.timestamp)}</span>
              </div>
              <div>
                <span className="text-gray-600">Issues Found:</span>
                <span className="ml-2 font-medium">{recent_scan.total_issues}</span>
              </div>
              <div>
                <span className="text-gray-600">Critical:</span>
                <span className="ml-2 font-medium text-red-600">{recent_scan.critical_issues}</span>
              </div>
            </div>
          </div>
        )}

        {/* Frameworks Compliant */}
        {frameworks_compliant.length > 0 && (
          <div className="mb-6">
            <h4 className="font-semibold text-gray-800 mb-2">Compliance Frameworks</h4>
            <div className="flex flex-wrap gap-2">
              {frameworks_compliant.map((framework) => (
                <span key={framework} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {framework}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Trend Analysis */}
        {vulnerability_trend && vulnerability_trend.length > 1 && (
          <div className="border-t pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span>📊</span>
                <span className="font-medium text-gray-800">Trend Analysis</span>
              </div>
              
              {/* Trend Indicator */}
              <div className="flex items-center space-x-2">
                {trendDirection === 'improving' && <span className="text-green-600">📈</span>}
                {trendDirection === 'declining' && <span className="text-red-600">📉</span>}
                {trendDirection === 'stable' && <span className="text-gray-400">➡️</span>}
                <span className={`font-medium ${
                  trendDirection === 'improving' ? 'text-green-600' :
                  trendDirection === 'declining' ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {trendDirection === 'improving' ? 'Improving' :
                   trendDirection === 'declining' ? 'Needs Attention' : 'Stable'}
                </span>
              </div>
            </div>

            {/* Trend Details */}
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="bg-white p-3 rounded border">
                <span className="text-gray-600">Latest Scan</span>
                <div className="mt-1 font-medium">
                  {vulnerability_trend[0].total_issues} issues
                </div>
              </div>
              <div className="bg-white p-3 rounded border">
                <span className="text-gray-600">Previous Scan</span>
                <div className="mt-1 font-medium">
                  {vulnerability_trend[1].total_issues} issues
                </div>
              </div>
              <div className="bg-white p-3 rounded border">
                <span className="text-gray-600">Change</span>
                <div className={`mt-1 font-medium ${
                  vulnerability_trend[0].total_issues < vulnerability_trend[1].total_issues 
                    ? 'text-green-600' 
                    : vulnerability_trend[0].total_issues > vulnerability_trend[1].total_issues 
                    ? 'text-red-600' 
                    : 'text-gray-600'
                }`}>
                  {vulnerability_trend[0].total_issues < vulnerability_trend[1].total_issues 
                    ? `-${vulnerability_trend[1].total_issues - vulnerability_trend[0].total_issues}` 
                    : vulnerability_trend[0].total_issues > vulnerability_trend[1].total_issues 
                    ? `+${vulnerability_trend[0].total_issues - vulnerability_trend[1].total_issues}` 
                    : 'No change'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Last Scan Date */}
        <div className="mt-4 text-xs text-gray-500 text-center">
          Last updated: {formatDate(last_scan_date)}
        </div>
      </div>
    </div>
  );
};

export default QualityGradeDisplay;
