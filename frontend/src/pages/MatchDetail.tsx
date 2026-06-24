import { useParams, Link } from 'react-router-dom';
import { useMatch, useMatchStats, usePredictionHistory } from '../hooks/useMatch';
import { useWebSocket } from '../hooks/useWebSocket';
import { usePredictionsStore } from '../store/predictions';
import ProbabilityBar from '../components/ProbabilityBar';
import FactorsPanel from '../components/FactorsPanel';
import LiveBadge from '../components/LiveBadge';
import LiveEventLog from '../components/LiveEventLog';
import LiveStatsPanel from '../components/LiveStatsPanel/LiveStatsPanel';
import FeedStatusBanner from '../components/FeedStatusBanner';
import { getFlag } from '../utils/flags';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { Factor } from '../types';

const OUTCOME_LABEL: Record<string, string> = {
  home_win: 'Home Win',
  draw: 'Draw',
  away_win: 'Away Win',
};

export default function MatchDetail() {
  const { id } = useParams<{ id: string }>();
  const matchId = Number(id);

  const { data: match, isLoading } = useMatch(matchId);
  const { data: history } = usePredictionHistory(matchId);
  const { data: restStats } = useMatchStats(matchId, match?.status);
  const { connectionState } = useWebSocket(matchId);

  const livePrediction = usePredictionsStore(s => s.predictions[matchId]);
  const liveEvents = usePredictionsStore(s => s.liveEvents[matchId]) ?? [];
  const feedAvailable = usePredictionsStore(s => s.feedStatus[matchId] ?? true);
  const liveMatchState = usePredictionsStore(s => s.liveMatchState[matchId]);

  // WebSocket data is most current for live matches; REST is used for finished or initial load
  const displayStats = liveMatchState ?? (restStats?.available ? restStats : null);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-pitch flex items-center justify-center">
        <span className="font-display text-4xl font-bold text-gold animate-pulse">Loading…</span>
      </div>
    );
  }

  if (!match) {
    return (
      <div className="min-h-screen bg-pitch p-8">
        <Link to="/" className="text-gold text-sm hover:text-gold-bright">← All Matches</Link>
        <p className="text-red-400 mt-4">Match not found.</p>
      </div>
    );
  }

  const isFinished = match.status === 'finished';
  const isLive = match.status === 'live' || match.status === 'halftime';
  const isUpcoming = match.status === 'scheduled';

  // For live/upcoming: use live WS prediction or fallback to API prediction
  // For finished: always show the static pre-match prediction from API (for comparison)
  const displayPrediction = isFinished ? match.prediction : (livePrediction ?? match.prediction);
  const factors: Factor[] = displayPrediction?.top_factors ?? [];

  const chartData = (history?.predictions ?? []).map((p, i) => ({
    name: `#${i + 1}`,
    home: Math.round(p.home_win_prob * 100),
    draw: Math.round(p.draw_prob * 100),
    away: Math.round(p.away_win_prob * 100),
  }));

  const homeFlag = getFlag(match.home_team?.country_code);
  const awayFlag = getFlag(match.away_team?.country_code);

  // Determine actual outcome label for finished matches
  const actualOutcome = match.accuracy?.actual_outcome ?? null;
  const predictedOutcome = match.accuracy?.predicted_outcome ?? null;
  const wasCorrect = match.accuracy?.was_correct ?? null;

  return (
    <div className="min-h-screen bg-pitch text-slate-100">
      {/* ── Header ── */}
      <header className="sticky top-0 z-20 bg-pitch/95 backdrop-blur border-b border-white/5 px-4 sm:px-6 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-slate-500 hover:text-white transition-colors text-sm group">
            <span className="group-hover:-translate-x-0.5 transition-transform">←</span>
            <span className="font-display font-bold tracking-wide">ALL MATCHES</span>
          </Link>
          <div className="flex items-center gap-3">
            <LiveBadge status={match.status} scheduledAt={match.scheduled_at} />
            {(isLive || isUpcoming) && (
              <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded ${
                connectionState === 'connected'  ? 'text-green-400 bg-green-500/10' :
                connectionState === 'connecting' ? 'text-gold bg-gold/10' :
                                                  'text-slate-600 bg-slate-800'
              }`}>
                {connectionState === 'connected' ? '● WS' : '○ WS'}
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-4">
        {isLive && <FeedStatusBanner available={feedAvailable} lastUpdated={new Date()} />}

        {/* ── Match stats: live (WebSocket) or final (REST) ── */}
        {(isLive || isFinished) && displayStats && (
          <LiveStatsPanel
            matchState={displayStats}
            homeTeamName={match.home_team?.name ?? 'Home'}
            awayTeamName={match.away_team?.name ?? 'Away'}
            isFinished={isFinished}
          />
        )}

        {/* ── Scoreboard card ── */}
        <div className="bg-card rounded-2xl border border-white/5 overflow-hidden">
          <div className="px-6 pt-5 pb-2 flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-widest text-slate-600 font-medium">{match.stage}</span>
            {match.venue && (
              <span className="text-[11px] text-slate-600 truncate ml-4 max-w-[200px] text-right">
                {match.venue}, {match.city}
              </span>
            )}
          </div>

          <div className="flex items-center justify-between px-6 pb-6 gap-4">
            <div className="flex-1 flex flex-col items-center gap-2">
              <span className="text-5xl leading-none select-none">{homeFlag}</span>
              <p className="text-base font-bold text-white text-center">{match.home_team?.name ?? 'Home'}</p>
              <p className="text-[11px] text-slate-600 uppercase tracking-widest">{match.home_team?.country_code}</p>
            </div>

            <div className="flex-shrink-0 text-center min-w-[100px]">
              {isFinished || isLive ? (
                <span className={`font-display text-6xl font-black leading-none tracking-tight ${
                  isLive ? 'text-gold' : 'text-white'
                }`}>
                  {match.home_score ?? 0}–{match.away_score ?? 0}
                </span>
              ) : (
                <div className="space-y-1">
                  <span className="font-display text-xl font-bold text-slate-600 tracking-widest block">VS</span>
                  <p className="text-[11px] text-slate-500 tabular-nums">
                    {new Date(match.scheduled_at).toLocaleDateString('en-GB', {
                      day: 'numeric', month: 'short',
                    })}
                  </p>
                  <p className="text-[11px] text-slate-400 tabular-nums font-medium">
                    {new Date(match.scheduled_at).toLocaleTimeString('en-GB', {
                      hour: '2-digit', minute: '2-digit',
                    })} UTC
                  </p>
                </div>
              )}
            </div>

            <div className="flex-1 flex flex-col items-center gap-2">
              <span className="text-5xl leading-none select-none">{awayFlag}</span>
              <p className="text-base font-bold text-white text-center">{match.away_team?.name ?? 'Away'}</p>
              <p className="text-[11px] text-slate-600 uppercase tracking-widest">{match.away_team?.country_code}</p>
            </div>
          </div>
        </div>

        {/* ── Finished: AI prediction vs actual result ── */}
        {isFinished && (
          <div className="bg-card rounded-2xl border border-white/5 overflow-hidden">
            {/* Accuracy badge */}
            {wasCorrect !== null && (
              <div className={`px-5 py-3 flex items-center gap-2 text-sm font-bold border-b ${
                wasCorrect
                  ? 'bg-green-500/10 border-green-500/20 text-green-400'
                  : 'bg-red-500/10 border-red-500/20 text-red-400'
              }`}>
                <span className="text-base">{wasCorrect ? '✓' : '✗'}</span>
                <span>AI {wasCorrect ? 'Predicted Correctly' : 'Got This Wrong'}</span>
                {predictedOutcome && (
                  <span className="ml-auto text-[11px] font-normal opacity-75">
                    Predicted: {OUTCOME_LABEL[predictedOutcome] ?? predictedOutcome}
                    {actualOutcome && predictedOutcome !== actualOutcome && (
                      <> · Actual: {OUTCOME_LABEL[actualOutcome] ?? actualOutcome}</>
                    )}
                  </span>
                )}
              </div>
            )}

            <div className="p-5 space-y-5">
              <div className="flex items-center justify-between">
                <p className="text-[10px] uppercase tracking-widest text-slate-600">
                  AI Pre-Match Prediction
                </p>
                {displayPrediction?.expected_home_goals !== undefined && (
                  <p className="text-[11px] text-slate-500">
                    xG: <span className="text-slate-300 font-medium tabular-nums">
                      {displayPrediction.expected_home_goals.toFixed(1)} – {displayPrediction.expected_away_goals.toFixed(1)}
                    </span>
                  </p>
                )}
              </div>

              {displayPrediction ? (
                <ProbabilityBar
                  homeWinProb={displayPrediction.home_win_prob}
                  drawProb={displayPrediction.draw_prob}
                  awayWinProb={displayPrediction.away_win_prob}
                  homeTeamName={match.home_team?.name ?? 'Home'}
                  awayTeamName={match.away_team?.name ?? 'Away'}
                  confidenceLow={displayPrediction.confidence_low}
                  confidenceHigh={displayPrediction.confidence_high}
                />
              ) : (
                <p className="text-slate-600 text-sm">No pre-match prediction on record.</p>
              )}

              {factors.length > 0 && (
                <div className="pt-3 border-t border-white/[0.06]">
                  <FactorsPanel factors={factors} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Live / Upcoming: AI prediction ── */}
        {!isFinished && displayPrediction && (
          <div className="bg-card rounded-2xl border border-white/5 p-5 space-y-5">
            <div className="flex items-center justify-between">
              <p className="text-[10px] uppercase tracking-widest text-slate-600">
                {isLive ? 'Live AI Prediction' : 'AI Pre-Match Prediction'}
              </p>
              {displayPrediction.expected_home_goals !== undefined && (
                <p className="text-[11px] text-slate-500">
                  xG: <span className="text-slate-300 font-medium tabular-nums">
                    {displayPrediction.expected_home_goals.toFixed(1)} – {displayPrediction.expected_away_goals.toFixed(1)}
                  </span>
                </p>
              )}
            </div>
            <ProbabilityBar
              homeWinProb={displayPrediction.home_win_prob}
              drawProb={displayPrediction.draw_prob}
              awayWinProb={displayPrediction.away_win_prob}
              homeTeamName={match.home_team?.name ?? 'Home'}
              awayTeamName={match.away_team?.name ?? 'Away'}
              confidenceLow={displayPrediction.confidence_low}
              confidenceHigh={displayPrediction.confidence_high}
            />
            {factors.length > 0 && (
              <div className="pt-3 border-t border-white/[0.06]">
                <FactorsPanel factors={factors} />
              </div>
            )}
          </div>
        )}

        {/* ── Probability timeline ── */}
        {chartData.length > 1 && (
          <div className="bg-card rounded-2xl border border-white/5 p-5">
            <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-4">Prediction Timeline</p>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={chartData}>
                <XAxis dataKey="name" tick={{ fill: '#475569', fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#475569', fontSize: 10 }} width={28} />
                <Tooltip
                  contentStyle={{ background: '#0F172A', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, fontSize: 11 }}
                  labelStyle={{ color: '#94A3B8' }}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: '#64748B' }} />
                <Line type="monotone" dataKey="home" stroke="#3B82F6" strokeWidth={2} dot={false} name="Home %" />
                <Line type="monotone" dataKey="draw"  stroke="#475569" strokeWidth={2} dot={false} name="Draw %" />
                <Line type="monotone" dataKey="away"  stroke="#EF4444" strokeWidth={2} dot={false} name="Away %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* ── Live event log ── */}
        {(isLive || liveEvents.length > 0) && (
          <div className="bg-card rounded-2xl border border-white/5 p-5">
            <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-4">Match Events</p>
            <LiveEventLog events={liveEvents} />
          </div>
        )}
      </main>
    </div>
  );
}
