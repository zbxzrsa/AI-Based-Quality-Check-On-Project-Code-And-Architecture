/**
 * PullRequests评论featurepropertytest
 * 
 * Feature: frontend-production-optimization
 * Property 14: 评论threadcreate
 * 
 * **Validates: Requirements 3.2**
 * 
 * testCoverage:
 * - 对于任何code行上的评论add操作，shouldcreate评论thread并support后续回复
 * 
 * note: testVerifiesPullRequestscomponent的评论threadcreateand回复feature的正确性。
 */

import React from 'react';
import fc from 'fast-check';
import { render, screen, cleanup, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PullRequests, PullRequest, User } from '../PullRequests';
import type { FileDiff, Comment } from '../../components/CodeDiff';

// Mock ErrorBoundary
jest.mock('../../components/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock LoadingState
jest.mock('../../components/LoadingState', () => ({
  LoadingState: ({ text }: { text: string }) => <div>{text}</div>,
}));

// Mock CodeDiff with comment functionality
jest.mock('../../components/CodeDiff', () => {
  const React = require('react');
  return {
    __esModule: true,
    default: ({ files, comments, onAddComment, onDeleteComment }: any) => {
      const [localComments, setLocalComments] = React.useState(comments || []);
      
      React.useEffect(() => {
        setLocalComments(comments || []);
      }, [comments]);

      const handleAddComment = (fileName: string, lineNumber: number, content: string, parentId?: string) => {
        if (onAddComment) {
          onAddComment(fileName, lineNumber, content, parentId);
        }
      };

      const handleDeleteComment = (commentId: string) => {
        if (onDeleteComment) {
          onDeleteComment(commentId);
        }
      };

      const renderComment = (comment: any, depth: number = 0) => (
        <div 
          key={comment.id} 
          data-testid={`comment-${comment.id}`}
          style={{ marginLeft: `${depth * 20}px` }}
        >
          <div data-testid={`comment-author-${comment.id}`}>{comment.author}</div>
          <div data-testid={`comment-content-${comment.id}`}>{comment.content}</div>
          <div data-testid={`comment-line-${comment.id}`}>Line: {comment.lineNumber}</div>
          <button 
            data-testid={`reply-button-${comment.id}`}
            onClick={() => handleAddComment(comment.fileName, comment.lineNumber, `Reply to ${comment.id}`, comment.id)}
          >
            Reply
          </button>
          <button 
            data-testid={`delete-button-${comment.id}`}
            onClick={() => handleDeleteComment(comment.id)}
          >
            Delete
          </button>
          {comment.replies && comment.replies.length > 0 && (
            <div data-testid={`replies-${comment.id}`}>
              {comment.replies.map((reply: any) => renderComment(reply, depth + 1))}
            </div>
          )}
        </div>
      );

      return (
        <div data-testid="code-diff">
          <div data-testid="files-count">Files: {files.length}</div>
          {files.map((file: any, index: number) => (
            <div key={index} data-testid={`file-${index}`}>
              <div data-testid={`file-path-${index}`}>{file.path}</div>
              {file.chunks && file.chunks.map((chunk: any, chunkIndex: number) => (
                <div key={chunkIndex} data-testid={`chunk-${index}-${chunkIndex}`}>
                  {chunk.lines && chunk.lines.map((line: any, lineIndex: number) => (
                    <div key={lineIndex} data-testid={`line-${index}-${line.lineNumber || lineIndex}`}>
                      <span>{line.content}</span>
                      <button
                        data-testid={`add-comment-${index}-${line.lineNumber || lineIndex}`}
                        onClick={() => handleAddComment(file.path, line.lineNumber || lineIndex, `Comment on line ${line.lineNumber || lineIndex}`)}
                      >
                        Add Comment
                      </button>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ))}
          <div data-testid="comments-section">
            {localComments.map((comment: any) => renderComment(comment))}
          </div>
        </div>
      );
    },
  };
});

// Helper function to create mock user
const createMockUser = (overrides?: Partial<User>): User => ({
  id: 'user-1',
  name: 'Test User',
  email: 'test@example.com',
  role: 'developer',
  ...overrides,
});

// Helper function to create mock file diff
const createMockFileDiff = (overrides?: Partial<FileDiff>): FileDiff => ({
  path: 'src/test.ts',
  status: 'modified',
  additions: 10,
  deletions: 5,
  chunks: [
    {
      oldStart: 1,
      oldLines: 5,
      newStart: 1,
      newLines: 10,
      lines: [
        {
          type: 'add',
          content: 'console.log("test");',
          lineNumber: 1,
          newLineNumber: 1,
        },
        {
          type: 'add',
          content: 'const x = 42;',
          lineNumber: 2,
          newLineNumber: 2,
        },
        {
          type: 'context',
          content: 'function test() {',
          lineNumber: 3,
          newLineNumber: 3,
        },
      ],
    },
  ],
  ...overrides,
});

// Helper function to create mock PR
const createMockPR = (overrides?: Partial<PullRequest>): PullRequest => ({
  id: 'pr-1',
  number: 1,
  title: 'Test PR',
  description: 'Test description',
  author: createMockUser(),
  status: 'open',
  sourceBranch: 'feature/test',
  targetBranch: 'main',
  approvers: [],
  reviewers: [],
  diff: {
    files: [createMockFileDiff()],
    totalAdditions: 10,
    totalDeletions: 5,
    totalChanges: 15,
  },
  comments: [],
  createdAt: new Date('2024-01-01'),
  updatedAt: new Date('2024-01-02'),
  ...overrides,
});

describe('Property 14: 评论threadcreate', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // customGenerator：generate有效的filepath
  const filePathArbitrary = () =>
    fc.oneof(
      fc.constantFrom(
        'src/index.ts',
        'src/components/Button.tsx',
        'src/utils/helpers.ts',
        'src/services/api.ts',
        'tests/unit/example.test.ts'
      ),
      fc.string({ minLength: 5, maxLength: 50 }).map(s => `src/${s}.ts`)
    );

  // customGenerator：generate有效的行号
  const lineNumberArbitrary = () => fc.integer({ min: 1, max: 1000 });

  // customGenerator：generate有效的评论content
  const commentContentArbitrary = () =>
    fc.oneof(
      fc.constantFrom(
        'This looks good',
        'Please fix this',
        'Can you explain this logic?',
        'LGTM',
        'Consider refactoring this',
        'Add error handling here'
      ),
      fc.string({ minLength: 5, maxLength: 200 }).filter(s => s.trim().length >= 5)
    );

  // customGenerator：generateuser名
  const userNameArbitrary = () =>
    fc.constantFrom('Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank');

  it('should为任何code行create评论thread', async () => {
    await fc.assert(
      fc.asyncProperty(
        filePathArbitrary(),
        lineNumberArbitrary(),
        commentContentArbitrary(),
        async (fileName, lineNumber, commentContent) => {
          const fileDiff = createMockFileDiff({
            path: fileName,
            chunks: [
              {
                oldStart: 1,
                oldLines: 10,
                newStart: 1,
                newLines: 10,
                lines: Array.from({ length: 10 }, (_, i) => ({
                  type: 'add' as const,
                  content: `Line ${i + 1} content`,
                  lineNumber: i + 1,
                  newLineNumber: i + 1,
                })),
              },
            ],
          });

          const pr = createMockPR({
            diff: {
              files: [fileDiff],
              totalAdditions: 10,
              totalDeletions: 0,
              totalChanges: 10,
            },
            comments: [],
          });

          const { unmount, container } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          const prTitle = screen.getByText('Test PR');
          await userEvent.click(prTitle);

          // waitrendercomplete
          await new Promise(resolve => setTimeout(resolve, 100));

          // verifyCodeDiff已render
          const codeDiff = screen.getByTestId('code-diff');
          expect(codeDiff).toBeInTheDocument();

          // 查找add评论button（use第一item可用的行）
          const addCommentButtons = container.querySelectorAll('[data-testid^="add-comment-"]');
          expect(addCommentButtons.length).toBeGreaterThan(0);

          // 点击第一itemadd评论button
          const firstButton = addCommentButtons[0] as HTMLButtonElement;
          await userEvent.click(firstButton);

          // wait评论add
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify评论已create
          const commentsSection = screen.getByTestId('comments-section');
          expect(commentsSection).toBeInTheDocument();

          // verify评论content存在
          const comments = container.querySelectorAll('[data-testid^="comment-"]');
          expect(comments.length).toBeGreaterThan(0);

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);

  it('shouldsupport在评论thread中add回复', async () => {
    await fc.assert(
      fc.asyncProperty(
        commentContentArbitrary(),
        commentContentArbitrary(),
        async (originalComment, replyComment) => {
          const existingComment: Comment = {
            id: 'comment-1',
            author: 'Reviewer',
            content: originalComment,
            createdAt: new Date(),
            lineNumber: 1,
            fileName: 'src/test.ts',
            replies: [],
          };

          const pr = createMockPR({
            comments: [existingComment],
          });

          const { unmount, container } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          await userEvent.click(screen.getByText('Test PR'));
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify原始评论存在
          const originalCommentElement = screen.getByTestId('comment-comment-1');
          expect(originalCommentElement).toBeInTheDocument();

          // 点击回复button
          const replyButton = screen.getByTestId('reply-button-comment-1');
          await userEvent.click(replyButton);
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify回复已add
          const repliesSection = container.querySelector('[data-testid="replies-comment-1"]');
          expect(repliesSection).toBeInTheDocument();

          // verify回复content
          const replies = repliesSection?.querySelectorAll('[data-testid^="comment-"]');
          expect(replies && replies.length).toBeGreaterThan(0);

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);

  it('shouldsupport多层嵌套回复', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 2, max: 5 }),
        async (replyDepth) => {
          const pr = createMockPR({
            comments: [
              {
                id: 'comment-1',
                author: 'User1',
                content: 'Original comment',
                createdAt: new Date(),
                lineNumber: 1,
                fileName: 'src/test.ts',
                replies: [],
              },
            ],
          });

          const { unmount, container } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          await userEvent.click(screen.getByText('Test PR'));
          await new Promise(resolve => setTimeout(resolve, 100));

          // add多层回复
          let currentCommentId = 'comment-1';
          for (let i = 0; i < replyDepth; i++) {
            const replyButton = screen.getByTestId(`reply-button-${currentCommentId}`);
            await userEvent.click(replyButton);
            await new Promise(resolve => setTimeout(resolve, 100));

            // 查找新add的回复
            const repliesSection = container.querySelector(`[data-testid="replies-${currentCommentId}"]`);
            expect(repliesSection).toBeInTheDocument();

            // get最新的回复ID（简化handle，实际should从DOM中提取）
            const newReplies = repliesSection?.querySelectorAll('[data-testid^="comment-"]');
            if (newReplies && newReplies.length > 0) {
              const lastReply = newReplies[newReplies.length - 1];
              const replyId = lastReply.getAttribute('data-testid')?.replace('comment-', '');
              if (replyId) {
                currentCommentId = replyId;
              }
            }
          }

          // verify嵌套结构存在
          const allComments = container.querySelectorAll('[data-testid^="comment-"]');
          expect(allComments.length).toBeGreaterThanOrEqual(replyDepth + 1);

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);

  it('should为不同code行create独立的评论thread', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(lineNumberArbitrary(), { minLength: 2, maxLength: 5 }).map(arr => [...new Set(arr)]),
        async (lineNumbers) => {
          if (lineNumbers.length < 2) return; // need至少2item不同的行号

          const fileDiff = createMockFileDiff({
            chunks: [
              {
                oldStart: 1,
                oldLines: Math.max(...lineNumbers),
                newStart: 1,
                newLines: Math.max(...lineNumbers),
                lines: lineNumbers.map(lineNum => ({
                  type: 'add' as const,
                  content: `Line ${lineNum} content`,
                  lineNumber: lineNum,
                  newLineNumber: lineNum,
                })),
              },
            ],
          });

          const pr = createMockPR({
            diff: {
              files: [fileDiff],
              totalAdditions: lineNumbers.length,
              totalDeletions: 0,
              totalChanges: lineNumbers.length,
            },
            comments: [],
          });

          const { unmount, container } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          await userEvent.click(screen.getByText('Test PR'));
          await new Promise(resolve => setTimeout(resolve, 100));

          // 为每item行号add评论
          for (const lineNum of lineNumbers.slice(0, 2)) {
            const addCommentButton = container.querySelector(
              `[data-testid="add-comment-0-${lineNum}"]`
            ) as HTMLButtonElement;
            
            if (addCommentButton) {
              await userEvent.click(addCommentButton);
              await new Promise(resolve => setTimeout(resolve, 100));
            }
          }

          // verifycreate了多item独立的评论
          const comments = container.querySelectorAll('[data-testid^="comment-"]');
          expect(comments.length).toBeGreaterThanOrEqual(2);

          // verify评论关联到不同的行号
          const commentLines = Array.from(comments).map(comment => {
            const lineElement = comment.querySelector('[data-testid^="comment-line-"]');
            return lineElement?.textContent;
          });

          const uniqueLines = new Set(commentLines);
          expect(uniqueLines.size).toBeGreaterThanOrEqual(2);

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);

  it('should保持评论thread的作者info', async () => {
    await fc.assert(
      fc.asyncProperty(
        userNameArbitrary(),
        commentContentArbitrary(),
        async (authorName, commentContent) => {
          const comment: Comment = {
            id: 'comment-1',
            author: authorName,
            content: commentContent,
            createdAt: new Date(),
            lineNumber: 1,
            fileName: 'src/test.ts',
            replies: [],
          };

          const pr = createMockPR({
            comments: [comment],
          });

          const { unmount } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          await userEvent.click(screen.getByText('Test PR'));
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify作者infoshow
          const authorElement = screen.getByTestId('comment-author-comment-1');
          expect(authorElement).toHaveTextContent(authorName);

          // verify评论contentshow
          const contentElement = screen.getByTestId('comment-content-comment-1');
          expect(contentElement).toHaveTextContent(commentContent);

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);

  it('shouldsupportdelete评论and回复', async () => {
    await fc.assert(
      fc.asyncProperty(
        commentContentArbitrary(),
        async (commentContent) => {
          const comment: Comment = {
            id: 'comment-1',
            author: 'User1',
            content: commentContent,
            createdAt: new Date(),
            lineNumber: 1,
            fileName: 'src/test.ts',
            replies: [
              {
                id: 'reply-1',
                author: 'User2',
                content: 'Reply content',
                createdAt: new Date(),
                lineNumber: 1,
                fileName: 'src/test.ts',
                parentId: 'comment-1',
              },
            ],
          };

          const pr = createMockPR({
            comments: [comment],
          });

          const { unmount, container } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          await userEvent.click(screen.getByText('Test PR'));
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify评论and回复都存在
          expect(screen.getByTestId('comment-comment-1')).toBeInTheDocument();
          expect(screen.getByTestId('comment-reply-1')).toBeInTheDocument();

          // delete回复
          const deleteReplyButton = screen.getByTestId('delete-button-reply-1');
          await userEvent.click(deleteReplyButton);
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify回复已delete
          expect(screen.queryByTestId('comment-reply-1')).not.toBeInTheDocument();

          // verify原始评论仍然存在
          expect(screen.getByTestId('comment-comment-1')).toBeInTheDocument();

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);

  it('shouldBeAt多itemfile中support评论thread', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(filePathArbitrary(), { minLength: 2, maxLength: 5 }).map(arr => [...new Set(arr)]),
        async (filePaths) => {
          if (filePaths.length < 2) return; // need至少2item不同的file

          const files = filePaths.map(path =>
            createMockFileDiff({
              path,
              chunks: [
                {
                  oldStart: 1,
                  oldLines: 5,
                  newStart: 1,
                  newLines: 5,
                  lines: [
                    {
                      type: 'add' as const,
                      content: 'Line 1',
                      lineNumber: 1,
                      newLineNumber: 1,
                    },
                  ],
                },
              ],
            })
          );

          const pr = createMockPR({
            diff: {
              files,
              totalAdditions: files.length,
              totalDeletions: 0,
              totalChanges: files.length,
            },
            comments: [],
          });

          const { unmount, container } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          await userEvent.click(screen.getByText('Test PR'));
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify所有file都已render
          const fileElements = container.querySelectorAll('[data-testid^="file-"]');
          expect(fileElements.length).toBe(filePaths.length);

          // 为前两itemfileadd评论
          for (let i = 0; i < Math.min(2, filePaths.length); i++) {
            const addCommentButton = container.querySelector(
              `[data-testid="add-comment-${i}-1"]`
            ) as HTMLButtonElement;
            
            if (addCommentButton) {
              await userEvent.click(addCommentButton);
              await new Promise(resolve => setTimeout(resolve, 100));
            }
          }

          // verifycreate了多item评论
          const comments = container.querySelectorAll('[data-testid^="comment-"]');
          expect(comments.length).toBeGreaterThanOrEqual(2);

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);

  it('should保持评论thread的时间顺序', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(commentContentArbitrary(), { minLength: 2, maxLength: 5 }),
        async (commentContents) => {
          const comments: Comment[] = commentContents.map((content, index) => ({
            id: `comment-${index + 1}`,
            author: `User${index + 1}`,
            content,
            createdAt: new Date(Date.now() + index * 1000), // 确保时间递增
            lineNumber: 1,
            fileName: 'src/test.ts',
            replies: [],
          }));

          const pr = createMockPR({
            comments,
          });

          const { unmount, container } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          await userEvent.click(screen.getByText('Test PR'));
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify所有评论都已render
          const commentElements = container.querySelectorAll('[data-testid^="comment-comment-"]');
          expect(commentElements.length).toBe(commentContents.length);

          // verify评论按顺序show
          commentElements.forEach((element, index) => {
            const contentElement = element.querySelector(`[data-testid="comment-content-comment-${index + 1}"]`);
            expect(contentElement).toHaveTextContent(commentContents[index]);
          });

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);

  it('shouldBeAt评论thread中保持file名and行号info', async () => {
    await fc.assert(
      fc.asyncProperty(
        filePathArbitrary(),
        lineNumberArbitrary(),
        commentContentArbitrary(),
        async (fileName, lineNumber, content) => {
          const comment: Comment = {
            id: 'comment-1',
            author: 'Reviewer',
            content,
            createdAt: new Date(),
            lineNumber,
            fileName,
            replies: [],
          };

          const pr = createMockPR({
            comments: [comment],
          });

          const { unmount } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          await userEvent.click(screen.getByText('Test PR'));
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify行号info
          const lineElement = screen.getByTestId('comment-line-comment-1');
          expect(lineElement).toHaveTextContent(`Line: ${lineNumber}`);

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);

  it('shouldsupport在同一行上create多item评论thread', async () => {
    await fc.assert(
      fc.asyncProperty(
        lineNumberArbitrary(),
        fc.array(commentContentArbitrary(), { minLength: 2, maxLength: 4 }),
        async (lineNumber, commentContents) => {
          const comments: Comment[] = commentContents.map((content, index) => ({
            id: `comment-${index + 1}`,
            author: `User${index + 1}`,
            content,
            createdAt: new Date(Date.now() + index * 1000),
            lineNumber,
            fileName: 'src/test.ts',
            replies: [],
          }));

          const pr = createMockPR({
            comments,
          });

          const { unmount, container } = render(<PullRequests initialPRs={[pr]} />);

          // openPRdetail
          await userEvent.click(screen.getByText('Test PR'));
          await new Promise(resolve => setTimeout(resolve, 100));

          // verify所有评论都已render
          const commentElements = container.querySelectorAll('[data-testid^="comment-comment-"]');
          expect(commentElements.length).toBe(commentContents.length);

          // verify所有评论都关联到同一行
          commentElements.forEach(element => {
            const lineElement = element.querySelector('[data-testid^="comment-line-"]');
            expect(lineElement).toHaveTextContent(`Line: ${lineNumber}`);
          });

          unmount();
          cleanup();
        }
      ),
      { numRuns: 100 }
    );
  }, 60000);
});
