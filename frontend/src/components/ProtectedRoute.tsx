'use client';

/**
 * Protected Route Wrapper Component
 */
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useIsAuthenticated } from '@/hooks/useAuth';

interface ProtectedRouteProps {
    children: React.ReactNode;
    requiredRole?: string;
}

export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
    const router = useRouter();
    const { isAuthenticated, isLoading, user } = useIsAuthenticated();

    useEffect(() => {
        if (!isLoading && isAuthenticated && requiredRole && user?.role !== requiredRole) {
            router.push('/unauthorized');
        }
    }, [isLoading, isAuthenticated, user, requiredRole, router]);

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            </div>
        );
    }

    if (requiredRole && user?.role !== requiredRole) {
        return null;
    }

    return <>{children}</>;
}
