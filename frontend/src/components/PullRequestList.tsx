/**
 * PullRequestList Component
 * 
 * Displays a filterable list of pull requests
 */

import React, { useMemo } from 'react';
import type { PullRequest, User } from '../types/pullRequest';

interface PullRequestListProps {
  pullRequests: PullRequest[];
  filterStatus: PullRequest['status'] | 'all';
  onFilterChange: (status: PullRequest['status'] | 'all') => void;
  onSelectPR: (pr: PullRequest) => void;
}

export const PullRequestList: React.FC<PullRequestListProps> = ({
  pullRequests,
  filterStatus,
  onFilterChange,
  onSelectPR,
}) => {
  // Filter PRs by status
  const filteredPRs = useMemo(() => {
    if (filterStatus === 'all') {
      return pullRequests;
    }
    return pullRequests.filter((pr) => pr.status === filterStatus);
  }, [pullRequests, filterStatus]);

  const getStatusColor = (status: PullRequest['status']) => {
    switch (status) {
      case 'open': return '#007bff';
      case 'approved': return '#28a745';
      case 'rejected': return '#dc3545';
      case 'merged': return '#6f42c1';
      case 'closed': return '#6c757d';
      default: return '#6c757d';
    }
  };

  const getStatusIcon = (status: PullRequest['status']) => {
    switch (status) {
      case 'open': return '🔄';
      case 'approved': return '✅';
      case 'rejected': return '❌';
      case 'merged': return '🔀';
      case 'closed': return '🔒';
      default: return '❓';
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Pull Requests ({filteredPRs.length})</h2>
        
        <div style={styles.filterContainer}>
          <label style={styles.filterLabel}>Filter by status:</label>
          <select
            value={filterStatus}
            onChange={(e) => onFilterChange(e.target.value as PullRequest['status'] | 'all')}
            style={styles.filterSelect}
          >
            <option value="all">All</option>
            <option value="open">Open</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="merged">Merged</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>

      <div style={styles.prList}>
        {filteredPRs.length === 0 ? (
          <div style={styles.emptyState}>
            <p>No pull requests found for the selected filter.</p>
          </div>
        ) : (
          filteredPRs.map((pr) => (
            <div
              key={pr.id}
              style={styles.prCard}
              onClick={() => onSelectPR(pr)}
            >
              <div style={styles.prHeader}>
                <div style={styles.prTitle}>
                  <span style={styles.prNumber}>#{pr.number}</span>
                  <span style={styles.prTitleText}>{pr.title}</span>
                </div>
                <div
                  style={{
                    ...styles.statusBadge,
                    backgroundColor: getStatusColor(pr.status),
                  }}
                >
                  {getStatusIcon(pr.status)} {pr.status.toUpperCase()}
                </div>
              </div>

              <div style={styles.prMeta}>
                <div style={styles.prAuthor}>
                  <img
                    src={pr.author.avatar || '/default-avatar.png'}
                    alt={pr.author.name}
                    style={styles.avatar}
                  />
                  <span>{pr.author.name}</span>
                </div>
                <div style={styles.prBranches}>
                  {pr.sourceBranch} → {pr.targetBranch}
                </div>
              </div>

              <div style={styles.prStats}>
                <span style={styles.statItem}>
                  +{pr.diff.totalAdditions} -{pr.diff.totalDeletions}
                </span>
                <span style={styles.statItem}>
                  {pr.diff.files.length} files
                </span>
                <span style={styles.statItem}>
                  {pr.comments.length} comments
                </span>
              </div>

              <div style={styles.prFooter}>
                <span style={styles.timestamp}>
                  Created {pr.createdAt.toLocaleDateString()}
                </span>
                <div style={styles.reviewers}>
                  {pr.reviewers.slice(0, 3).map((reviewer) => (
                    <img
                      key={reviewer.id}
                      src={reviewer.avatar || '/default-avatar.png'}
                      alt={reviewer.name}
                      style={styles.reviewerAvatar}
                      title={reviewer.name}
                    />
                  ))}
                  {pr.reviewers.length > 3 && (
                    <span style={styles.moreReviewers}>
                      +{pr.reviewers.length - 3}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    flexWrap: 'wrap' as const,
    gap: '10px',
  },
  title: {
    margin: 0,
    color: '#333',
    fontSize: '24px',
  },
  filterContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  filterLabel: {
    fontSize: '14px',
    color: '#666',
  },
  filterSelect: {
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
  },
  prList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  },
  emptyState: {
    textAlign: 'center' as const,
    padding: '40px',
    color: '#666',
  },
  prCard: {
    border: '1px solid #e1e5e9',
    borderRadius: '8px',
    padding: '16px',
    backgroundColor: '#fff',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    ':hover': {
      borderColor: '#0366d6',
      boxShadow: '0 2px 8px rgba(3, 102, 214, 0.1)',
    },
  },
  prHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '12px',
    gap: '10px',
  },
  prTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flex: 1,
  },
  prNumber: {
    color: '#666',
    fontSize: '14px',
    fontWeight: 'bold',
  },
  prTitleText: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#0366d6',
  },
  statusBadge: {
    padding: '4px 8px',
    borderRadius: '12px',
    color: '#fff',
    fontSize: '12px',
    fontWeight: 'bold',
    whiteSpace: 'nowrap' as const,
  },
  prMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
    fontSize: '14px',
    color: '#666',
  },
  prAuthor: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  avatar: {
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    objectFit: 'cover' as const,
  },
  prBranches: {
    fontFamily: 'monospace',
    fontSize: '12px',
    backgroundColor: '#f6f8fa',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  prStats: {
    display: 'flex',
    gap: '16px',
    marginBottom: '12px',
    fontSize: '12px',
    color: '#666',
  },
  statItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  prFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '12px',
    color: '#666',
  },
  timestamp: {},
  reviewers: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  reviewerAvatar: {
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    objectFit: 'cover' as const,
  },
  moreReviewers: {
    fontSize: '10px',
    color: '#666',
  },
};