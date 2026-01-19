'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import MainLayout from '@/components/layout/main-layout';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Search,
  FileCode,
  GitPullRequest,
  AlertCircle,
  FolderGit2,
} from 'lucide-react';
import Link from 'next/link';

interface SearchResult {
  id: string;
  type: 'project' | 'pr' | 'issue';
  title: string;
  description: string;
  metadata: {
    projectName?: string;
    status?: string;
    severity?: string;
    date?: string;
  };
  link: string;
}

export default function SearchPage() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [isSearching, setIsSearching] = useState(false);
  const [activeTab, setActiveTab] = useState('all');

  // Mock search results
  const mockResults: SearchResult[] = [
    {
      id: '1',
      type: 'project',
      title: 'AI Code Review Platform',
      description: 'Automated code review and architecture analysis platform',
      metadata: {
        status: 'active',
        date: '2026-01-15',
      },
      link: '/projects/1',
    },
    {
      id: '2',
      type: 'pr',
      title: 'Add user authentication with JWT tokens',
      description: 'Implements JWT-based authentication system',
      metadata: {
        projectName: 'AI Code Review Platform',
        status: 'in_review',
        date: '2026-01-19',
      },
      link: '/reviews/123',
    },
    {
      id: '3',
      type: 'issue',
      title: 'JWT secret should not be hardcoded',
      description: 'Security vulnerability in authentication module',
      metadata: {
        projectName: 'AI Code Review Platform',
        severity: 'critical',
        date: '2026-01-19',
      },
      link: '/reviews/123',
    },
    {
      id: '4',
      type: 'project',
      title: 'E-commerce API',
      description: 'RESTful API for e-commerce platform',
      metadata: {
        status: 'active',
        date: '2026-01-10',
      },
      link: '/projects/2',
    },
    {
      id: '5',
      type: 'pr',
      title: 'Implement payment gateway integration',
      description: 'Adds Stripe payment processing',
      metadata: {
        projectName: 'E-commerce API',
        status: 'approved',
        date: '2026-01-18',
      },
      link: '/reviews/456',
    },
  ];

  const filteredResults = mockResults.filter((result) => {
    const matchesQuery =
      result.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      result.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTab = activeTab === 'all' || result.type === activeTab;
    return matchesQuery && matchesTab;
  });

  const resultCounts = {
    all: mockResults.filter((r) =>
      r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.description.toLowerCase().includes(searchQuery.toLowerCase())
    ).length,
    project: mockResults.filter(
      (r) =>
        r.type === 'project' &&
        (r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          r.description.toLowerCase().includes(searchQuery.toLowerCase()))
    ).length,
    pr: mockResults.filter(
      (r) =>
        r.type === 'pr' &&
        (r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          r.description.toLowerCase().includes(searchQuery.toLowerCase()))
    ).length,
    issue: mockResults.filter(
      (r) =>
        r.type === 'issue' &&
        (r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          r.description.toLowerCase().includes(searchQuery.toLowerCase()))
    ).length,
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'project':
        return <FolderGit2 className="h-5 w-5 text-blue-500" />;
      case 'pr':
        return <GitPullRequest className="h-5 w-5 text-purple-500" />;
      case 'issue':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <FileCode className="h-5 w-5" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-500';
      case 'in_review':
        return 'bg-yellow-500';
      case 'approved':
        return 'bg-green-500';
      case 'critical':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  useEffect(() => {
    if (searchQuery) {
      setIsSearching(true);
      // Simulate API call
      const timer = setTimeout(() => {
        setIsSearching(false);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [searchQuery]);

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Search className="h-8 w-8" />
            Search Results
          </h1>
          <p className="text-muted-foreground mt-1">
            Search across projects, pull requests, and issues
          </p>
        </div>

        {/* Search Bar */}
        <Card className="p-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="Search projects, PRs, issues..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 text-lg h-12"
              autoFocus
            />
          </div>
        </Card>

        {/* Results */}
        {searchQuery ? (
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="all">
                All ({resultCounts.all})
              </TabsTrigger>
              <TabsTrigger value="project">
                Projects ({resultCounts.project})
              </TabsTrigger>
              <TabsTrigger value="pr">
                Pull Requests ({resultCounts.pr})
              </TabsTrigger>
              <TabsTrigger value="issue">
                Issues ({resultCounts.issue})
              </TabsTrigger>
            </TabsList>

            <TabsContent value={activeTab} className="space-y-4 mt-6">
              {isSearching ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <Card key={i} className="p-6">
                      <Skeleton className="h-6 w-3/4 mb-2" />
                      <Skeleton className="h-4 w-full" />
                    </Card>
                  ))}
                </div>
              ) : filteredResults.length > 0 ? (
                <div className="space-y-4">
                  {filteredResults.map((result) => (
                    <Link key={result.id} href={result.link}>
                      <Card className="p-6 hover:shadow-md transition-shadow cursor-pointer">
                        <div className="flex items-start gap-4">
                          <div className="flex-shrink-0 mt-1">
                            {getIcon(result.type)}
                          </div>
                          <div className="flex-1 space-y-2">
                            <div className="flex items-start justify-between gap-4">
                              <h3 className="text-lg font-semibold">
                                {result.title}
                              </h3>
                              <Badge
                                variant="outline"
                                className="capitalize flex-shrink-0"
                              >
                                {result.type}
                              </Badge>
                            </div>
                            <p className="text-muted-foreground">
                              {result.description}
                            </p>
                            <div className="flex flex-wrap gap-2 text-sm">
                              {result.metadata.projectName && (
                                <Badge variant="secondary">
                                  {result.metadata.projectName}
                                </Badge>
                              )}
                              {result.metadata.status && (
                                <Badge
                                  className={getStatusColor(
                                    result.metadata.status
                                  )}
                                >
                                  {result.metadata.status.replace('_', ' ')}
                                </Badge>
                              )}
                              {result.metadata.severity && (
                                <Badge
                                  className={getStatusColor(
                                    result.metadata.severity
                                  )}
                                >
                                  {result.metadata.severity}
                                </Badge>
                              )}
                              {result.metadata.date && (
                                <span className="text-muted-foreground">
                                  {new Date(
                                    result.metadata.date
                                  ).toLocaleDateString()}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </Card>
                    </Link>
                  ))}
                </div>
              ) : (
                <Card className="p-12">
                  <div className="text-center">
                    <Search className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">
                      No results found
                    </h3>
                    <p className="text-muted-foreground">
                      Try adjusting your search query or filters
                    </p>
                  </div>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        ) : (
          <Card className="p-12">
            <div className="text-center">
              <Search className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">
                Start searching
              </h3>
              <p className="text-muted-foreground">
                Enter a search query to find projects, pull requests, and issues
              </p>
            </div>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
