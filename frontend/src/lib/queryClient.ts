import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
            gcTime: 10 * 60 * 1000, // 10 minutes
            retry: (failureCount, error) => {
                // Don't retry on 401 or 403 errors
                const axiosError = error as any;
                if (axiosError?.response?.status === 401 || axiosError?.response?.status === 403) {
                    return false;
                }
                return failureCount < 3;
            },
        },
    },
});
