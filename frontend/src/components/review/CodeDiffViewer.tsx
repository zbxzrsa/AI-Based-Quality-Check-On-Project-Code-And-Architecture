'use client';

/**
 * Code Diff Viewer Component
 */
import { useState } from 'react';
import { ChevronDown, ChevronRight, MessageSquare } from 'lucide-react';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';

interface DiffLine {
    type: 'add' | 'remove' | 'context';
    oldLineNumber?: number;
    newLineNumber?: number;
    content: string;
}

interface DiffFile {
    filename: string;
    status: 'added' | 'modified' | 'removed';
    additions: number;
    deletions: number;
    lines: DiffLine[];
}

interface CodeDiffViewerProps {
    files: DiffFile[];
    onLineClick?: (file: string, line: number) => void;
    highlightedLines?: { file: string; line: number }[];
}

export default function CodeDiffViewer({
    files,
    onLineClick,
    highlightedLines = [],
}: CodeDiffViewerProps) {
    const [expandedFiles, setExpandedFiles] = useState<Set<string>>(
        new Set(files.map((f) => f.filename))
    );
    const [viewMode, setViewMode] = useState<'unified' | 'split'>('unified');

    const toggleFile = (filename: string) => {
        setExpandedFiles((prev) => {
            const next = new Set(prev);
            if (next.has(filename)) {
                next.delete(filename);
            } else {
                next.add(filename);
            }
            return next;
        });
    };

    const getLineClassName = (line: DiffLine, filename: string, lineNum?: number) => {
        const isHighlighted = highlightedLines.some(
            (hl) => hl.file === filename && hl.line === lineNum
        );

        const baseClasses = 'font-mono text-sm leading-6 px-4 hover:bg-gray-50 dark:hover:bg-gray-700/50';

        if (isHighlighted) {
            return `${baseClasses} bg-yellow-100 dark:bg-yellow-900/30 ring-2 ring-yellow-400 dark:ring-yellow-600`;
        }

        if (line.type === 'add') {
            return `${baseClasses} bg-green-50 dark:bg-green-900/20 text-green-900 dark:text-green-100`;
        }

        if (line.type === 'remove') {
            return `${baseClasses} bg-red-50 dark:bg-red-900/20 text-red-900 dark:text-red-100`;
        }

        return `${baseClasses} text-gray-700 dark:text-gray-300`;
    };

    const getLinePrefix = (type: string) => {
        if (type === 'add') return '+';
        if (type === 'remove') return '-';
        return ' ';
    };

    return (
        <div className="space-y-4">
            {/* View Mode Toggle */}
            <div className="flex items-center justify-between bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-white">
                    Files Changed ({files.length})
                </h3>
                <div className="flex rounded-md shadow-sm">
                    <button
                        onClick={() => setViewMode('unified')}
                        className={`px-4 py-2 text-sm font-medium rounded-l-md border ${viewMode === 'unified'
                                ? 'bg-primary-50 dark:bg-primary-900/30 border-primary-500 text-primary-700 dark:text-primary-300'
                                : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                            }`}
                    >
                        Unified
                    </button>
                    <button
                        onClick={() => setViewMode('split')}
                        className={`px-4 py-2 text-sm font-medium rounded-r-md border-t border-r border-b ${viewMode === 'split'
                                ? 'bg-primary-50 dark:bg-primary-900/30 border-primary-500 text-primary-700 dark:text-primary-300'
                                : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                            }`}
                    >
                        Split
                    </button>
                </div>
            </div>

            {/* File Diffs */}
            {files.map((file) => (
                <div
                    key={file.filename}
                    className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden"
                >
                    {/* File Header */}
                    <button
                        onClick={() => toggleFile(file.filename)}
                        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                    >
                        <div className="flex items-center gap-3">
                            {expandedFiles.has(file.filename) ? (
                                <ChevronDown className="h-5 w-5 text-gray-400" />
                            ) : (
                                <ChevronRight className="h-5 w-5 text-gray-400" />
                            )}
                            <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
                                {file.filename}
                            </span>
                            <span
                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${file.status === 'added'
                                        ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                                        : file.status === 'removed'
                                            ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                                            : 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300'
                                    }`}
                            >
                                {file.status}
                            </span>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                            <span className="text-green-600 dark:text-green-400">+{file.additions}</span>
                            <span className="text-red-600 dark:text-red-400">-{file.deletions}</span>
                        </div>
                    </button>

                    {/* File Content */}
                    {expandedFiles.has(file.filename) && (
                        <div className="border-t border-gray-200 dark:border-gray-700">
                            <div className="overflow-x-auto">
                                <table className="w-full border-collapse">
                                    <tbody>
                                        {file.lines.map((line, idx) => (
                                            <tr
                                                key={idx}
                                                className={getLineClassName(file.filename, line.newLineNumber || line.oldLineNumber)}
                                                onClick={() =>
                                                    onLineClick?.(file.filename, line.newLineNumber || line.oldLineNumber || 0)
                                                }
                                            >
                                                {/* Old Line Number */}
                                                <td className="w-12 px-2 text-right text-xs text-gray-400 select-none">
                                                    {line.oldLineNumber}
                                                </td>
                                                {/* New Line Number */}
                                                <td className="w-12 px-2 text-right text-xs text-gray-400 select-none">
                                                    {line.newLineNumber}
                                                </td>
                                                {/* Line Content */}
                                                <td className="px-4">
                                                    <span className="select-none text-gray-400 mr-2">
                                                        {getLinePrefix(line.type)}
                                                    </span>
                                                    <code>{line.content}</code>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
