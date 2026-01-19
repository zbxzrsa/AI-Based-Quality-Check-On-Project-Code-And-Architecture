'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ChevronDown,
  ChevronRight,
  FileCode,
  Columns2,
  AlignJustify,
} from 'lucide-react';

interface DiffLine {
  lineNumber: number | null;
  oldLineNumber: number | null;
  newLineNumber: number | null;
  type: 'add' | 'remove' | 'context' | 'header';
  content: string;
}

interface FileDiff {
  filename: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  lines: DiffLine[];
}

interface CodeDiffViewerProps {
  files: FileDiff[];
  onLineClick?: (filename: string, lineNumber: number) => void;
}

export default function CodeDiffViewer({
  files,
  onLineClick,
}: CodeDiffViewerProps) {
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(
    new Set(files.map((f) => f.filename))
  );
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('unified');
  const [selectedFile, setSelectedFile] = useState<string | null>(
    files[0]?.filename || null
  );

  const toggleFile = (filename: string) => {
    const newExpanded = new Set(expandedFiles);
    if (newExpanded.has(filename)) {
      newExpanded.delete(filename);
    } else {
      newExpanded.add(filename);
    }
    setExpandedFiles(newExpanded);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'added':
        return 'bg-green-500';
      case 'modified':
        return 'bg-yellow-500';
      case 'deleted':
        return 'bg-red-500';
      case 'renamed':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getLineClass = (type: string) => {
    switch (type) {
      case 'add':
        return 'bg-green-50 dark:bg-green-950/30 border-l-2 border-green-500';
      case 'remove':
        return 'bg-red-50 dark:bg-red-950/30 border-l-2 border-red-500';
      case 'context':
        return 'bg-background';
      case 'header':
        return 'bg-muted text-muted-foreground font-semibold';
      default:
        return '';
    }
  };

  const getLinePrefix = (type: string) => {
    switch (type) {
      case 'add':
        return '+';
      case 'remove':
        return '-';
      case 'context':
        return ' ';
      default:
        return '';
    }
  };

  const renderUnifiedView = (file: FileDiff) => {
    return (
      <div className="font-mono text-sm">
        {file.lines.map((line, idx) => (
          <div
            key={idx}
            className={`flex hover:bg-muted/50 ${getLineClass(line.type)}`}
            onClick={() =>
              line.newLineNumber &&
              onLineClick?.(file.filename, line.newLineNumber)
            }
          >
            <div className="flex-shrink-0 w-16 px-2 text-right text-muted-foreground select-none border-r">
              {line.oldLineNumber || ''}
            </div>
            <div className="flex-shrink-0 w-16 px-2 text-right text-muted-foreground select-none border-r">
              {line.newLineNumber || ''}
            </div>
            <div className="flex-shrink-0 w-8 px-2 text-muted-foreground select-none">
              {getLinePrefix(line.type)}
            </div>
            <div className="flex-1 px-2 overflow-x-auto whitespace-pre">
              {line.content}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderSplitView = (file: FileDiff) => {
    return (
      <div className="grid grid-cols-2 gap-px bg-border font-mono text-sm">
        {/* Left side - deletions */}
        <div>
          {file.lines
            .filter((line) => line.type === 'remove' || line.type === 'context')
            .map((line, idx) => (
              <div
                key={`left-${idx}`}
                className={`flex ${getLineClass(line.type)}`}
              >
                <div className="flex-shrink-0 w-16 px-2 text-right text-muted-foreground select-none border-r">
                  {line.oldLineNumber || ''}
                </div>
                <div className="flex-shrink-0 w-8 px-2 text-muted-foreground select-none">
                  {line.type === 'remove' ? '-' : ' '}
                </div>
                <div className="flex-1 px-2 overflow-x-auto whitespace-pre">
                  {line.content}
                </div>
              </div>
            ))}
        </div>

        {/* Right side - additions */}
        <div>
          {file.lines
            .filter((line) => line.type === 'add' || line.type === 'context')
            .map((line, idx) => (
              <div
                key={`right-${idx}`}
                className={`flex ${getLineClass(line.type)}`}
                onClick={() =>
                  line.newLineNumber &&
                  onLineClick?.(file.filename, line.newLineNumber)
                }
              >
                <div className="flex-shrink-0 w-16 px-2 text-right text-muted-foreground select-none border-r">
                  {line.newLineNumber || ''}
                </div>
                <div className="flex-shrink-0 w-8 px-2 text-muted-foreground select-none">
                  {line.type === 'add' ? '+' : ' '}
                </div>
                <div className="flex-1 px-2 overflow-x-auto whitespace-pre">
                  {line.content}
                </div>
              </div>
            ))}
        </div>
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* File Tree Navigation */}
      <div className="lg:col-span-1">
        <Card className="p-4">
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <FileCode className="h-4 w-4" />
            Files Changed ({files.length})
          </h3>
          <div className="space-y-1">
            {files.map((file) => (
              <button
                key={file.filename}
                onClick={() => setSelectedFile(file.filename)}
                className={`w-full text-left px-2 py-1.5 rounded text-sm hover:bg-muted transition-colors ${
                  selectedFile === file.filename ? 'bg-muted' : ''
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate flex-1">{file.filename}</span>
                  <Badge
                    className={`${getStatusColor(file.status)} text-xs`}
                    variant="secondary"
                  >
                    {file.status[0].toUpperCase()}
                  </Badge>
                </div>
                <div className="flex gap-2 text-xs text-muted-foreground mt-1">
                  <span className="text-green-600">+{file.additions}</span>
                  <span className="text-red-600">-{file.deletions}</span>
                </div>
              </button>
            ))}
          </div>
        </Card>
      </div>

      {/* Diff Viewer */}
      <div className="lg:col-span-3 space-y-4">
        {/* View Controls */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Code Changes</h3>
          <div className="flex gap-2">
            <Button
              variant={viewMode === 'unified' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('unified')}
            >
              <AlignJustify className="h-4 w-4 mr-2" />
              Unified
            </Button>
            <Button
              variant={viewMode === 'split' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('split')}
            >
              <Columns2 className="h-4 w-4 mr-2" />
              Split
            </Button>
          </div>
        </div>

        {/* File Diffs */}
        <div className="space-y-4">
          {files
            .filter((file) => !selectedFile || file.filename === selectedFile)
            .map((file) => (
              <Card key={file.filename} className="overflow-hidden">
                {/* File Header */}
                <div
                  className="flex items-center justify-between p-4 bg-muted cursor-pointer"
                  onClick={() => toggleFile(file.filename)}
                >
                  <div className="flex items-center gap-2">
                    {expandedFiles.has(file.filename) ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <FileCode className="h-4 w-4" />
                    <span className="font-medium">{file.filename}</span>
                    <Badge className={getStatusColor(file.status)}>
                      {file.status}
                    </Badge>
                  </div>
                  <div className="flex gap-3 text-sm">
                    <span className="text-green-600">
                      +{file.additions} additions
                    </span>
                    <span className="text-red-600">
                      -{file.deletions} deletions
                    </span>
                  </div>
                </div>

                {/* Diff Content */}
                {expandedFiles.has(file.filename) && (
                  <div className="border-t">
                    {viewMode === 'unified'
                      ? renderUnifiedView(file)
                      : renderSplitView(file)}
                  </div>
                )}
              </Card>
            ))}
        </div>
      </div>
    </div>
  );
}
