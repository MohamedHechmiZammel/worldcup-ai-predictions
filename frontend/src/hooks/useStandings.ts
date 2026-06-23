import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export function useStandings() {
  return useQuery({
    queryKey: ['standings'],
    queryFn: api.getStandings,
    staleTime: 55_000,       // refresh just before the 60s backend cache expires
    refetchInterval: 60_000,
    retry: 1,
  });
}
