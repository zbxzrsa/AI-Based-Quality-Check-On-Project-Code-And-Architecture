'use client';

/**
 * Issue Card Component for AI Analysis
 */
import { AlertCircle, CheckCircle, Info, Lock, Zap, Code, Layers, Brain } from 'lucide-react';

interface Issue {
    type: 'security' | 'logic' | 'architecture' | 'performance' | 'quality';
    severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
    confidence: number;
    file: string;
    line: number;
    title: string;
    description: string;
    suggestion: string;
    example?: string;
}

interface IssueCardProps {
    issue: Issue;
    onJumpToCode?: () => void;
    onAccept?: () => void;
    onDismiss?: () => void;
}

export default function IssueCard({ issue, onJumpToCode, onAccept, onDismiss }: IssueCardProps) {
    const getTypeIcon = () => {
        switch (issue.type) {
            case 'security':
                return <Lock className="h-5 w-5" />;
            case 'architecture':
                return <Layers className="h-5 w-5" />;
            case 'logic':
                return <Brain className="h-5 w-5" />;
            case 'performance':
                return <Zap className="h-5 w-5" />;
            case 'quality':
                return <Code className="h-5 w-5" />;
        }
    };

    const getTypeColor = () => {
        switch (issue.type) {
            case 'security':
                return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
            case 'architecture':
                return 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20';
            case 'logic':
                return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20';
            case 'performance':
                return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
            case 'quality':
                return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/20';
        }
    };

    const getSeverityBadge = () => {
        const colors = {
            critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
            high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
            medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
            low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
            info: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
        };

        return (
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[issue.severity]}`}>
                {issue.severity}
            </span>
        );
    };

    return (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 hover:shadow-md transition-shadow">
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded ${getTypeColor()}`}>
                        {getTypeIcon()}
                    </div>
                    <div>
                        <h4 className="font-medium text-gray-900 dark:text-white text-sm">
                            {issue.title}
                        </h4>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {issue.file}:{issue.line}
                        </p>
                    </div>
                </div>
                {getSeverityBadge()}
            </div>

            {/* Description */}
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                {issue.description}
            </p>

            {/* Suggestion */}
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-md p-3 mb-3">
                <div className="flex items-start gap-2">
                    <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-xs font-medium text-blue-900 dark:text-blue-300 mb-1">
                            Suggestion
                        </p>
                        <p className="text-xs text-blue-800 dark:text-blue-200">
                            {issue.suggestion}
                        </p>
                    </div>
                </div>
            </div>

            {/* Example Code */}
            {issue.example && (
                <div className="bg-gray-50 dark:bg-gray-900/50 rounded-md p-3 mb-3">
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Example Fix
                    </p>
                    <pre className="text-xs text-gray-800 dark:text-gray-200 overflow-x-auto">
                        <code>{issue.example}</code>
                    </pre>
                </div>
            )}

            {/* Confidence Score */}
            <div className="mb-3">
                <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-gray-600 dark:text-gray-400">Confidence</span>
                    <span className="font-medium text-gray-900 dark:text-white">{issue.confidence}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                    <div
                        className={`h-1.5 rounded-full ${issue.confidence >= 80
                                ? 'bg-green-500'
                                : issue.confidence >= 60
                                    ? 'bg-yellow-500'
                                    : 'bg-red-500'
                            }`}
                        style={{ width: `${issue.confidence}%` }}
                    />
                </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
                <button
                    onClick={onJumpToCode}
                    className="flex-1 px-3 py-2 text-xs font-medium text-primary-700 dark:text-primary-300 bg-primary-50 dark:bg-primary-900/30 rounded-md hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors"
                >
                    Jump to Code
                </button>
                {onAccept && (
                    <button
                        onClick={onAccept}
                        className="px-3 py-2 text-xs font-medium text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/30 rounded-md hover:bg-green-100 dark:hover:bg-green-900/50 transition-colors"
                    >
                        Accept
                    </button>
                )}
                {onDismiss && (
                    <button
                        onClick={onDismiss}
                        className="px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700/50 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                        Dismiss
                    </button>
                )}
            </div>
        </div>
    );
}
