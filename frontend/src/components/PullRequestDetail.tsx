/**
 * PullRequestDetail Component
 * 
 * Displays detailed view of a pull request with code diff
 */

import React, { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import type { PullRequest, User } from '../types/pullRequest';
import type { Comment } from '../components/CodeDiff';
import { ApprovalActions } from './ApprovalActions';

const CodeDiff = dynamic(() => import('../components/CodeDiff').then(mod => ({ default: mod.default })), {
  ssr: false,
  loading: () => <div className="p-4">Loading...</div>
});

interface PullRequestDetailProps {
  pullRequest: PullRequest;
  onBack: () => void;
  onApprovalSubmit: (decision: 'approved' | 'rejected', comment?: string) => void;
  onAddComment: (comment: Comment) => void;
}

export const PullRequestDetail: React.FC<PullRequestDetailProps> = ({
  pullRequest,
  onBack,
  onApprovalSubmit,
  onAddComment,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'files' | 'comments'>('overview');

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

  const renderOverview = () => (
    <div style={styles.overview}>
      <div style={styles.description}>
        <h3>Description</h3>
        <p>{pullRequest.description || 'No description provided.'}</p>
      </div>

      <div style={styles.metadata}>
        <div style={styles.metaSection}>
          <h4>Details</h4>
          <div style={styles.metaItem}>
            <strong>Author:</strong> {pullRequest.author.name}
          </div>
          <div style={styles.metaItem}>
            <strong>Branches:</strong> {pullRequest.sourceBranch} → {pullRequest.targetBranch}
          </div>
          <div style={styles.metaItem}>
            <strong>Created:</strong> {pullRequest.createdAt.toLocaleDateString()}
          </div>
          <div style={styles.metaItem}>
            <strong>Updated:</strong> {pullRequest.updatedAt.toLocaleDateString()}
          </div>
        </div>

        <div style={styles.metaSection}>
          <h4>Changes</h4>
          <div style={styles.metaItem}>
            <strong>Files:</strong> {pullRequest.diff.files.length}
          </div>
          <div style={styles.metaItem}>
            <strong>Additions:</strong> <span style={{ color: '#28a745' }}>+{pullRequest.diff.totalAdditions}</span>
          </div>
          <div style={styles.metaItem}>
            <strong>Deletions:</strong> <span style={{ color: '#dc3545' }}>-{pullRequest.diff.totalDeletions}</span>
          </div>
        </div>

        <div style={styles.metaSection}>
          <h4>Reviewers</h4>
          <div style={styles.reviewersList}>
            {pullRequest.reviewers.map((reviewer) => (
              <div key={reviewer.id} style={styles.reviewer}>
                <img
                  src={reviewer.avatar || '/default-avatar.png'}
                  alt={reviewer.name}
                  style={styles.reviewerAvatar}
                />
                <span>{reviewer.name}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={styles.metaSection}>
          <h4>Approvals</h4>
          <div style={styles.approvalsList}>
            {pullRequest.approvers.map((approver, index) => (
              <div key={index} style={styles.approval}>
                <img
                  src={approver.user.avatar || '/default-avatar.png'}
                  alt={approver.user.name}
                  style={styles.reviewerAvatar}
                />
                <div style={styles.approvalInfo}>
                  <div style={styles.approverName}>{approver.user.name}</div>
                  <div style={{
                    ...styles.approvalStatus,
                    color: approver.status === 'approved' ? '#28a745' : 
                           approver.status === 'rejected' ? '#dc3545' : '#6c757d'
                  }}>
                    {approver.status.toUpperCase()}
                  </div>
                  {approver.comment && (
                    <div style={styles.approvalComment}>{approver.comment}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  const renderFiles = () => (
    <div style={styles.filesTab}>
      <CodeDiff
        files={pullRequest.diff.files}
        comments={pullRequest.comments}
        onAddComment={onAddComment}
      />
    </div>
  );

  const renderComments = () => (
    <div style={styles.commentsTab}>
      <h3>Comments ({pullRequest.comments.length})</h3>
      {pullRequest.comments.length === 0 ? (
        <p style={styles.noComments}>No comments yet.</p>
      ) : (
        <div style={styles.commentsList}>
          {pullRequest.comments.map((comment) => (
            <div key={comment.id} style={styles.comment}>
              <div style={styles.commentHeader}>
                <img
                  src={comment.author.avatar || '/default-avatar.png'}
                  alt={comment.author.name}
                  style={styles.commentAvatar}
                />
                <div style={styles.commentMeta}>
                  <strong>{comment.author.name}</strong>
                  <span style={styles.commentTime}>
                    {comment.createdAt.toLocaleDateString()}
                  </span>
                </div>
              </div>
              <div style={styles.commentContent}>
                {comment.content}
              </div>
              {comment.filePath && (
                <div style={styles.commentFile}>
                  On file: <code>{comment.filePath}</code>
                  {comment.lineNumber && ` at line ${comment.lineNumber}`}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button onClick={onBack} style={styles.backButton}>
          ← Back to List
        </button>
        
        <div style={styles.titleSection}>
          <h1 style={styles.title}>
            #{pullRequest.number} {pullRequest.title}
          </h1>
          <div
            style={{
              ...styles.statusBadge,
              backgroundColor: getStatusColor(pullRequest.status),
            }}
          >
            {getStatusIcon(pullRequest.status)} {pullRequest.status.toUpperCase()}
          </div>
        </div>
      </div>

      <div style={styles.tabs}>
        <button
          onClick={() => setActiveTab('overview')}
          style={{
            ...styles.tab,
            ...(activeTab === 'overview' ? styles.activeTab : {}),
          }}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('files')}
          style={{
            ...styles.tab,
            ...(activeTab === 'files' ? styles.activeTab : {}),
          }}
        >
          Files ({pullRequest.diff.files.length})
        </button>
        <button
          onClick={() => setActiveTab('comments')}
          style={{
            ...styles.tab,
            ...(activeTab === 'comments' ? styles.activeTab : {}),
          }}
        >
          Comments ({pullRequest.comments.length})
        </button>
      </div>

      <div style={styles.content}>
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'files' && renderFiles()}
        {activeTab === 'comments' && renderComments()}
      </div>

      {pullRequest.status === 'open' && (
        <ApprovalActions onSubmit={onApprovalSubmit} />
      )}
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
    marginBottom: '20px',
  },
  backButton: {
    padding: '8px 16px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: '#fff',
    cursor: 'pointer',
    fontSize: '14px',
    marginBottom: '16px',
  },
  titleSection: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    flexWrap: 'wrap' as const,
  },
  title: {
    margin: 0,
    fontSize: '24px',
    color: '#333',
    flex: 1,
  },
  statusBadge: {
    padding: '6px 12px',
    borderRadius: '16px',
    color: '#fff',
    fontSize: '12px',
    fontWeight: 'bold',
    whiteSpace: 'nowrap' as const,
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid #e1e5e9',
    marginBottom: '20px',
  },
  tab: {
    padding: '12px 16px',
    border: 'none',
    backgroundColor: 'transparent',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    color: '#666',
    borderBottom: '2px solid transparent',
  },
  activeTab: {
    color: '#0366d6',
    borderBottomColor: '#0366d6',
  },
  content: {
    minHeight: '400px',
  },
  overview: {
    display: 'grid',
    gridTemplateColumns: '2fr 1fr',
    gap: '20px',
  },
  description: {
    backgroundColor: '#f8f9fa',
    padding: '20px',
    borderRadius: '8px',
  },
  metadata: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '20px',
  },
  metaSection: {
    backgroundColor: '#fff',
    border: '1px solid #e1e5e9',
    borderRadius: '8px',
    padding: '16px',
  },
  metaItem: {
    marginBottom: '8px',
    fontSize: '14px',
  },
  reviewersList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  },
  reviewer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
  },
  reviewerAvatar: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    objectFit: 'cover' as const,
  },
  approvalsList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  },
  approval: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
  },
  approvalInfo: {
    flex: 1,
  },
  approverName: {
    fontSize: '14px',
    fontWeight: '600',
  },
  approvalStatus: {
    fontSize: '12px',
    fontWeight: '600',
    textTransform: 'uppercase' as const,
  },
  approvalComment: {
    fontSize: '12px',
    color: '#666',
    marginTop: '4px',
  },
  filesTab: {
    backgroundColor: '#fff',
  },
  commentsTab: {
    backgroundColor: '#fff',
  },
  noComments: {
    color: '#666',
    fontStyle: 'italic',
    textAlign: 'center' as const,
    padding: '40px',
  },
  commentsList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  },
  comment: {
    border: '1px solid #e1e5e9',
    borderRadius: '8px',
    padding: '16px',
    backgroundColor: '#f8f9fa',
  },
  commentHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px',
  },
  commentAvatar: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    objectFit: 'cover' as const,
  },
  commentMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
  },
  commentTime: {
    color: '#666',
    fontSize: '12px',
  },
  commentContent: {
    fontSize: '14px',
    lineHeight: '1.5',
    marginBottom: '8px',
  },
  commentFile: {
    fontSize: '12px',
    color: '#666',
    fontStyle: 'italic',
  },
};