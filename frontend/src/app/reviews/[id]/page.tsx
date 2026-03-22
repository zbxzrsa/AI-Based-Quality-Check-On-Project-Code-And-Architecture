'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import CodeDiffViewer from '@/components/reviews/code-diff-viewer';
import ReviewCommentCard, { ReviewComment } from '@/components/reviews/review-comment-card';
import CommentFiltersComponent, { CommentFilters } from '@/components/reviews/comment-filters';
import ComplianceStatus from '@/components/reviews/compliance-status';
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  FileCode,
  GitCommit,
  GitPullRequest,
  Info,
  RefreshCw,
  User,
  XCircle,
} from 'lucide-react';

type ReviewStatus = 'pending' | 'in_progress' | 'completed' | 'failed';
type CommentStatus = 'open' | 'resolved' | 'wont_fix';

interface ReviewApiResponse {
  review_id: string;
  status: ReviewStatus;
  started_at: string | null;
  completed_at: string | null;
  summary?: {
    total_issues?: number;
    severity_counts?: Record<string, number>;
  } | null;
  comments: Array<{
    id: string;
    file_path: string;
    line_number: number | null;
    message: string;
    severity: string;
    category: string | null;
    suggested_fix?: string | null;
    rule_id?: string | null;
    rule_name?: string | null;
  }>;
}

interface PullFilesApiResponse {
  pr_id: string;
  pr_number: number;
  files: Array<{
    filename: string;
    status: 'added' | 'modified' | 'deleted' | 'renamed';
    additions: number;
    deletions: number;
    changes: number;
    diff?: {
      lines?: Array<{
        line_number?: number | null;
        old_line_number?: number | null;
        new_line_number?: number | null;
        type?: 'add' | 'remove' | 'context' | 'header';
        content?: string;
      }>;
    };
  }>;
}

interface PullRequestReviewData {
  reviewId: string;
  prId: string;
  prNumber: number;
  status: ReviewStatus;
  startedAt: string | null;
  completedAt: string | null;
  summary: ReviewApiResponse['summary'];
  files: PullFilesApiResponse['files'];
  comments: ReviewComment[];
}

const normalizeSeverity = (severity: string | null | undefined): ReviewComment['severity'] => {
  switch ((severity || '').toLowerCase()) {
    case 'critical':
      return 'critical';
    case 'high':
      return 'high';
    case 'medium':
      return 'medium';
    default:
      return 'low';
  }
};

const getStatusBadgeVariant = (status: ReviewStatus) => {
  switch (status) {
    case 'completed':
      return 'default';
    case 'in_progress':
      return 'secondary';
    case 'failed':
      return 'destructive';
    default:
      return 'outline';
  }
};

const getStatusIcon = (status: ReviewStatus) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-600" />;
    case 'in_progress':
      return <RefreshCw className="h-4 w-4 text-blue-600" />;
    default:
      return <AlertCircle className="h-4 w-4 text-yellow-600" />;
  }
};

const formatReviewComments = (comments: ReviewApiResponse['comments']): ReviewComment[] =>
  comments.map((comment) => ({
    id: comment.id,
    severity: normalizeSeverity(comment.severity),
    category: comment.category || 'general',
    message: comment.message,
    filename: comment.file_path,
    lineNumber: comment.line_number || 1,
    suggestedFix: comment.suggested_fix || undefined,
    reasoning: comment.rule_name || comment.rule_id || undefined,
    status: 'open',
  }));

const toViewerFiles = (files: PullFilesApiResponse['files']) =>
  files.map((file) => ({
    filename: file.filename,
    status: file.status,
    additions: file.additions,
    deletions: file.deletions,
    lines: (file.diff?.lines || []).map((line, index) => ({
      lineNumber: line.new_line_number ?? line.old_line_number ?? index + 1,
      oldLineNumber: line.old_line_number ?? null,
      newLineNumber: line.new_line_number ?? null,
      type: line.type || 'context',
      content: line.content || '',
    })),
  }));

export default function PullRequestReviewPage() {
  const params = useParams();
  const router = useRouter();
  const prId = (params?.id as string) || '';

  const [reviewData, setReviewData] = useState<PullRequestReviewData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isQueueing, setIsQueueing] = useState(false);
  const [commentFilters, setCommentFilters] = useState<CommentFilters>({
    severity: [],
    category: [],
    status: [],
  });
  const [commentStatuses, setCommentStatuses] = useState<Record<string, CommentStatus>>({});

  useEffect(() => {
    let cancelled = false;

    const loadReview = async () => {
      if (!prId) {
        setError('Missing pull request identifier');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const [reviewResponse, filesResponse] = await Promise.all([
          fetch(`/api/github/pr/${prId}/review`, { credentials: 'include' }),
          fetch(`/api/github/pulls/${prId}/files`, { credentials: 'include' }),
        ]);

        if (!filesResponse.ok) {
          const filesError = await filesResponse.json().catch(() => ({ detail: 'Failed to load pull request files' }));
          throw new Error(filesError.detail || 'Failed to load pull request files');
        }
        const files = (await filesResponse.json()) as PullFilesApiResponse;

        let review: ReviewApiResponse | null = null;
        if (reviewResponse.ok) {
          review = (await reviewResponse.json()) as ReviewApiResponse;
        } else if (reviewResponse.status !== 404) {
          const reviewError = await reviewResponse.json().catch(() => ({ detail: 'Failed to load review' }));
          throw new Error(reviewError.detail || 'Failed to load review');
        }

        if (cancelled) {
          return;
        }

        setReviewData({
          reviewId: review?.review_id || `pending-${prId}`,
          prId,
          prNumber: files.pr_number,
          status: review?.status || 'pending',
          startedAt: review?.started_at || null,
          completedAt: review?.completed_at || null,
          summary: review?.summary || {
            total_issues: 0,
            severity_counts: {},
          },
          files: files.files,
          comments: formatReviewComments(review?.comments || []),
        });
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load review details');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadReview();

    return () => {
      cancelled = true;
    };
  }, [prId]);

  const comments = useMemo(() => {
    if (!reviewData) {
      return [];
    }

    return reviewData.comments.map((comment) => ({
      ...comment,
      status: commentStatuses[comment.id] || comment.status,
    }));
  }, [commentStatuses, reviewData]);

  const filteredComments = useMemo(() => {
    return comments.filter((comment) => {
      if (commentFilters.severity.length > 0 && !commentFilters.severity.includes(comment.severity)) {
        return false;
      }

      if (commentFilters.category.length > 0 && !commentFilters.category.includes(comment.category)) {
        return false;
      }

      if (commentFilters.status.length > 0 && !commentFilters.status.includes(comment.status)) {
        return false;
      }

      return true;
    });
  }, [commentFilters, comments]);

  const availableCategories = useMemo(
    () => Array.from(new Set(comments.map((comment) => comment.category))).sort(),
    [comments]
  );

  const severityCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };

    comments.forEach((comment) => {
      counts[comment.severity] += 1;
    });

    return counts;
  }, [comments]);

  const complianceData = useMemo(() => {
    const violations = comments
      .filter((comment) => comment.severity === 'critical' || comment.severity === 'high')
      .slice(0, 5)
      .map((comment) => ({
        id: comment.id,
        rule: comment.category,
        description: comment.message,
        severity: comment.severity,
        affectedFiles: [comment.filename],
      }));

    const issueCount = comments.length;
    const highSeverityCount = severityCounts.critical + severityCounts.high;

    return {
      iso25010: {
        name: 'ISO/IEC 25010',
        status: highSeverityCount > 0 ? 'warning' as const : 'passed' as const,
        score: Math.max(0, 100 - issueCount * 5),
        violations,
      },
      iso23396: {
        name: 'ISO/IEC 23396',
        status: severityCounts.critical > 0 ? 'failed' as const : highSeverityCount > 0 ? 'warning' as const : 'passed' as const,
        score: Math.max(0, 100 - highSeverityCount * 10 - severityCounts.medium * 4),
        violations,
      },
    };
  }, [comments, severityCounts]);

  const viewerFiles = useMemo(() => toViewerFiles(reviewData?.files || []), [reviewData?.files]);

  const updateCommentStatus = (commentId: string, status: CommentStatus) => {
    setCommentStatuses((current) => ({ ...current, [commentId]: status }));
  };

  const queueAnalysis = async () => {
    if (!prId || isQueueing) {
      return;
    }

    setIsQueueing(true);
    setError(null);

    try {
      const response = await fetch(`/api/github/pr/${prId}/analyze`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        const analysisError = await response.json().catch(() => ({ detail: 'Failed to queue analysis' }));
        throw new Error(analysisError.detail || 'Failed to queue analysis');
      }

      setReviewData((current) =>
        current
          ? {
              ...current,
              status: 'in_progress',
              startedAt: current.startedAt || new Date().toISOString(),
            }
          : current
      );
    } catch (queueError) {
      setError(queueError instanceof Error ? queueError.message : 'Failed to queue analysis');
    } finally {
      setIsQueueing(false);
    }
  };

  if (isLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <Skeleton className="h-10 w-1/2" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </MainLayout>
    );
  }

  if (error || !reviewData) {
    return (
      <MainLayout>
        <Card>
          <CardHeader>
            <CardTitle>Unable to load review</CardTitle>
            <CardDescription>{error || 'This pull request does not have a review yet.'}</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button variant="outline" onClick={() => router.back()}>
              Back
            </Button>
            <Button onClick={() => window.location.reload()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-muted-foreground">
              <GitPullRequest className="h-4 w-4" />
              <span>Pull Request Review</span>
            </div>
            <h1 className="text-3xl font-semibold">PR #{reviewData.prNumber}</h1>
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                {getStatusIcon(reviewData.status)}
                Review {reviewData.status.replace('_', ' ')}
              </span>
              {reviewData.startedAt && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  Started {new Date(reviewData.startedAt).toLocaleString()}
                </span>
              )}
              {reviewData.completedAt && (
                <span className="flex items-center gap-1">
                  <CheckCircle2 className="h-4 w-4" />
                  Completed {new Date(reviewData.completedAt).toLocaleString()}
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge variant={getStatusBadgeVariant(reviewData.status)}>
              {reviewData.status.replace('_', ' ')}
            </Badge>
            <Badge variant="outline">Review ID {reviewData.reviewId}</Badge>
            {(reviewData.status === 'pending' || reviewData.status === 'failed') && (
              <Button onClick={queueAnalysis} disabled={isQueueing}>
                {isQueueing ? 'Queueing analysis...' : 'Analyze Now'}
              </Button>
            )}
            <Button variant="outline" onClick={() => router.back()}>
              Back
            </Button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Total Findings</CardDescription>
              <CardTitle>{comments.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Files Changed</CardDescription>
              <CardTitle>{viewerFiles.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>High Severity</CardDescription>
              <CardTitle>{severityCounts.critical + severityCounts.high}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Medium and Low</CardDescription>
              <CardTitle>{severityCounts.medium + severityCounts.low}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        <Tabs defaultValue="comments" className="space-y-4">
          <TabsList>
            <TabsTrigger value="comments">Findings</TabsTrigger>
            <TabsTrigger value="changes">Code Changes</TabsTrigger>
            <TabsTrigger value="compliance">Compliance</TabsTrigger>
            <TabsTrigger value="summary">Summary</TabsTrigger>
          </TabsList>

          <TabsContent value="comments" className="space-y-4">
            <CommentFiltersComponent
              filters={commentFilters}
              onFiltersChange={setCommentFilters}
              availableCategories={availableCategories}
            />

            {filteredComments.length === 0 ? (
              <Card>
                <CardContent className="flex items-center justify-center py-12 text-muted-foreground">
                  No findings match the current filters.
                </CardContent>
              </Card>
            ) : (
              filteredComments.map((comment) => (
                <ReviewCommentCard
                  key={comment.id}
                  comment={comment}
                  onResolve={() => updateCommentStatus(comment.id, 'resolved')}
                  onWontFix={() => updateCommentStatus(comment.id, 'wont_fix')}
                />
              ))
            )}
          </TabsContent>

          <TabsContent value="changes">
            <Card>
              <CardHeader>
                <CardTitle>Changed Files</CardTitle>
                <CardDescription>Unified and split diff views for the reviewed pull request</CardDescription>
              </CardHeader>
              <CardContent>
                {viewerFiles.length > 0 ? (
                  <CodeDiffViewer files={viewerFiles} />
                ) : (
                  <div className="flex items-center justify-center py-12 text-muted-foreground">
                    <FileCode className="mr-2 h-4 w-4" />
                    No diff data available for this pull request.
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="compliance">
            <ComplianceStatus
              iso25010={complianceData.iso25010}
              iso23396={complianceData.iso23396}
            />
          </TabsContent>

          <TabsContent value="summary">
            <Card>
              <CardHeader>
                <CardTitle>Review Summary</CardTitle>
                <CardDescription>Overview of the automated review results</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-lg border p-4">
                    <div className="mb-2 flex items-center gap-2 font-medium">
                      <Info className="h-4 w-4 text-blue-600" />
                      Severity breakdown
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span>Critical</span>
                        <span>{severityCounts.critical}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>High</span>
                        <span>{severityCounts.high}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Medium</span>
                        <span>{severityCounts.medium}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Low</span>
                        <span>{severityCounts.low}</span>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-lg border p-4">
                    <div className="mb-2 flex items-center gap-2 font-medium">
                      <GitCommit className="h-4 w-4 text-purple-600" />
                      Review metadata
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span>Review status</span>
                        <span>{reviewData.status}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Tracked files</span>
                        <span>{viewerFiles.length}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Total issues</span>
                        <span>{reviewData.summary?.total_issues ?? comments.length}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>PR identifier</span>
                        <span>{reviewData.prId}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border p-4 text-sm text-muted-foreground">
                  <div className="mb-2 flex items-center gap-2 font-medium text-foreground">
                    <User className="h-4 w-4" />
                    What this page shows
                  </div>
                  It is now backed by the live pull request review and changed-file APIs, so the findings, severities,
                  and diff viewer all reflect the latest stored review data instead of placeholder content.
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
}
