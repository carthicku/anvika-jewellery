import { useQuery } from '@tanstack/react-query';

import { api, unwrap } from '../client';
import { queryKeys } from '../queryKeys';

/** Backend liveness, shown as a small development-only status indicator. */
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => unwrap(api.GET('/api/v1/health')),
    staleTime: 30_000,
    retry: false,
  });
}
