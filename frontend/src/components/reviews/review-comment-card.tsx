'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  AlertCircle,
  XCircle,
  Info,
  CheckCircle2,
  X,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Code,
} from 'lucide-react';

export interface ReviewComment {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  message: string;
  filename: string;
  lineNumber: number;
  codeSnippet?: string;
  suggestedFix?: string;
  reasoning?: string;
  status: 'open' | 'resolved' | 'wont_fix';
}

interface ReviewCommentCardProps {
  comment: ReviewComment;
  onResolve: () => void;
  onWontFix: () => void;
  onAskAI: () => void;
}

export default function ReviewCommentCard({
  comment,
  onResolve,
  onWontFix,
  onAskAI,
}: ReviewCommentCardProps) {
  const [showReasoning, setShowReasoning] = useState(false);
  const [showSuggestedFix, setShowSuggestedFix] = useState(false);

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'high':
        return <AlertCircle className="h-5 w-5 text-orange-500" />;
      case 'medium':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'low':
        return <Info className="h-5 w-5 text-blue-500" />;
      default:
        return <Info className="h-5 w-5" />;
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

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      security: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      performance: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
      maintainability: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'best-practices': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      'code-style': 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
      documentation: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    };
    return colors[category.toLowerCase()] || 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'resolved':
        return (
          <Badge className="bg-green-500">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Resolved
          </Badge>
        );
      case 'wont_fix':
        return (
          <Badge className="bg-gray-500">
            <X className="h-3 w-3 mr-1" />
            Won't Fix
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 flex-1">
            {getSeverityIcon(comment.severity)}
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className={getSeverityColor(comment.severity)}>
                  {comment.severity.toUpperCase()}
                </Badge>
                <Badge variant="outline" className={getCategoryColor(comment.category)}>
                  {comment.category}
                </Badge>
                {getStatusBadge(comment.status)}
              </div>
              <p className="text-sm font-medium">{comment.message}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Code className="h-3 w-3" />
                <span>
                  {comment.filename}:{comment.lineNumber}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Code Snippet */}
        {comment.codeSnippet && (
          <div className="rounded-md bg-muted p-3 font-mono text-sm overflow-x-auto">
            <pre className="whitespace-pre">{comment.codeSnippet}</pre>
          </div>
        )}

        {/* Suggested Fix */}
        {comment.suggestedFix && (
          <div className="space-y-2">
            <button
              onClick={() => setShowSuggestedFix(!showSuggestedFix)}
              className="flex items-center gap-2 text-sm font-medium text-primary hover:underline"
            >
              {showSuggestedFix ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              Suggested Fix
            </button>
            {showSuggestedFix && (
              <div className="rounded-md bg-green-50 dark:bg-green-950/30 p-3 font-mono text-sm overflow-x-auto border-l-2 border-green-500">
                <pre className="whitespace-pre">{comment.suggestedFix}</pre>
              </div>
            )}
          </div>
        )}

        {/* Reasoning */}
        {comment.reasoning && (
          <div className="space-y-2">
            <button
              onClick={() => setShowReasoning(!showReasoning)}
              className="flex items-center gap-2 text-sm font-medium text-primary hover:underline"
            >
              {showReasoning ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              Show AI Reasoning
            </button>
            {showReasoning && (
              <div className="rounded-md bg-blue-50 dark:bg-blue-950/30 p-3 text-sm border-l-2 border-blue-500">
                <p className="text-muted-foreground">{comment.reasoning}</p>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        {comment.status === 'open' && (
          <div className="flex items-center gap-2 pt-2 border-t">
            <Button
              size="sm"
              variant="default"
              onClick={onResolve}
              className="flex items-center gap-2"
            >
              <CheckCircle2 className="h-4 w-4" />
              Resolve
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={onWontFix}
              className="flex items-center gap-2"
            >
              <X className="h-4 w-4" />
              Won't Fix
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={onAskAI}
              className="flex items-center gap-2"
            >
              <MessageSquare className="h-4 w-4" />
              Ask AI
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
