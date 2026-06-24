export interface Team {
  id: number;
  name: string;
  country_code: string;
  fifa_ranking: number | null;
  group_letter: string | null;
  avg_goals_scored: number | null;
  avg_goals_conceded: number | null;
  form_points: number | null;
}

export type MatchStatus = 'scheduled' | 'live' | 'halftime' | 'finished' | 'postponed' | 'cancelled';

export interface Factor {
  feature: string;
  impact_pct: number;
  label: string;
}

export interface Prediction {
  id: number;
  match_id: number;
  prediction_type: 'prematch' | 'live';
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  expected_home_goals: number;
  expected_away_goals: number;
  confidence_low: number;
  confidence_high: number;
  top_factors: Factor[];
  created_at: string;  // ISO datetime string
}

export interface AccuracyInfo {
  was_correct: boolean;
  predicted_outcome: string;
  actual_outcome: string;
}

export interface Match {
  id: number;
  external_id: string | null;
  home_team_id: number;
  away_team_id: number;
  home_team: Team | null;
  away_team: Team | null;
  scheduled_at: string;  // ISO datetime string
  venue: string | null;
  city: string | null;
  stage: string;
  status: MatchStatus;
  home_score: number | null;
  away_score: number | null;
  prediction?: Prediction | null;
  accuracy?: AccuracyInfo | null;
}

export interface MatchListResponse {
  matches: Match[];
  total: number;
  live_count: number;
}

export interface PredictionHistoryResponse {
  match_id: number;
  predictions: Prediction[];
}

export interface AccuracyResponse {
  total_predictions: number;
  correct_predictions: number;
  accuracy_pct: number;
  by_stage: Record<string, number>;
}

export interface TeamStanding {
  team: Team;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
  points: number;
  projected?: boolean; // true when at least one match is AI-projected
}

// ESPN live standings (from /api/v1/standings)
export interface LiveStandingEntry {
  team_abbr: string;
  team_name: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  points: number;
  note: string;
  note_color: string;
}

export interface StandingsResponse {
  groups: Record<string, LiveStandingEntry[]>;
}

export interface LiveMatchStateData {
  minute: number | null;
  period: number | null;
  period_description: string;
  home_stats: Record<string, string | number> | null;
  away_stats: Record<string, string | number> | null;
}

// WebSocket message types
export type WSMessageType = 'connected' | 'prediction_update' | 'live_event' | 'match_status_change' | 'match_state_update' | 'feed_status' | 'accuracy_update' | 'ping' | 'pong';

export interface WSMessage {
  type: WSMessageType;
  match_id?: string;
  payload?: unknown;
}

export interface LiveEvent {
  id: number;
  match_id: number;
  external_event_id: string;
  event_type: 'goal' | 'yellow_card' | 'red_card' | 'substitution' | 'halftime' | 'fulltime';
  player_name: string | null;
  minute: number;
  home_score_after: number;
  away_score_after: number;
  created_at: string;
}
