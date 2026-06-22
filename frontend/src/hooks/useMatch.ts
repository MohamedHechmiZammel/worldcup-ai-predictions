import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export function useMatch(matchId: number) {
  return useQuery({
    queryKey: ['match', matchId],
    queryFn: () => api.getMatch(matchId),
    staleTime: 5_000,
  });
}

export function usePredictionHistory(matchId: number) {
  return useQuery({
    queryKey: ['predictionHistory', matchId],
    queryFn: () => api.getPredictionHistory(matchId),
    staleTime: 30_000,
  });
}
