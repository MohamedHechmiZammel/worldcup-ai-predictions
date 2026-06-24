import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import type { MatchStatus } from '../types';

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

export function useMatchStats(matchId: number, status: MatchStatus | undefined) {
  return useQuery({
    queryKey: ['matchStats', matchId],
    queryFn: () => api.getMatchStats(matchId),
    // No stats to fetch before kick-off
    enabled: status !== undefined && status !== 'scheduled',
    // Live: refetch every 30 s as fallback (WebSocket is primary); finished: cache 5 min
    staleTime: status === 'finished' ? 5 * 60_000 : 30_000,
    refetchInterval: status === 'live' || status === 'halftime' ? 30_000 : false,
    retry: 1,
  });
}
