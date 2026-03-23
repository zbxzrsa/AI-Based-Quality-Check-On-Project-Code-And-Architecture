'use client';

/**
 * CodeDiff Component
 * 
 * A comprehensive code difference viewer with:
 * - Syntax highlighting using Prism.js
 * - Inline comments on specific lines
 * - Pagination for large diffs (1000+ lines)
 * - Support for additions, deletions, and context lines
 * 
 * **Validates: Requirements 3.1, 3.5**
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { ChevronDown, ChevronRight, MessageSquare, ChevronLeft, ChevronRight as ChevronRightIcon } from 'lucide-react';
import DOMPurify from 'dompurify';

// Types
export interface DiffLine {
  type: 'add' | 'delete' | 'context';
  content: string;
  lineNumber: number;
  oldLineNumber?: number;
  newLineNumber?: number;
}

export interface DiffChunk {
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  lines: DiffLine[];
}

export interface FileDiff {
  path: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  chunks: DiffChunk[];
  language?: string;
}

export interface Comment {
  id: string;
  author: string;
  content: string;
  createdAt: Date;
  lineNumber: number;
  fileName: string;
  replies?: Comment[];
  parentId?: string;
}

export interface CodeDiffProps {
  files: FileDiff[];
  comments?: Comment[];
  onAddComment?: (fileName: string, lineNumber: number, content: string, parentId?: string) => void;
  onDeleteComment?: (commentId: string) => void;
  linesPerPage?: number;
  enablePagination?: boolean;
}

const LINES_PER_PAGE_DEFAULT = 1000;

/**
 * Detect programming language from file extension
 */
function detectLanguage(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase();
  const languageMap: Record<string, string> = {
    'js': 'javascript',
    'jsx': 'jsx',
    'ts': 'typescript',
    'tsx': 'tsx',
    'py': 'python',
    'css': 'css',
    'json': 'json',
    'md': 'markdown',
    'html': 'markup',
    'xml': 'markup',
  };
  return languageMap[ext || ''] || 'javascript';
}

/**
 * Apply syntax highlighting to code content
 * Uses dynamic import to avoid SSR issues with Prism.js
 */
async function loadPrismAndHighlight(content: string, language: string): Promise<string> {
  if (typeof window === 'undefined') {
    return content;
  }
  
  try {
    const Prism = (await import('prismjs')).default;
    await import('prismjs/themes/prism-tomorrow.css');
    await import('prismjs/components/prism-python');
    await import('prismjs/components/prism-javascript');
    await import('prismjs/components/prism-typescript');
    await import('prismjs/components/prism-jsx');
    await import('prismjs/components/prism-tsx');
    await import('prismjs/components/prism-css');
    await import('prismjs/components/prism-json');
    await import('prismjs/components/prism-markdown');
    
    const grammar = Prism.languages[language];
    if (grammar) {
      return Prism.highlight(content, grammar, language);
    }
  } catch (error) {
    console.warn('Syntax highlighting failed:', error);
  }
  return content;
}

// Simple synchronous highlight that doesn't use Prism
function simpleHighlight(content: string): string {
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * CodeDiff Component
 */
export default function CodeDiff({
  files,
  comments = [],
  onAddComment,
  onDeleteComment,
  linesPerPage = LINES_PER_PAGE_DEFAULT,
  enablePagination = true,
}: CodeDiffProps) {
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(
    new Set(files.map((f) => f.path))
  );
  const [commentingLine, setCommentingLine] = useState<{ file: string; line: number } | null>(null);
  const [commentText, setCommentText] = useState('');
  const [currentPages, setCurrentPages] = useState<Record<string, number>>({});
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');

  // Toggle file expansion
  const toggleFile = useCallback((filePath: string) => {
    setExpandedFiles((prev) => {
      const next = new Set(prev);
      if (next.has(filePath)) {
        next.delete(filePath);
      } else {
        next.add(filePath);
      }
      return next;
    });
  }, []);

  // Handle comment submission
  const handleAddComment = useCallback(() => {
    if (commentingLine && commentText.trim() && onAddComment) {
      onAddComment(commentingLine.file, commentingLine.line, commentText.trim());
      setCommentText('');
      setCommentingLine(null);
    }
  }, [commentingLine, commentText, onAddComment]);

  // Handle reply submission
  const handleAddReply = useCallback((parentId: string, fileName: string, lineNumber: number) => {
    if (replyText.trim() && onAddComment) {
      onAddComment(fileName, lineNumber, replyText.trim(), parentId);
      setReplyText('');
      setReplyingTo(null);
    }
  }, [replyText, onAddComment]);

  // Get comments for a specific line (only top-level comments, not replies)
  const getCommentsForLine = useCallback(
    (fileName: string, lineNumber: number) => {
      return comments.filter(
        (c) => c.fileName === fileName && c.lineNumber === lineNumber && !c.parentId
      );
    },
    [comments]
  );

  // Calculate total lines for a file
  const getTotalLines = useCallback((file: FileDiff) => {
    return file.chunks.reduce((total, chunk) => total + chunk.lines.length, 0);
  }, []);

  // Get paginated chunks for a file
  const getPaginatedChunks = useCallback(
    (file: FileDiff, page: number) => {
      if (!enablePagination) {
        return file.chunks;
      }

      const totalLines = getTotalLines(file);
      if (totalLines <= linesPerPage) {
        return file.chunks;
      }

      const startLine = page * linesPerPage;
      const endLine = startLine + linesPerPage;
      let currentLine = 0;
      const paginatedChunks: DiffChunk[] = [];

      for (const chunk of file.chunks) {
        const chunkEndLine = currentLine + chunk.lines.length;

        if (chunkEndLine > startLine && currentLine < endLine) {
          const lineStart = Math.max(0, startLine - currentLine);
          const lineEnd = Math.min(chunk.lines.length, endLine - currentLine);
          
          if (lineStart < lineEnd) {
            paginatedChunks.push({
              ...chunk,
              lines: chunk.lines.slice(lineStart, lineEnd),
            });
          }
        }

        currentLine = chunkEndLine;
        if (currentLine >= endLine) break;
      }

      return paginatedChunks;
    },
    [enablePagination, linesPerPage, getTotalLines]
  );

  // Get total pages for a file
  const getTotalPages = useCallback(
    (file: FileDiff) => {
      if (!enablePagination) return 1;
      const totalLines = getTotalLines(file);
      return Math.ceil(totalLines / linesPerPage);
    },
    [enablePagination, linesPerPage, getTotalLines]
  );

  // Get current page for a file
  const getCurrentPage = useCallback(
    (filePath: string) => {
      return currentPages[filePath] || 0;
    },
    [currentPages]
  );

  // Set page for a file
  const setPage = useCallback((filePath: string, page: number) => {
    setCurrentPages((prev) => ({ ...prev, [filePath]: page }));
  }, []);

  // Render line with syntax highlighting
  const renderLine = useCallback(
    async (line: DiffLine, file: FileDiff) => {
      const language = file.language || detectLanguage(file.path);
      const highlighted = typeof window !== 'undefined' 
        ? await loadPrismAndHighlight(line.content, language)
        : simpleHighlight(line.content);
      const sanitizedHtml = DOMPurify.sanitize(highlighted);
      return (
        <code
          className="whitespace-pre"
          dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
        />
      );
    },
    []
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-white">
          Files Changed ({files.length})
        </h3>
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {files.reduce((sum, f) => sum + f.additions, 0)} additions,{' '}
          {files.reduce((sum, f) => sum + f.deletions, 0)} deletions
        </div>
      </div>

      {/* File Diffs */}
      {files.map((file) => {
        const totalLines = getTotalLines(file);
        const totalPages = getTotalPages(file);
        const currentPage = getCurrentPage(file.path);
        const paginatedChunks = getPaginatedChunks(file, currentPage);
        const showPagination = enablePagination && totalLines > linesPerPage;

        return (
          <div
            key={file.path}
            className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden"
          >
            {/* File Header */}
            <button
              onClick={() => toggleFile(file.path)}
              className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                {expandedFiles.has(file.path) ? (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                )}
                <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
                  {file.path}
                </span>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    file.status === 'added'
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                      : file.status === 'deleted'
                      ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                      : file.status === 'renamed'
                      ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'
                      : 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300'
                  }`}
                >
                  {file.status}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-green-600 dark:text-green-400">
                  +{file.additions}
                </span>
                <span className="text-red-600 dark:text-red-400">
                  -{file.deletions}
                </span>
                {showPagination && (
                  <span className="text-gray-500 dark:text-gray-400">
                    {totalLines} lines
                  </span>
                )}
              </div>
            </button>

            {/* File Content */}
            {expandedFiles.has(file.path) && (
              <div className="border-t border-gray-200 dark:border-gray-700">
                {/* Pagination Controls - Top */}
                {showPagination && (
                  <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      Showing lines {currentPage * linesPerPage + 1} -{' '}
                      {Math.min((currentPage + 1) * linesPerPage, totalLines)} of{' '}
                      {totalLines}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPage(file.path, Math.max(0, currentPage - 1))}
                        disabled={currentPage === 0}
                        className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        Page {currentPage + 1} of {totalPages}
                      </span>
                      <button
                        onClick={() =>
                          setPage(file.path, Math.min(totalPages - 1, currentPage + 1))
                        }
                        disabled={currentPage >= totalPages - 1}
                        className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ChevronRightIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}

                {/* Diff Lines */}
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <tbody>
                      {paginatedChunks.map((chunk, chunkIdx) =>
                        chunk.lines.map((line, lineIdx) => {
                          const lineComments = getCommentsForLine(
                            file.path,
                            line.lineNumber
                          );
                          const isCommenting =
                            commentingLine?.file === file.path &&
                            commentingLine?.line === line.lineNumber;

                          return (
                            <tr key={`${chunkIdx}-${lineIdx}`}>
                              <td colSpan={4}>
                                {/* Diff Line */}
                                <div
                                  className={`flex items-start font-mono text-sm leading-6 ${
                                    line.type === 'add'
                                      ? 'bg-green-50 dark:bg-green-900/20'
                                      : line.type === 'delete'
                                      ? 'bg-red-50 dark:bg-red-900/20'
                                      : 'bg-white dark:bg-gray-800'
                                  }`}
                                >
                                  {/* Old Line Number */}
                                  <div className="w-12 px-2 text-right text-xs text-gray-400 select-none flex-shrink-0">
                                    {line.oldLineNumber}
                                  </div>
                                  {/* New Line Number */}
                                  <div className="w-12 px-2 text-right text-xs text-gray-400 select-none flex-shrink-0">
                                    {line.newLineNumber}
                                  </div>
                                  {/* Line Content */}
                                  <div className="flex-1 px-4 overflow-x-auto">
                                    <span
                                      className={`select-none mr-2 ${
                                        line.type === 'add'
                                          ? 'text-green-600 dark:text-green-400'
                                          : line.type === 'delete'
                                          ? 'text-red-600 dark:text-red-400'
                                          : 'text-gray-400'
                                      }`}
                                    >
                                      {line.type === 'add'
                                        ? '+'
                                        : line.type === 'delete'
                                        ? '-'
                                        : ' '}
                                    </span>
                                    {renderLine(line, file)}
                                  </div>
                                  {/* Comment Button */}
                                  {onAddComment && (
                                    <button
                                      onClick={() =>
                                        setCommentingLine({
                                          file: file.path,
                                          line: line.lineNumber,
                                        })
                                      }
                                      className="w-8 h-6 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-700 flex-shrink-0"
                                      title="Add comment"
                                    >
                                      <MessageSquare className="h-4 w-4 text-gray-400" />
                                    </button>
                                  )}
                                </div>

                                {/* Comment Form */}
                                {isCommenting && (
                                  <div className="bg-gray-50 dark:bg-gray-700/50 p-4 border-t border-gray-200 dark:border-gray-700">
                                    <textarea
                                      value={commentText}
                                      onChange={(e) => setCommentText(e.target.value)}
                                      placeholder="Add a comment..."
                                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none"
                                      rows={3}
                                      autoFocus
                                    />
                                    <div className="flex gap-2 mt-2">
                                      <button
                                        onClick={handleAddComment}
                                        disabled={!commentText.trim()}
                                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                                      >
                                        Comment
                                      </button>
                                      <button
                                        onClick={() => {
                                          setCommentingLine(null);
                                          setCommentText('');
                                        }}
                                        className="px-4 py-2 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-500 text-sm"
                                      >
                                        Cancel
                                      </button>
                                    </div>
                                  </div>
                                )}

                                {/* Existing Comments */}
                                {lineComments.length > 0 && (
                                  <div className="bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700">
                                    {lineComments.map((comment) => (
                                      <div key={comment.id}>
                                        {/* Main Comment */}
                                        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                                          <div className="flex items-start justify-between">
                                            <div className="flex-1">
                                              <div className="flex items-center gap-2 mb-1">
                                                <span className="font-medium text-sm text-gray-900 dark:text-white">
                                                  {comment.author}
                                                </span>
                                                <span className="text-xs text-gray-500 dark:text-gray-400">
                                                  {comment.createdAt.toLocaleString()}
                                                </span>
                                              </div>
                                              <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                                                {comment.content}
                                              </p>
                                              <button
                                                onClick={() => setReplyingTo(comment.id)}
                                                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                                              >
                                                Reply
                                              </button>
                                            </div>
                                            {onDeleteComment && (
                                              <button
                                                onClick={() => onDeleteComment(comment.id)}
                                                className="text-xs text-red-600 dark:text-red-400 hover:underline"
                                              >
                                                Delete
                                              </button>
                                            )}
                                          </div>

                                          {/* Reply Form */}
                                          {replyingTo === comment.id && (
                                            <div className="mt-3 ml-6 bg-white dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-600">
                                              <textarea
                                                value={replyText}
                                                onChange={(e) => setReplyText(e.target.value)}
                                                placeholder="Write a reply..."
                                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none text-sm"
                                                rows={2}
                                                autoFocus
                                              />
                                              <div className="flex gap-2 mt-2">
                                                <button
                                                  onClick={() => handleAddReply(comment.id, file.path, line.lineNumber)}
                                                  disabled={!replyText.trim()}
                                                  className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-xs"
                                                >
                                                  Reply
                                                </button>
                                                <button
                                                  onClick={() => {
                                                    setReplyingTo(null);
                                                    setReplyText('');
                                                  }}
                                                  className="px-3 py-1 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-500 text-xs"
                                                >
                                                  Cancel
                                                </button>
                                              </div>
                                            </div>
                                          )}

                                          {/* Replies */}
                                          {comment.replies && comment.replies.length > 0 && (
                                            <div className="mt-3 ml-6 space-y-3">
                                              {comment.replies.map((reply) => (
                                                <div
                                                  key={reply.id}
                                                  className="bg-white dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-600"
                                                >
                                                  <div className="flex items-start justify-between">
                                                    <div className="flex-1">
                                                      <div className="flex items-center gap-2 mb-1">
                                                        <span className="font-medium text-sm text-gray-900 dark:text-white">
                                                          {reply.author}
                                                        </span>
                                                        <span className="text-xs text-gray-500 dark:text-gray-400">
                                                          {reply.createdAt.toLocaleString()}
                                                        </span>
                                                      </div>
                                                      <p className="text-sm text-gray-700 dark:text-gray-300">
                                                        {reply.content}
                                                      </p>
                                                    </div>
                                                    {onDeleteComment && (
                                                      <button
                                                        onClick={() => onDeleteComment(reply.id)}
                                                        className="text-xs text-red-600 dark:text-red-400 hover:underline"
                                                      >
                                                        Delete
                                                      </button>
                                                    )}
                                                  </div>
                                                </div>
                                              ))}
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Pagination Controls - Bottom */}
                {showPagination && (
                  <div className="flex items-center justify-center px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPage(file.path, Math.max(0, currentPage - 1))}
                        disabled={currentPage === 0}
                        className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        Page {currentPage + 1} of {totalPages}
                      </span>
                      <button
                        onClick={() =>
                          setPage(file.path, Math.min(totalPages - 1, currentPage + 1))
                        }
                        disabled={currentPage >= totalPages - 1}
                        className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ChevronRightIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
