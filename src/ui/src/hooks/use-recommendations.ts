import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recommendationsApi } from '@/lib/api';

export function useRecommendations(
  params?: Parameters<typeof recommendationsApi.list>[0]
) {
  return useQuery({
    queryKey: ['recommendations', params],
    queryFn: () => recommendationsApi.list(params),
  });
}

export function useApproveRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: recommendationsApi.approve,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recommendations'] }),
  });
}

export function useRejectRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      recommendationsApi.reject(id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recommendations'] }),
  });
}

export function useDismissRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: recommendationsApi.dismiss,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recommendations'] }),
  });
}
