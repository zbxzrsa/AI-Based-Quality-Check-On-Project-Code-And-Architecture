'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/layout/main-layout';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Search, Filter, GitPullRequest, Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

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
}

const mockReviews: Review[] = [
  {
    id: '1',
    title: 'Add user authentication feature',
    repository: 'frontend-app',
    author: 'john.doe',
    status: 'approved',
    qualityScore: 92,
    securityScore: 95,
    createdAt: '2024-01-15T10:30:00Z',
    updatedAt: '2024-01-15T14:20:00Z',
  },
  {
    id: '2',
    title: 'Fix database connection pooling',
    repository: 'backend-api',
    author: 'jane.smith',
    status: 'in_progress',
    qualityScore: 85,
    securityScore: 88,
    createdAt: '2024-01-16T09:15:00Z',
    updatedAt: '2024-01-16T11:45:00Z',
  },
  {
    id: '3',
    title: 'Update dependencies to latest versions',
    repository: 'frontend-app',
    author: 'bob.wilson',
    status: 'pending',
    qualityScore: 78,
    securityScore: 82,
    createdAt: '2024-01-17T08:00:00Z',
    updatedAt: '2024-01-17T08:00:00Z',
  },
];

const statusConfig = {
  pending: { label: 'Pending', icon: Clock, variant: 'secondary' as const, color: 'text-yellow-600' },
  in_progress: { label: 'In Progress', icon: AlertCircle, variant: 'default' as const, color: 'text-blue-600' },
  approved: { label: 'Approved', icon: CheckCircle2, variant: 'default' as const, color: 'text-green-600' },
  rejected: { label: 'Rejected', icon: XCircle, variant: 'destructive' as const, color: 'text-red-600' },
};

export default function ReviewsPage() {
  const router = useRouter();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    // Simulate API call
    const timer = setTimeout(() => {
      setReviews(mockReviews);
      setIsLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  const filteredReviews = reviews.filter((review) => {
    const matchesSearch =
      review.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      review.repository.toLowerCase().includes(searchQuery.toLowerCase()) ||
      review.author.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'all' || review.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 75) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Code Reviews"
          description="View and manage all code reviews across your projects"
        />

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search reviews..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-[200px]">
                  <Filter className="h-4 w-4 mr-2" />
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
            </div>
          </CardContent>
        </Card>

        {/* Reviews List */}
        <div className="space-y-4">
          {isLoading ? (
            <>
              {[1, 2, 3].map((i) => (
                <Card key={i}>
                  <CardHeader>
                    <Skeleton className="h-6 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-2/3" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </>
          ) : filteredReviews.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <GitPullRequest className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No reviews found</h3>
                <p className="text-muted-foreground">
                  {searchQuery || statusFilter !== 'all'
                    ? 'Try adjusting your filters'
                    : 'No code reviews available yet'}
                </p>
              </CardContent>
            </Card>
          ) : (
            filteredReviews.map((review) => {
              const StatusIcon = statusConfig[review.status].icon;
              return (
                <Card
                  key={review.id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => router.push(`/reviews/${review.id}`)}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="space-y-1 flex-1">
                        <CardTitle className="text-xl">{review.title}</CardTitle>
                        <CardDescription>
                          {review.repository} • by {review.author}
                        </CardDescription>
                      </div>
                      <Badge variant={statusConfig[review.status].variant}>
                        <StatusIcon className="h-3 w-3 mr-1" />
                        {statusConfig[review.status].label}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-6">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Quality Score:</span>
                        <span className={`text-sm font-semibold ${getScoreColor(review.qualityScore)}`}>
                          {review.qualityScore}%
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Security Score:</span>
                        <span className={`text-sm font-semibold ${getScoreColor(review.securityScore)}`}>
                          {review.securityScore}%
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
                          Updated {new Date(review.updatedAt).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      </div>
    </MainLayout>
  );
}
