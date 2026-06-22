import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import type { Match } from '../types';

const STAGE_ORDER = [
  'Group A', 'Group B', 'Group C', 'Group D',
  'Group E', 'Group F', 'Group G', 'Group H',
  'Group I', 'Group J', 'Group K', 'Group L',
  'Round of 32', 'Round of 16', 'Quarter-finals',
  'Semi-finals', 'Third place', 'Final',
];

export function useMatches(params?: { status?: string; stage?: string }) {
  const query = useQuery({
    queryKey: ['matches', params],
    queryFn: () => api.getMatches(params),
    refetchInterval: 30_000,  // poll every 30 seconds
    staleTime: 10_000,
  });

  // Group matches by stage in priority order
  const matchesByStage = groupByStage(query.data?.matches ?? []);

  return {
    ...query,
    matchesByStage,
  };
}

function groupByStage(matches: Match[]): Map<string, Match[]> {
  const groups = new Map<string, Match[]>();

  // Sort matches by stage priority then scheduled_at
  const sorted = [...matches].sort((a, b) => {
    const stageA = STAGE_ORDER.indexOf(a.stage);
    const stageB = STAGE_ORDER.indexOf(b.stage);
    if (stageA !== stageB) return stageA - stageB;
    return new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime();
  });

  for (const match of sorted) {
    if (!groups.has(match.stage)) groups.set(match.stage, []);
    groups.get(match.stage)!.push(match);
  }

  return groups;
}
