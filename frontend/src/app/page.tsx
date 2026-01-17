'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser, useIsAuthenticated } from '../hooks/useAuth';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Shield, Code, GitPullRequest, Users, TrendingUp, Database, Cpu, Lock } from 'lucide-react';

export default function Home() {
    const router = useRouter();
    const { isLoading } = useUser();
    const { isAuthenticated } = useIsAuthenticated();
    const [stats, setStats] = useState({
        totalReviews: 0,
        projects: 0,
        complianceScore: 0,
        securityIssues: 0
    });

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/auth/signin');
        } else if (isAuthenticated) {
            fetchStats();
        }
    }, [isAuthenticated, isLoading, router]);

    const fetchStats = async () => {
        try {
            const response = await fetch('/api/v1/dashboard/stats');
            if (response.ok) {
                const data = await response.json();
                setStats(data);
            }
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
    };

    const features = [
        {
            title: 'AI-Powered Code Review',
            description: 'Automated pull request analysis with AI-driven insights and suggestions',
            icon: <Cpu className="h-8 w-8" />,
            color: 'text-blue-600',
            href: '/dashboard'
        },
        {
            title: 'Architecture Analysis',
            description: 'Graph-based dependency analysis and architectural drift detection',
            icon: <Database className="h-8 w-8" />,
            color: 'text-green-600',
            href: '/analysis'
        },
        {
            title: 'Security Compliance',
            description: 'Automated security scanning and compliance monitoring',
            icon: <Shield className="h-8 w-8" />,
            color: 'text-red-600',
            href: '/security'
        },
        {
            title: 'Project Management',
            description: 'Centralized project dashboard with quality metrics and insights',
            icon: <Users className="h-8 w-8" />,
            color: 'text-purple-600',
            href: '/projects'
        }
    ];

    const statsData = [
        {
            label: 'Total Reviews',
            value: stats.totalReviews.toLocaleString(),
            icon: <Code className="h-6 w-6" />
        },
        {
            label: 'Active Projects',
            value: stats.projects.toString(),
            icon: <GitPullRequest className="h-6 w-6" />
        },
        {
            label: 'Compliance Score',
            value: `${stats.complianceScore}%`,
            icon: <TrendingUp className="h-6 w-6" />
        },
        {
            label: 'Security Issues',
            value: stats.securityIssues.toString(),
            icon: <Lock className="h-6 w-6" />
        }
    ];

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading...</p>
                </div>
            </div>
        );
    }

    return (
        <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
            {/* Hero Section */}
            <section className="relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 opacity-10"></div>
                <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
                    <div className="text-center">
                        <h1 className="text-4xl md:text-6xl font-bold text-slate-900 dark:text-white mb-6">
                            AI-Based Quality Check on Project Code and Architecture
                        </h1>
                        <p className="text-lg md:text-xl text-slate-600 dark:text-slate-300 mb-8 max-w-3xl mx-auto">
                            Revolutionize your code review process with AI-powered analysis, 
                            architectural insights, and automated compliance monitoring. 
                            Built for modern development teams seeking excellence.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Button 
                                onClick={() => router.push('/dashboard')}
                                className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold"
                            >
                                Get Started
                            </Button>
                            <Button 
                                onClick={() => router.push('/projects')}
                                variant="outline"
                                className="border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 px-8 py-3 rounded-lg font-semibold"
                            >
                                View Projects
                            </Button>
                        </div>
                    </div>
                </div>
            </section>

            {/* Stats Section */}
            <section className="py-16 bg-white dark:bg-slate-800/50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                        {statsData.map((stat, index) => (
                            <Card key={index} className="text-center p-6">
                                <div className="flex items-center justify-center w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-full mx-auto mb-4">
                                    <div className="text-blue-600 dark:text-blue-400">
                                        {stat.icon}
                                    </div>
                                </div>
                                <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                                    {stat.value}
                                </h3>
                                <p className="text-slate-600 dark:text-slate-300">
                                    {stat.label}
                                </p>
                            </Card>
                        ))}
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-16">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-4">
                            Powerful Features for Modern Development
                        </h2>
                        <p className="text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto">
                            Our platform combines cutting-edge AI technology with proven software engineering practices
                            to deliver unparalleled code quality and architectural insights.
                        </p>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                        {features.map((feature, index) => (
                            <Card 
                                key={index} 
                                className="p-6 hover:shadow-lg transition-shadow duration-300 cursor-pointer"
                                onClick={() => router.push(feature.href)}
                            >
                                <div className="flex items-center mb-4">
                                    <div className={`p-3 rounded-full bg-blue-50 dark:bg-blue-900/20 ${feature.color}`}>
                                        {feature.icon}
                                    </div>
                                    <div className="ml-4">
                                        <h3 className="text-xl font-semibold text-slate-900 dark:text-white">
                                            {feature.title}
                                        </h3>
                                    </div>
                                </div>
                                <p className="text-slate-600 dark:text-slate-300 mb-4">
                                    {feature.description}
                                </p>
                                <div className="flex items-center justify-between">
                                    <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
                                        AI-Powered
                                    </Badge>
                                    <span className="text-blue-600 dark:text-blue-400 font-medium">
                                        Learn more →
                                    </span>
                                </div>
                            </Card>
                        ))}
                    </div>
                </div>
            </section>

            {/* Technology Stack */}
            <section className="py-16 bg-slate-50 dark:bg-slate-800/50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-4">
                            Built with Modern Technology
                        </h2>
                        <p className="text-slate-600 dark:text-slate-300">
                            Our platform leverages the latest technologies to ensure performance, scalability, and reliability.
                        </p>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                        {['Next.js', 'FastAPI', 'Neo4j', 'Redis', 'PostgreSQL', 'Tailwind CSS', 'React', 'Python'].map((tech, index) => (
                            <div key={index} className="bg-white dark:bg-slate-700 p-6 rounded-lg shadow-sm">
                                <span className="text-lg font-semibold text-slate-900 dark:text-white">
                                    {tech}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-16">
                <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
                    <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-6">
                        Ready to Transform Your Code Review Process?
                    </h2>
                    <p className="text-lg text-slate-600 dark:text-slate-300 mb-8">
                        Join hundreds of development teams who have already improved their code quality 
                        and architectural standards with our AI-powered platform.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Button 
                            onClick={() => router.push('/auth/signin')}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold"
                        >
                            Start Free Trial
                        </Button>
                        <Button 
                            onClick={() => router.push('/docs')}
                            variant="outline"
                            className="border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 px-8 py-3 rounded-lg font-semibold"
                        >
                            View Documentation
                        </Button>
                    </div>
                </div>
            </section>
        </main>
    );
}
