'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import CodeDiffViewer from '@/components/reviews/code-diff-viewer';
import ReviewCommentCard, { ReviewComment } from '@/components/reviews/review-comment-card';
import CommentFiltersComponent, { CommentFilters } from '@/components/reviews/comment-filters';
import ComplianceStatus from '@/components/reviews/compliance-status';
import { apiGet } from '@/lib/api-client';
import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  FileCode,
  GitCommit,
  Loader2,
  ShieldCheck,
} from 'lucide-react';

interface ReviewApiComment {
  id: string;
  file_path: string;
  line_number: number | null;
  message: string;
  severity: string;
  category: string | null;
  suggested_fix: string | null;
  rule_id: string | null;
  rule_name: string | null;
}

interface ReviewApiResponse {
  review_id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  summary?: {
    total_issues?: number;
    message?: string;
    severity_counts?: Record<string, number>;
  } | null;
  comments: ReviewApiComment[];
}

interface ParsedDiffChange {
  type: 'addition' | 'deletion' | 'context';
  line: string;
  line_number?: number;
}

interface ParsedDiffHunk {
  old_start: number;
  new_start: number;
  changes: ParsedDiffChange[];
}

interface ParsedDiff {
  old_path: string;
  new_path: string;
  hunks: ParsedDiffHunk[];
}

interface PullRequestFile {
  filename: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  changes?: number;
  diff?: ParsedDiff;
}

interface PullRequestFilesResponse {
  pr_id: string;
  pr_number: number;
  files: PullRequestFile[];
}

interface DiffLine {
  lineNumber: number | null;
  oldLineNumber: number | null;
  newLineNumber: number | null;
  type: 'add' | 'remove' | 'context' | 'header';
  content: string;
}

interface DiffFile {
  filename: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  lines: DiffLine[];
}

const formatDate = (value?: string | null) => {
  if (!value) {
    return 'Not available';
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not available' : date.toLocaleString();
};

const normalizeSeverity = (severity?: string | null): ReviewComment['severity'] => {
  switch ((severity || '').toLowerCase()) {
    case 'critical':
      return 'critical';
    case 'high':
      return 'high';
    case 'medium':
      return 'medium';
    case 'low':
    case 'info':
    default:
      return 'low';
  }
};

const normalizeCategory = (category?: string | null) => {
  return category ? category : 'general';
};

const statusVariant = (status?: string | null) => {
  switch ((status || '').toLowerCase()) {
    case 'completed':
    case 'reviewed':
    case 'approved':
      return 'success' as const;
    case 'analyzing':
    case 'in_progress':
    case 'pending':
      return 'warning' as const;
    case 'failed':
    case 'rejected':
      return 'destructive' as const;
    default:
      return 'outline' as const;
  }
};

const toSentenceCase = (value?: string | null) => {
  if (!value) {
    return 'Unknown';
  }
  return value.replace(/[_-]/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
};

const toDiffLines = (file: PullRequestFile): DiffLine[] => {
  if (!file.diff?.hunks?.length) {
    return [
      {
        lineNumber: null,
        oldLineNumber: null,
        newLineNumber: null,
        type: 'context',
        content: 'Diff details are not available for this file.',
      },
    ];
  }

  const lines: DiffLine[] = [];

  file.diff.hunks.forEach((hunk) => {
    lines.push({
      lineNumber: null,
      oldLineNumber: null,
      newLineNumber: null,
      type: 'header',
      content: `@@ -${hunk.old_start} +${hunk.new_start} @@`,
    });

    let oldLine = hunk.old_start;
    let newLine = hunk.new_start;

    hunk.changes.forEach((change) => {
      if (change.type === 'addition') {
        lines.push({
          lineNumber: change.line_number ?? newLine,
          oldLineNumber: null,
          newLineNumber: change.line_number ?? newLine,
          type: 'add',
          content: change.line,
        });
        newLine += 1;
        return;
      }

      if (change.type === 'deletion') {
        lines.push({
          lineNumber: change.line_number ?? oldLine,
          oldLineNumber: change.line_number ?? oldLine,
          newLineNumber: null,
          type: 'remove',
          content: change.line,
        });
        oldLine += 1;
        return;
      }

      lines.push({
        lineNumber: newLine,
        oldLineNumber: oldLine,
        newLineNumber: newLine,
        type: 'context',
        content: change.line,
      });
      oldLine += 1;
      newLine += 1;
    });
  });

  return lines;
};

const buildComplianceStandard = (
  name: string,
  comments: ReviewComment[]
) => {
  const critical = comments.filter((comment) => comment.severity === 'critical').length;
  const high = comments.filter((comment) => comment.severity === 'high').length;
  const medium = comments.filter((comment) => comment.severity === 'medium').length;
  const score = Math.max(0, 100 - critical * 25 - high * 12 - medium * 6 - Math.max(0, comments.length - critical - high - medium) * 3);
  const status = critical > 0 ? 'failed' : high > 0 || medium > 2 ? 'warning' : 'passed';

  return {
    name,
    status: status as 'passed' | 'warning' | 'failed',
    score,
    violations: comments.slice(0, 8).map((comment) => ({
      id: comment.id,
      rule: comment.message,
      description: comment.suggestedFix || 'No suggested fix was returned for this finding.',
      severity: comment.severity,
      affectedFiles: [comment.filename],
    })),
  };
};

export default function PullRequestReviewPage() {
  const params = useParams();
  const prId = typeof params?.id === 'string' ? params.id : '';
  const reviewEndpoint = prId ? `/api/github/pulls/${prId}/review/` : '';
  const filesEndpoint = prId ? `/api/github/pulls/${prId}/files/` : '';
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<ReviewApiResponse | null>(null);
  const [fileResponse, setFileResponse] = useState<PullRequestFilesResponse | null>(null);
  const [commentFilters, setCommentFilters] = useState<CommentFilters>({
    severity: [],
    category: [],
    status: [],
  });
  const [commentStatuses, setCommentStatuses] = useState<Record<string, ReviewComment['status']>>({});

  useEffect(() => {
    if (!prId) {
      setError('Pull request ID is missing.');
      setIsLoading(false);
      return;
    }

    let active = true;

    const loadReview = async (silent = false) => {
      if (!silent) {
        setIsLoading(true);
      }
      setError(null);

      const [reviewResult, filesResult] = await Promise.allSettled([
        apiGet<ReviewApiResponse>(reviewEndpoint),
        apiGet<PullRequestFilesResponse>(filesEndpoint),
      ]);

      if (!active) {
        return;
      }

      if (reviewResult.status === 'fulfilled') {
        setReview(reviewResult.value);
      } else {
        setReview(null);
      }

      if (filesResult.status === 'fulfilled') {
        setFileResponse(filesResult.value);
      } else {
        setFileResponse(null);
      }

      if (reviewResult.status === 'rejected' && filesResult.status === 'rejected') {
        setError(reviewResult.reason instanceof Error ? reviewResult.reason.message : 'Unable to load pull request review details.');
      }

      setIsLoading(false);
    };

    void loadReview();
    const intervalId = window.setInterval(() => {
      void loadReview(true);
    }, 5000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, [filesEndpoint, prId, reviewEndpoint]);

  const comments = useMemo<ReviewComment[]>(() => {
    return (review?.comments || []).map((comment) => ({
      id: comment.id,
      severity: normalizeSeverity(comment.severity),
      category: normalizeCategory(comment.category),
      message: comment.message,
      filename: comment.file_path,
      lineNumber: comment.line_number ?? 0,
      suggestedFix: comment.suggested_fix || undefined,
      reasoning: comment.rule_name || comment.rule_id || undefined,
      status: commentStatuses[comment.id] || 'open',
    }));
  }, [commentStatuses, review?.comments]);

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

  const availableCategories = useMemo(() => {
    return Array.from(new Set(comments.map((comment) => comment.category))).sort();
  }, [comments]);

  const diffFiles = useMemo<DiffFile[]>(() => {
    return (fileResponse?.files || []).map((file) => ({
      filename: file.filename,
      status: file.status,
      additions: file.additions,
      deletions: file.deletions,
      lines: toDiffLines(file),
    }));
  }, [fileResponse?.files]);

  const totalAdditions = useMemo(() => {
    return (fileResponse?.files || []).reduce((total, file) => total + file.additions, 0);
  }, [fileResponse?.files]);

  const totalDeletions = useMemo(() => {
    return (fileResponse?.files || []).reduce((total, file) => total + file.deletions, 0);
  }, [fileResponse?.files]);

  const severityCounts = useMemo(() => {
    return {
      critical: comments.filter((comment) => comment.severity === 'critical').length,
      high: comments.filter((comment) => comment.severity === 'high').length,
      medium: comments.filter((comment) => comment.severity === 'medium').length,
      low: comments.filter((comment) => comment.severity === 'low').length,
    };
  }, [comments]);

  const architectureComments = useMemo(() => {
    return comments.filter((comment) => {
      const category = comment.category.toLowerCase();
      return category.includes('architecture') || category.includes('maintainability') || category.includes('performance') || category.includes('best-practices');
    });
  }, [comments]);

  const iso25010 = useMemo(() => buildComplianceStandard('ISO/IEC 25010', comments), [comments]);
  const iso23396 = useMemo(() => buildComplianceStandard('ISO/IEC 23396', architectureComments), [architectureComments]);

  const summaryMessage = review?.summary?.message || 'This review shows the latest automated findings for the selected pull request.';

  const updateCommentStatus = (commentId: string, status: ReviewComment['status']) => {
    setCommentStatuses((current) => ({
      ...current,
      [commentId]: status,
    }));
  };

  if (isLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <Skeleton className="h-10 w-72" />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((item) => (
              <Skeleton key={item} className="h-28" />
            ))}
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </MainLayout>
    );
  }

  if (error) {
    return (
      <MainLayout>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <AlertCircle className="h-12 w-12 text-destructive" />
            <div>
              <h1 className="text-xl font-semibold">Unable to load this review</h1>
              <p className="mt-2 text-sm text-muted-foreground">{error}</p>
            </div>
            <Button asChild variant="outline">
              <Link href="/reviews">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Pull Requests
              </Link>
            </Button>
          </CardContent>
        </Card>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Pull Request Review"
          description={`Review ID: ${review?.review_id || 'Not available'} | Pull request #${fileResponse?.pr_number ?? 'N/A'} | PR ID: ${prId}`}
          actions={
            <>
              <Badge variant={statusVariant(review?.status)}>{toSentenceCase(review?.status)}</Badge>
              <Button asChild variant="outline">
                <Link href="/reviews">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Pull Requests
                </Link>
              </Button>
            </>
          }
        />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Findings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{comments.length}</div>
              <p className="text-xs text-muted-foreground">Total issues returned by the latest review.</p>
            </CardContent>
          </Card>
          <Card className="border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Files changed</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{diffFiles.length}</div>
              <p className="text-xs text-muted-foreground">Files with diff data available for inspection.</p>
            </CardContent>
          </Card>
          <Card className="border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Lines changed</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">+{totalAdditions} / -{totalDeletions}</div>
              <p className="text-xs text-muted-foreground">Combined additions and deletions across the pull request.</p>
            </CardContent>
          </Card>
          <Card className="border-white/70 bg-white/80 dark:border-white/10 dark:bg-slate-950/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Critical + high</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{severityCounts.critical + severityCounts.high}</div>
              <p className="text-xs text-muted-foreground">Priority findings that need attention first.</p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="flex h-auto flex-wrap justify-start gap-2 bg-transparent p-0">
            <TabsTrigger value="overview" className="border">Overview</TabsTrigger>
            <TabsTrigger value="comments" className="border">Issues</TabsTrigger>
            <TabsTrigger value="diff" className="border">Code Diff</TabsTrigger>
            <TabsTrigger value="compliance" className="border">Compliance</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-[1.2fr,0.8fr]">
              <Card>
                <CardHeader>
                  <CardTitle>Review summary</CardTitle>
                  <CardDescription>Latest automated review status and execution timestamps.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">{summaryMessage}</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-lg border p-4">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Clock className="h-4 w-4" />
                        Started
                      </div>
                      <p className="mt-2 font-medium">{formatDate(review?.started_at)}</p>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="h-4 w-4" />
                        Completed
                      </div>
                      <p className="mt-2 font-medium">{formatDate(review?.completed_at)}</p>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <ShieldCheck className="h-4 w-4" />
                        Review status
                      </div>
                      <div className="mt-2">
                        <Badge variant={statusVariant(review?.status)}>{toSentenceCase(review?.status)}</Badge>
                      </div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <GitCommit className="h-4 w-4" />
                        Pull request number
                      </div>
                      <p className="mt-2 font-medium">#{fileResponse?.pr_number ?? 'N/A'}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Severity breakdown</CardTitle>
                  <CardDescription>Latest issue distribution from the stored review result.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {Object.entries(severityCounts).map(([severity, count]) => (
                    <div key={severity} className="flex items-center justify-between rounded-lg border p-3">
                      <span>{toSentenceCase(severity)}</span>
                      <span className="font-semibold">{count}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="comments" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Issue filters</CardTitle>
                <CardDescription>Filter findings by severity, category, and status.</CardDescription>
              </CardHeader>
              <CardContent>
                <CommentFiltersComponent
                  filters={commentFilters}
                  onFiltersChange={setCommentFilters}
                  availableCategories={availableCategories}
                />
              </CardContent>
            </Card>

            {filteredComments.length > 0 ? (
              <div className="space-y-4">
                {filteredComments.map((comment) => (
                  <ReviewCommentCard
                    key={comment.id}
                    comment={comment}
                    onResolve={() => updateCommentStatus(comment.id, 'resolved')}
                    onWontFix={() => updateCommentStatus(comment.id, 'wont_fix')}
                  />
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="py-10 text-center text-sm text-muted-foreground">
                  No review comments match the current filters.
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="diff" className="space-y-4">
            {diffFiles.length > 0 ? (
              <CodeDiffViewer files={diffFiles} />
            ) : review?.status === 'analyzing' ? (
              <Card>
                <CardContent className="flex items-center justify-center gap-3 py-10 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Diff data will appear after GitHub file sync completes.
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="flex flex-col items-center justify-center gap-3 py-10 text-center text-sm text-muted-foreground">
                  <FileCode className="h-8 w-8" />
                  No diff files are available for this pull request yet.
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="compliance" className="space-y-4">
            <ComplianceStatus iso25010={iso25010} iso23396={iso23396} />
            {comments.length === 0 && (
              <Card>
                <CardContent className="flex items-center gap-3 py-6 text-sm text-muted-foreground">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  No findings are currently stored for this review, so the compliance summary is based on a clean result.
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
}

