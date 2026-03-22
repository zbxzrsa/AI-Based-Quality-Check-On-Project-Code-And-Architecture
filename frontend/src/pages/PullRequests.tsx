/**
 * PullRequests Page Component
 * 
 * Features:
 * - Display Pull Request list
 * - Integrate CodeDiff component to show code differences
 * - Support viewing PR details and code changes
 * - Wrapped with ErrorBoundary
 * 
 * Verification Requirement: 3.1
 */

'use client';

import React, { useState, useCallback } from 'react';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { LoadingState } from '../components/LoadingState';
import { PullRequestList } from '../components/PullRequestList';
import { PullRequestDetail } from '../components/PullRequestDetail';
import type { PullRequest, PullRequestsProps } from '../types/pullRequest';
import type { Comment } from '../components/CodeDiff';
import '../styles/responsive.css';

/**
 * PullRequests Page Main Component
 */
export const PullRequestsComponent: React.FC<PullRequestsProps> = ({ initialPRs = [] }) => {
  const [pullRequests, setPullRequests] = useState<PullRequest[]>(initialPRs);
  const [selectedPR, setSelectedPR] = useState<PullRequest | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [filterStatus, setFilterStatus] = useState<PullRequest['status'] | 'all'>('all');

  // Handle PR selection
  const handleSelectPR = useCallback((pr: PullRequest) => {
    setSelectedPR(pr);
  }, []);

  // Handle back to list
  const handleBackToList = useCallback(() => {
    setSelectedPR(null);
  }, []);

  // Handle approval submission
  const handleApprovalSubmit = useCallback((decision: 'approved' | 'rejected', comment?: string) => {
    if (!selectedPR) return;

    // Update the PR with the new approval
    const updatedPR = {
      ...selectedPR,
      status: decision as PullRequest['status'],
      approvers: [
        ...selectedPR.approvers,
        {
          user: {
            id: 'current-user',
            name: 'Current User',
            email: 'user@example.com',
            role: 'developer' as const,
          },
          status: decision,
          comment,
          timestamp: new Date(),
        },
      ],
      updatedAt: new Date(),
    };

    // Update the PR in the list
    setPullRequests(prev => 
      prev.map(pr => pr.id === selectedPR.id ? updatedPR : pr)
    );
    
    // Update the selected PR
    setSelectedPR(updatedPR);
  }, [selectedPR]);

  // Handle add comment
  const handleAddComment = useCallback(
    (fileName: string, lineNumber: number, content: string, parentId?: string) => {
    if (!selectedPR) return;

    const newComment: Comment = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      author: 'Current User',
      content,
      createdAt: new Date(),
      lineNumber,
      fileName,
      parentId,
    };

    const comments = parentId
      ? selectedPR.comments.map((existing) => {
          if (existing.id !== parentId) {
            return existing;
          }
          return {
            ...existing,
            replies: [...(existing.replies || []), newComment],
          };
        })
      : [...selectedPR.comments, newComment];

    const updatedPR = {
      ...selectedPR,
      comments,
      updatedAt: new Date(),
    };

    // Update the PR in the list
    setPullRequests(prev => 
      prev.map(pr => pr.id === selectedPR.id ? updatedPR : pr)
    );
    
    // Update the selected PR
    setSelectedPR(updatedPR);
    },
    [selectedPR]
  );

  if (loading) {
    return <LoadingState message="Loading pull requests..." />;
  }

  if (error) {
    return (
      <div style={styles.errorContainer}>
        <h2>Error Loading Pull Requests</h2>
        <p>{error.message}</p>
        <button 
          onClick={() => {
            setError(null);
            setLoading(false);
          }}
          style={styles.retryButton}
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div style={styles.container}>
        {selectedPR ? (
          <PullRequestDetail
            pullRequest={selectedPR}
            onBack={handleBackToList}
            onApprovalSubmit={handleApprovalSubmit}
            onAddComment={handleAddComment}
          />
        ) : (
          <PullRequestList
            pullRequests={pullRequests}
            filterStatus={filterStatus}
            onFilterChange={setFilterStatus}
            onSelectPR={handleSelectPR}
          />
        )}
      </div>
    </ErrorBoundary>
  );
};

/**
 * Main PullRequests component with error boundary
 */
const PullRequests: React.FC<PullRequestsProps> = (props) => {
  return (
    <ErrorBoundary>
      <PullRequestsComponent {...props} />
    </ErrorBoundary>
  );
};

export default PullRequests;

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f6f8fa',
  },
  errorContainer: {
    padding: '40px',
    textAlign: 'center' as const,
    backgroundColor: '#f8f9fa',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column' as const,
    justifyContent: 'center',
    alignItems: 'center',
  },
  retryButton: {
    padding: '10px 20px',
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    marginTop: '16px',
  },
};
