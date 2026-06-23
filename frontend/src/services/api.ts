import type {
  Match,
  MatchListResponse,
  Prediction,
  PredictionHistoryResponse,
  AccuracyResponse,
  StandingsResponse,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    if (response.status === 404) throw new Error(`Not found: ${path}`);
    if (response.status === 503) throw new Error('Service unavailable');
    throw new Error(`API error ${response.status}: ${path}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getMatches: (params?: { status?: string; stage?: string }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.stage) query.set('stage', params.stage);
    const qs = query.toString();
    return apiFetch<MatchListResponse>(`/api/v1/matches${qs ? `?${qs}` : ''}`);
  },
  getMatch: (id: number) => apiFetch<Match>(`/api/v1/matches/${id}`),
  getLatestPrediction: (matchId: number) => apiFetch<Prediction>(`/api/v1/predictions/${matchId}/latest`),
  getPredictionHistory: (matchId: number) => apiFetch<PredictionHistoryResponse>(`/api/v1/predictions/${matchId}/history`),
  getAccuracy: () => apiFetch<AccuracyResponse>('/api/v1/accuracy'),
  getStandings: () => apiFetch<StandingsResponse>('/api/v1/standings'),
  health: () => apiFetch<{ status: string; environment: string }>('/health'),
};
