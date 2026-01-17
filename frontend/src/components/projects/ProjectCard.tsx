'use client';

/**
 * Project Card Component
 */
import { GitBranch, CheckCircle, Clock, MoreVertical, RefreshCw, Settings, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import type { Project } from '@/hooks/useProjects';
import { useSyncProject, useDeleteProject } from '@/hooks/useProjects';

interface ProjectCardProps {
    project: Project;
}

export default function ProjectCard({ project }: ProjectCardProps) {
    const [showMenu, setShowMenu] = useState(false);
    const { mutate: syncProject, isPending: isSyncing } = useSyncProject();
    const { mutate: deleteProject } = useDeleteProject();

    const handleSync = () => {
        syncProject(project.id);
        setShowMenu(false);
    };

    const handleDelete = () => {
        if (confirm(`Are you sure you want to delete "${project.name}"?`)) {
            deleteProject(project.id);
        }
        setShowMenu(false);
    };

    return (
        <div className="relative rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm hover:shadow-md transition-shadow">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
                <div className="flex-1 min-w-0">
                    <Link
                        href={`/projects/${project.id}`}
                        className="text-lg font-semibold text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 truncate block"
                    >
                        {project.name}
                    </Link>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                        {project.description || 'No description'}
                    </p>
                </div>

                {/* Actions Menu */}
                <div className="relative ml-4">
                    <button
                        onClick={() => setShowMenu(!showMenu)}
                        className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                        <MoreVertical className="h-5 w-5" />
                    </button>

                    {showMenu && (
                        <>
                            <div
                                className="fixed inset-0 z-10"
                                onClick={() => setShowMenu(false)}
                            />
                            <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black ring-opacity-5 z-20">
                                <div className="py-1">
                                    <button
                                        onClick={handleSync}
                                        disabled={isSyncing}
                                        className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                                    >
                                        <RefreshCw className={`h-4 w-4 mr-3 ${isSyncing ? 'animate-spin' : ''}`} />
                                        Sync with GitHub
                                    </button>
                                    <Link
                                        href={`/projects/${project.id}/settings`}
                                        className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                                    >
                                        <Settings className="h-4 w-4 mr-3" />
                                        Settings
                                    </Link>
                                    <button
                                        onClick={handleDelete}
                                        className="flex items-center w-full px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                                    >
                                        <Trash2 className="h-4 w-4 mr-3" />
                                        Delete
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Repository Info */}
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 mb-4">
                <GitBranch className="h-4 w-4" />
                <a
                    href={project.github_repo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-primary-600 dark:hover:text-primary-400 truncate"
                >
                    {project.github_repo_url.replace('https://github.com/', '')}
                </a>
            </div>

            {/* Language Tag */}
            {project.language && (
                <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-800 dark:text-primary-300 mb-4">
                    {project.language}
                </div>
            )}

            {/* Status Indicators (Mock data - replace with actual metrics) */}
            <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-1.5 text-sm">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-gray-600 dark:text-gray-400">Healthy</span>
                </div>
                <div className="flex items-center gap-1.5 text-sm">
                    <Clock className="h-4 w-4 text-gray-400" />
                    <span className="text-gray-600 dark:text-gray-400">
                        {new Date(project.updated_at).toLocaleDateString()}
                    </span>
                </div>
            </div>
        </div>
    );
}
