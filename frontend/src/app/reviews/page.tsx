'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/layout/main-layout';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Search, GitPullRequest, Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

interface Review {
  id: string;
  title: string;
  repository: string;
  author: string;
  status: 'pending' | 'approved' | 'rejected' | 'in_progress';
  qualityScore: number;
  securityScore: number;
  createdAt: string;
  updatedAt: string;
  prNumber?: number;
}

const statusConfig = {
  pending: { label: 'Pending', icon: Clock, variant: 'secondary' as const },
  in_progress: { label: 'In Progress', icon: AlertCircle, variant: 'default' as const },
  approved: { label: 'Approved', icon: CheckCircle2, variant: 'default' as const },
  rejected: { label: 'Rejected', icon: XCircle, variant: 'destructive' as const },
};

export default function ReviewsPage() {
  const router = useRouter();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [repositoryFilter, setRepositoryFilter] = useState<string>('all');

  useEffect(() => {
    let cancelled = false;

    const loadReviews = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch('/api/reviews', {
          credentials: 'include',
          cache: 'no-store',
        });

        if (!response.ok) {
          const apiError = await response.json().catch(() => ({ detail: 'Failed to load pull requests' }));
          throw new Error(apiError.detail || 'Failed to load pull requests');
        }

        const data = await response.json();
        if (!cancelled) {
          setReviews(Array.isArray(data.reviews) ? data.reviews : []);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load pull requests');
          setReviews([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadReviews();

    return () => {
      cancelled = true;
    };
  }, []);

  const repositories = Array.from(new Set(reviews.map((review) => review.repository)));

  const filteredReviews = reviews.filter((review) => {
    const matchesSearch =
      review.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      review.repository.toLowerCase().includes(searchQuery.toLowerCase()) ||
      review.author.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || review.status === statusFilter;
    const matchesRepository = repositoryFilter === 'all' || review.repository === repositoryFilter;

    return matchesSearch && matchesStatus && matchesRepository;
  });

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader title="Pull Requests" description="Review and manage code reviews" />

        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-4 md:flex-row">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search by title, repository, or author..."
                      value={searchQuery}
                      onChange={(event) => setSearchQuery(event.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-full md:w-[180px]">
                    <SelectValue placeholder="Filter by status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="in_progress">In Progress</SelectItem>
                    <SelectItem value="approved">Approved</SelectItem>
                    <SelectItem value="rejected">Rejected</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={repositoryFilter} onValueChange={setRepositoryFilter}>
                  <SelectTrigger className="w-full md:w-[180px]">
                    <SelectValue placeholder="Filter by repository" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Repositories</SelectItem>
                    {repositories.map((repo) => (
                      <SelectItem key={repo} value={repo}>
                        {repo}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {(searchQuery || statusFilter !== 'all' || repositoryFilter !== 'all') && (
                <div className="text-sm text-muted-foreground">
                  Showing {filteredReviews.length} of {reviews.length} pull requests
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {isLoading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, index) => (
              <Card key={index}>
                <CardHeader>
                  <Skeleton className="mb-2 h-6 w-3/4" />
                  <Skeleton className="h-4 w-full" />
                </CardHeader>
              </Card>
            ))}
          </div>
        ) : error ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <AlertCircle className="mb-4 h-12 w-12 text-destructive" />
              <h3 className="mb-2 text-lg font-semibold">Unable to load pull requests</h3>
              <p className="text-sm text-muted-foreground">{error}</p>
            </CardContent>
          </Card>
        ) : filteredReviews.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <GitPullRequest className="mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="mb-2 text-lg font-semibold">No pull requests found</h3>
              <p className="text-sm text-muted-foreground">
                {searchQuery || statusFilter !== 'all' || repositoryFilter !== 'all'
                  ? 'Try adjusting your search or filters'
                  : 'No pull requests available'}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredReviews.map((review) => {
              const StatusIcon = statusConfig[review.status].icon;

              return (
                <Card
                  key={review.id}
                  className="cursor-pointer transition-shadow hover:shadow-lg"
                  onClick={() => router.push(`/reviews/${review.id}`)}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="mb-2 flex items-center gap-2">
                          <GitPullRequest className="h-5 w-5 text-muted-foreground" />
                          <CardTitle className="text-lg">{review.title}</CardTitle>
                        </div>
                        <CardDescription>
                          <div className="flex flex-wrap items-center gap-2 text-sm">
                            <span className="font-medium">{review.repository}</span>
                            <span>•</span>
                            <span>{review.author}</span>
                            {typeof review.prNumber === 'number' && (
                              <>
                                <span>•</span>
                                <span>PR #{review.prNumber}</span>
                              </>
                            )}
                            <span>•</span>
                            <time dateTime={review.createdAt}>
                              {new Date(review.createdAt).toLocaleDateString()}
                            </time>
                          </div>
                        </CardDescription>
                      </div>
                      <Badge variant={statusConfig[review.status].variant} className="flex items-center gap-1">
                        <StatusIcon className="h-3 w-3" />
                        {statusConfig[review.status].label}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex gap-6 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Quality:</span>
                        <span className={`font-semibold ${getScoreColor(review.qualityScore)}`}>
                          {review.qualityScore}%
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Security:</span>
                        <span className={`font-semibold ${getScoreColor(review.securityScore)}`}>
                          {review.securityScore}%
                        </span>
                      </div>
                      <div className="ml-auto flex items-center gap-2 text-muted-foreground">
                        <Clock className="h-4 w-4" />
                        <span>Updated {new Date(review.updatedAt).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
