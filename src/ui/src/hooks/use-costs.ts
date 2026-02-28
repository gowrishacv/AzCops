import { useQuery } from '@tanstack/react-query';
import { costsApi } from '@/lib/api';

export function useCostSummary(days = 30) {
  return useQuery({
    queryKey: ['costs', 'summary', days],
    queryFn: () => costsApi.summary(days),
  });
}
