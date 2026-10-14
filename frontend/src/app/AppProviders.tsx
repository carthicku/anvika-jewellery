import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';

import { ApiError } from '@/api/client';
import { ToastProvider } from '@/components/ui/Toaster';

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // Retry network blips, but not client errors (404, 422, 403…), which won't fix themselves.
        retry: (failureCount, error) =>
          failureCount < 2 &&
          (!(error instanceof ApiError) || error.status === 0 || error.status >= 500),
      },
      mutations: { retry: false },
    },
  });
}

export function AppProviders({ children, client }: { children: ReactNode; client?: QueryClient }) {
  const [queryClient] = useState(() => client ?? createQueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
}
