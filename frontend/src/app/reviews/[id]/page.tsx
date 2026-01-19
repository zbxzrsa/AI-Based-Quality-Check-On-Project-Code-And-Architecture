'use client';

import { useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import CodeDiffViewer from '@/components/reviews/code-diff-viewer';
import ReviewCommentCard, {
  ReviewComment,
} from '@/components/reviews/review-comment-card';
import CommentFiltersComponent, {
  CommentFilters,
} from '@/components/reviews/comment-filters';
import ComplianceStatus from '@/components/reviews/compliance-status';
import {
  GitPullRequest,
  ExternalLink,
  FileCode,
  GitCommit,
  User,
  Calendar,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
} from 'lucide-react';

export default function PullRequestReviewPage() {
  const params = useParams();
  const [isLoading, setIsLoading] = useState(false);
  const [commentFilters, setCommentFilters] = useState<CommentFilters>({
    severity: [],
    category: [],
    status: [],
  });

  // Mock data - replace with actual API call
  const prData = {
    id: params.id,
    number: 123,
    title: 'Add user authentication with JWT tokens',
    status: 'in_review',
    author: 'john.doe',
    createdAt: '2026-01-15T10:30:00Z',
    githubUrl: 'https://github.com/example/repo/pull/123',
    filesChanged: 12,
    additions: 245,
    deletions: 89,
    reviewers: ['jane.smith', 'bob.wilson'],
    labels: ['feature', 'security'],
    overallScore: 85,
    issuesBySeverity: {
      critical: 1,
      high: 3,
      medium: 8,
      low: 12,
    },
    complianceStatus: {
      iso25010: 'passed',
      iso23396: 'warning',
    },
  };

  // Mock diff data
  const mockDiffFiles = [
    {
      filename: 'src/auth/jwt.ts',
      status: 'added' as const,
      additions: 85,
      deletions: 0,
      lines: [
        {
          lineNumber: 1,
          oldLineNumber: null,
          newLineNumber: 1,
          type: 'add' as const,
          content: "import jwt from 'jsonwebtoken';",
        },
        {
          lineNumber: 2,
          oldLineNumber: null,
          newLineNumber: 2,
          type: 'add' as const,
          content: "import { User } from '../types';",
        },
        {
          lineNumber: 3,
          oldLineNumber: null,
          newLineNumber: 3,
          type: 'add' as const,
          content: '',
        },
        {
          lineNumber: 4,
          oldLineNumber: null,
          newLineNumber: 4,
          type: 'add' as const,
          content: 'export function generateToken(user: User): string {',
        },
        {
          lineNumber: 5,
          oldLineNumber: null,
          newLineNumber: 5,
          type: 'add' as const,
          content: '  return jwt.sign({ id: user.id, email: user.email }, process.env.JWT_SECRET);',
        },
        {
          lineNumber: 6,
          oldLineNumber: null,
          newLineNumber: 6,
          type: 'add' as const,
          content: '}',
        },
      ],
    },
    {
      filename: 'src/middleware/auth.ts',
      status: 'modified' as const,
      additions: 15,
      deletions: 8,
      lines: [
        {
          lineNumber: 1,
          oldLineNumber: 1,
          newLineNumber: 1,
          type: 'context' as const,
          content: "import { Request, Response, NextFunction } from 'express';",
        },
        {
          lineNumber: 2,
          oldLineNumber: 2,
          newLineNumber: null,
          type: 'remove' as const,
          content: "import { verifySession } from './session';",
        },
        {
          lineNumber: 3,
          oldLineNumber: null,
          newLineNumber: 2,
          type: 'add' as const,
          content: "import { verifyToken } from '../auth/jwt';",
        },
        {
          lineNumber: 4,
          oldLineNumber: 3,
          newLineNumber: 3,
          type: 'context' as const,
          content: '',
        },
        {
          lineNumber: 5,
          oldLineNumber: 4,
          newLineNumber: 4,
          type: 'context' as const,
          content: 'export async function authenticate(req: Request, res: Response, next: NextFunction) {',
        },
        {
          lineNumber: 6,
          oldLineNumber: 5,
          newLineNumber: null,
          type: 'remove' as const,
          content: '  const session = await verifySession(req.cookies.session);',
        },
        {
          lineNumber: 7,
          oldLineNumber: null,
          newLineNumber: 5,
          type: 'add' as const,
          content: '  const token = req.headers.authorization?.split(" ")[1];',
        },
        {
          lineNumber: 8,
          oldLineNumber: null,
          newLineNumber: 6,
          type: 'add' as const,
          content: '  if (!token) return res.status(401).json({ error: "No token provided" });',
        },
        {
          lineNumber: 9,
          oldLineNumber: null,
          newLineNumber: 7,
          type: 'add' as const,
          content: '  const user = await verifyToken(token);',
        },
      ],
    },
    {
      filename: 'src/routes/auth.ts',
      status: 'modified' as const,
      additions: 45,
      deletions: 12,
      lines: [
        {
          lineNumber: 1,
          oldLineNumber: 1,
          newLineNumber: 1,
          type: 'context' as const,
          content: "import express from 'express';",
        },
        {
          lineNumber: 2,
          oldLineNumber: 2,
          newLineNumber: 2,
          type: 'context' as const,
          content: "import { login, register } from '../controllers/auth';",
        },
        {
          lineNumber: 3,
          oldLineNumber: null,
          newLineNumber: 3,
          type: 'add' as const,
          content: "import { authenticate } from '../middleware/auth';",
        },
      ],
    },
  ];

  // Mock review comments
  const mockComments: ReviewComment[] = [
    {
      id: '1',
      severity: 'critical',
      category: 'security',
      message: 'JWT secret should not be hardcoded or exposed in environment variables without proper encryption',
      filename: 'src/auth/jwt.ts',
      lineNumber: 5,
      codeSnippet: "  return jwt.sign({ id: user.id, email: user.email }, process.env.JWT_SECRET);",
      suggestedFix: "  const secret = await getEncryptedSecret('JWT_SECRET');\n  return jwt.sign({ id: user.id, email: user.email }, secret, { expiresIn: '1h' });",
      reasoning: 'Storing JWT secrets in plain environment variables is a security risk. Use a secure secret management service like AWS Secrets Manager or HashiCorp Vault. Additionally, tokens should have an expiration time to limit the impact of token theft.',
      status: 'open',
    },
    {
      id: '2',
      severity: 'high',
      category: 'security',
      message: 'Missing token expiration validation',
      filename: 'src/middleware/auth.ts',
      lineNumber: 7,
      codeSnippet: '  const user = await verifyToken(token);',
      suggestedFix: '  try {\n    const user = await verifyToken(token);\n    if (!user || user.exp < Date.now() / 1000) {\n      return res.status(401).json({ error: "Token expired" });\n    }\n  } catch (error) {\n    return res.status(401).json({ error: "Invalid token" });\n  }',
      reasoning: 'The current implementation does not check if the token has expired. This could allow attackers to use old tokens indefinitely. Always validate token expiration and handle verification errors properly.',
      status: 'open',
    },
    {
      id: '3',
      severity: 'medium',
      category: 'best-practices',
      message: 'Consider using async/await consistently',
      filename: 'src/routes/auth.ts',
      lineNumber: 3,
      codeSnippet: "import { authenticate } from '../middleware/auth';",
      reasoning: 'The codebase uses a mix of promises and async/await. For consistency and better error handling, consider using async/await throughout the authentication flow.',
      status: 'open',
    },
    {
      id: '4',
      severity: 'low',
      category: 'documentation',
      message: 'Missing JSDoc comments for public functions',
      filename: 'src/auth/jwt.ts',
      lineNumber: 4,
      codeSnippet: 'export function generateToken(user: User): string {',
      suggestedFix: '/**\n * Generates a JWT token for the authenticated user\n * @param user - The user object containing id and email\n * @returns A signed JWT token string\n */\nexport function generateToken(user: User): string {',
      reasoning: 'Public API functions should have JSDoc comments to improve code maintainability and provide better IDE support.',
      status: 'open',
    },
  ];

  // Filter comments based on active filters
  const filteredComments = useMemo(() => {
    return mockComments.filter((comment) => {
      // Severity filter
      if (
        commentFilters.severity.length > 0 &&
        !commentFilters.severity.includes(comment.severity)
      ) {
        return false;
      }

      // Category filter
      if (
        commentFilters.category.length > 0 &&
        !commentFilters.category.includes(comment.category)
      ) {
        return false;
      }

      // Status filter
      if (
        commentFilters.status.length > 0 &&
        !commentFilters.status.includes(comment.status)
      ) {
        return false;
      }

      return true;
    });
  }, [commentFilters]);

  // Get unique categories from comments
  const availableCategories = useMemo(() => {
    return Array.from(new Set(mockComments.map((c) => c.category)));
  }, []);

  // Mock compliance data
  const complianceData = {
    iso25010: {
      name: 'ISO/IEC 25010',
      status: 'passed' as const,
      score: 92,
      violations: [],
    },
    iso23396: {
      name: 'ISO/IEC 23396',
      status: 'warning' as const,
      score: 78,
      violations: [
        {
          id: 'v1',
          rule: 'Layered Architecture',
          description:
            'Business logic detected in presentation layer. Maintain clear separation of concerns.',
          severity: 'medium' as const,
          affectedFiles: ['src/components/UserProfile.tsx'],
        },
        {
          id: 'v2',
          rule: 'Dependency Direction',
          description:
            'Data layer component depends on presentation layer. Dependencies should flow inward.',
          severity: 'high' as const,
          affectedFiles: ['src/database/UserRepository.ts'],
        },
      ],
    },
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-500';
      case 'in_review':
        return 'bg-yellow-500';
      case 'changes_requested':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'approved':
        return 'Approved';
      case 'in_review':
        return 'In Review';
      case 'changes_requested':
        return 'Changes Requested';
      default:
        return 'Pending';
    }
  };

  if (isLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header Section */}
        <Card className="p-6">
          <div className="space-y-4">
            {/* Title and Status */}
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <GitPullRequest className="h-6 w-6 text-muted-foreground" />
                  <h1 className="text-2xl font-bold">
                    {prData.title}
                    <span className="text-muted-foreground ml-2">
                      #{prData.number}
                    </span>
                  </h1>
                </div>
                <Badge className={getStatusColor(prData.status)}>
                  {getStatusLabel(prData.status)}
                </Badge>
              </div>
              <Button variant="outline" size="sm" asChild>
                <a
                  href={prData.githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  View on GitHub
                </a>
              </Button>
            </div>

            {/* Metadata */}
            <div className="flex flex-wrap gap-6 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4" />
                <span>
                  <span className="font-medium text-foreground">
                    {prData.author}
                  </span>{' '}
                  opened this pull request
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                <span>
                  {new Date(prData.createdAt).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <FileCode className="h-4 w-4" />
                <span>
                  {prData.filesChanged} files changed
                </span>
              </div>
              <div className="flex items-center gap-2">
                <GitCommit className="h-4 w-4" />
                <span className="text-green-600">
                  +{prData.additions}
                </span>
                <span className="text-red-600">
                  -{prData.deletions}
                </span>
              </div>
            </div>

            {/* Reviewers and Labels */}
            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Reviewers:</span>
                <div className="flex gap-2">
                  {prData.reviewers.map((reviewer) => (
                    <Badge key={reviewer} variant="secondary">
                      {reviewer}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Labels:</span>
                <div className="flex gap-2">
                  {prData.labels.map((label) => (
                    <Badge key={label} variant="outline">
                      {label}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Main Content Area with Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-3 space-y-6">
            <Tabs defaultValue="review" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="review">AI Review</TabsTrigger>
                <TabsTrigger value="diff">Code Changes</TabsTrigger>
                <TabsTrigger value="compliance">Compliance</TabsTrigger>
              </TabsList>

              <TabsContent value="review" className="space-y-4">
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                  {/* Filters Sidebar */}
                  <div className="lg:col-span-1">
                    <Card className="p-4 sticky top-4">
                      <CommentFiltersComponent
                        filters={commentFilters}
                        onFiltersChange={setCommentFilters}
                        availableCategories={availableCategories}
                      />
                    </Card>
                  </div>

                  {/* Comments List */}
                  <div className="lg:col-span-3 space-y-4">
                    {filteredComments.length === 0 ? (
                      <Card className="p-6">
                        <p className="text-center text-muted-foreground">
                          No comments match the selected filters.
                        </p>
                      </Card>
                    ) : (
                      filteredComments.map((comment) => (
                        <ReviewCommentCard
                          key={comment.id}
                          comment={comment}
                          onResolve={() => {
                            console.log('Resolve comment:', comment.id);
                          }}
                          onWontFix={() => {
                            console.log("Won't fix comment:", comment.id);
                          }}
                          onAskAI={() => {
                            console.log('Ask AI about comment:', comment.id);
                          }}
                        />
                      ))
                    )}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="diff" className="space-y-4">
                <CodeDiffViewer
                  files={mockDiffFiles}
                  onLineClick={(filename, lineNumber) => {
                    console.log(`Clicked line ${lineNumber} in ${filename}`);
                  }}
                />
              </TabsContent>

              <TabsContent value="compliance" className="space-y-4">
                <ComplianceStatus
                  iso25010={complianceData.iso25010}
                  iso23396={complianceData.iso23396}
                />
              </TabsContent>
            </Tabs>
          </div>

          {/* Summary Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Overall Score */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Overall Score</h3>
              <div className="flex items-center justify-center">
                <div className="relative w-32 h-32">
                  <svg className="w-full h-full" viewBox="0 0 100 100">
                    <circle
                      className="text-muted stroke-current"
                      strokeWidth="10"
                      cx="50"
                      cy="50"
                      r="40"
                      fill="transparent"
                    />
                    <circle
                      className="text-primary stroke-current"
                      strokeWidth="10"
                      strokeLinecap="round"
                      cx="50"
                      cy="50"
                      r="40"
                      fill="transparent"
                      strokeDasharray={`${prData.overallScore * 2.51} 251`}
                      transform="rotate(-90 50 50)"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-3xl font-bold">
                      {prData.overallScore}
                    </span>
                  </div>
                </div>
              </div>
              <p className="text-center text-sm text-muted-foreground mt-4">
                Code Quality Score
              </p>
            </Card>

            {/* Issues by Severity */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Issues by Severity</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <XCircle className="h-4 w-4 text-red-500" />
                    <span className="text-sm">Critical</span>
                  </div>
                  <Badge variant="destructive">
                    {prData.issuesBySeverity.critical}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-orange-500" />
                    <span className="text-sm">High</span>
                  </div>
                  <Badge className="bg-orange-500">
                    {prData.issuesBySeverity.high}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-yellow-500" />
                    <span className="text-sm">Medium</span>
                  </div>
                  <Badge className="bg-yellow-500">
                    {prData.issuesBySeverity.medium}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Info className="h-4 w-4 text-blue-500" />
                    <span className="text-sm">Low</span>
                  </div>
                  <Badge className="bg-blue-500">
                    {prData.issuesBySeverity.low}
                  </Badge>
                </div>
              </div>
            </Card>

            {/* Compliance Status */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Compliance Status</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm">ISO/IEC 25010</span>
                  <Badge
                    className={
                      prData.complianceStatus.iso25010 === 'passed'
                        ? 'bg-green-500'
                        : 'bg-yellow-500'
                    }
                  >
                    {prData.complianceStatus.iso25010 === 'passed' ? (
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                    ) : (
                      <AlertCircle className="h-3 w-3 mr-1" />
                    )}
                    {prData.complianceStatus.iso25010}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">ISO/IEC 23396</span>
                  <Badge
                    className={
                      prData.complianceStatus.iso23396 === 'passed'
                        ? 'bg-green-500'
                        : 'bg-yellow-500'
                    }
                  >
                    {prData.complianceStatus.iso23396 === 'passed' ? (
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                    ) : (
                      <AlertCircle className="h-3 w-3 mr-1" />
                    )}
                    {prData.complianceStatus.iso23396}
                  </Badge>
                </div>
              </div>
            </Card>

            {/* Action Buttons */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Actions</h3>
              <div className="space-y-2">
                <Button className="w-full" variant="default">
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Approve PR
                </Button>
                <Button className="w-full" variant="destructive">
                  <XCircle className="h-4 w-4 mr-2" />
                  Request Changes
                </Button>
                <Button className="w-full" variant="outline">
                  <AlertCircle className="h-4 w-4 mr-2" />
                  Add Comment
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
