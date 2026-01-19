'use client';

import MainLayout from '@/components/layout/main-layout';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  User,
  Mail,
  Calendar,
  GitPullRequest,
  CheckCircle2,
  AlertCircle,
  Settings,
} from 'lucide-react';

export default function ProfilePage() {
  // Mock user data
  const user = {
    name: 'John Doe',
    email: 'john.doe@example.com',
    role: 'Developer',
    joinedDate: '2026-01-01',
    avatar: null,
  };

  const stats = {
    totalReviews: 45,
    approvedPRs: 38,
    pendingReviews: 7,
    criticalIssuesFound: 12,
  };

  const recentActivity = [
    {
      id: '1',
      type: 'review',
      title: 'Reviewed PR #123',
      project: 'AI Code Review Platform',
      date: '2026-01-19',
      status: 'approved',
    },
    {
      id: '2',
      type: 'issue',
      title: 'Found critical security issue',
      project: 'E-commerce API',
      date: '2026-01-18',
      status: 'critical',
    },
    {
      id: '3',
      type: 'review',
      title: 'Reviewed PR #456',
      project: 'Analytics Dashboard',
      date: '2026-01-17',
      status: 'changes_requested',
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Profile Header */}
        <Card className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-6">
              <Avatar className="h-24 w-24">
                <div className="h-full w-full rounded-full bg-primary flex items-center justify-center text-primary-foreground text-3xl font-bold">
                  {user.name
                    .split(' ')
                    .map((n) => n[0])
                    .join('')}
                </div>
              </Avatar>
              <div>
                <h1 className="text-3xl font-bold">{user.name}</h1>
                <div className="flex items-center gap-4 mt-2 text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4" />
                    <span>{user.email}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    <span>Joined {new Date(user.joinedDate).toLocaleDateString()}</span>
                  </div>
                </div>
                <Badge className="mt-2">{user.role}</Badge>
              </div>
            </div>
            <Button variant="outline" asChild>
              <a href="/settings">
                <Settings className="h-4 w-4 mr-2" />
                Edit Profile
              </a>
            </Button>
          </div>
        </Card>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Reviews</p>
                <p className="text-3xl font-bold mt-2">{stats.totalReviews}</p>
              </div>
              <GitPullRequest className="h-8 w-8 text-blue-500" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Approved PRs</p>
                <p className="text-3xl font-bold mt-2">{stats.approvedPRs}</p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pending Reviews</p>
                <p className="text-3xl font-bold mt-2">{stats.pendingReviews}</p>
              </div>
              <AlertCircle className="h-8 w-8 text-yellow-500" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Critical Issues</p>
                <p className="text-3xl font-bold mt-2">{stats.criticalIssuesFound}</p>
              </div>
              <AlertCircle className="h-8 w-8 text-red-500" />
            </div>
          </Card>
        </div>

        {/* Activity Tabs */}
        <Tabs defaultValue="activity" className="w-full">
          <TabsList>
            <TabsTrigger value="activity">Recent Activity</TabsTrigger>
            <TabsTrigger value="projects">Projects</TabsTrigger>
            <TabsTrigger value="achievements">Achievements</TabsTrigger>
          </TabsList>

          <TabsContent value="activity" className="space-y-4">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
              <div className="space-y-4">
                {recentActivity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center justify-between p-4 rounded-lg border"
                  >
                    <div className="flex-1">
                      <h4 className="font-medium">{activity.title}</h4>
                      <p className="text-sm text-muted-foreground">
                        {activity.project}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-muted-foreground">
                        {new Date(activity.date).toLocaleDateString()}
                      </span>
                      <Badge
                        className={
                          activity.status === 'approved'
                            ? 'bg-green-500'
                            : activity.status === 'critical'
                            ? 'bg-red-500'
                            : 'bg-yellow-500'
                        }
                      >
                        {activity.status.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="projects">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Your Projects</h3>
              <p className="text-muted-foreground">
                Projects you're contributing to will appear here.
              </p>
            </Card>
          </TabsContent>

          <TabsContent value="achievements">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Achievements</h3>
              <p className="text-muted-foreground">
                Your achievements and badges will appear here.
              </p>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
}
