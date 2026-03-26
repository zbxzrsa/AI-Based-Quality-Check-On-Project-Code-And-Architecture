/**
 * Pull Request Types
 *
 * Shared type definitions for pull request related components
 */

import type { FileDiff } from '../components/CodeDiff';

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: 'admin' | 'developer' | 'viewer';
}

export interface Approver {
  user: User;
  status: 'pending' | 'approved' | 'rejected';
  comment?: string;
  timestamp: Date;
}

export interface PullRequestComment {
  id: string;
  author: User;
  content: string;
  createdAt: Date;
  lineNumber: number;
  filePath: string;
  replies?: PullRequestComment[];
  parentId?: string;
}

export interface PullRequest {
  id: string;
  number: number;
  title: string;
  description: string;
  author: User;
  status: 'open' | 'approved' | 'rejected' | 'merged' | 'closed';
  sourceBranch: string;
  targetBranch: string;
  approvers: Approver[];
  reviewers: User[];
  diff: {
    files: FileDiff[];
    totalAdditions: number;
    totalDeletions: number;
    totalChanges: number;
  };
  comments: PullRequestComment[];
  createdAt: Date;
  updatedAt: Date;
}

export interface PullRequestsProps {
  /** Optional initial PR list */
  initialPRs?: PullRequest[];
}
