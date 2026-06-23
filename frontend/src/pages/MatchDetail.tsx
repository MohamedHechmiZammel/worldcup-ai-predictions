import { useParams, Link } from 'react-router-dom';
import { useMatch, usePredictionHistory } from '../hooks/useMatch';
import { useWebSocket } from '../hooks/useWebSocket';
import { usePredictionsStore } from '../store/predictions';
import ProbabilityBar from '../components/ProbabilityBar';
import FactorsPanel from '../components/FactorsPanel';
import LiveBadge from '../components/LiveBadge';
import LiveEventLog from '../components/LiveEventLog';
import FeedStatusBanner from '../components/FeedStatusBanner';
import { getFlag } from '../utils/flags';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { Factor } from '../types';

export default function MatchDetail() {
  const { id } = useParams<{ id: string }>();
  const matchId = Number(id);

  const { data: match, isLoading } = useMatch(matchId);
  const { data: history } = usePredictionHistory(matchId);
  const { connectionState } = useWebSocket(matchId);

  const livePrediction = usePredictionsStore(s => s.predictions[matchId]);
  const liveEvents = usePredictionsStore(s => s.liveEvents[matchId] ?? []);
  const feedAvailable = usePredictionsStore(s => s.feedStatus[matchId] ?? true);

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

  const prediction = livePrediction ?? match.prediction;
  const factors: Factor[] = prediction?.top_factors ?? [];

  const chartData = (history?.predictions ?? []).map((p, i) => ({
    name: `#${i + 1}`,
    home: Math.round(p.home_win_prob * 100),
    draw: Math.round(p.draw_prob * 100),
    away: Math.round(p.away_win_prob * 100),
  }));

  const showScore = match.status === 'live' || match.status === 'halftime' || match.status === 'finished';
  const homeFlag = getFlag(match.home_team?.country_code);
  const awayFlag = getFlag(match.away_team?.country_code);

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
            <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded ${
              connectionState === 'connected'  ? 'text-green-400 bg-green-500/10' :
              connectionState === 'connecting' ? 'text-gold bg-gold/10' :
                                                'text-slate-600 bg-slate-800'
            }`}>
              {connectionState === 'connected'  ? '● WS' :
               connectionState === 'connecting' ? '○ WS' : '○ WS'}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-4">
        <FeedStatusBanner available={feedAvailable} lastUpdated={new Date()} />

        {/* ── Scoreboard card ── */}
        <div className="bg-card rounded-2xl border border-white/5 overflow-hidden">
          {/* Stage label */}
          <div className="px-6 pt-5 pb-2 flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-widest text-slate-600 font-medium">{match.stage}</span>
            {match.venue && (
              <span className="text-[11px] text-slate-600 truncate ml-4 max-w-[200px] text-right">
                {match.venue}, {match.city}
              </span>
            )}
          </div>

          {/* Teams + score */}
          <div className="flex items-center justify-between px-6 pb-6 gap-4">
            {/* Home */}
            <div className="flex-1 flex flex-col items-center gap-2">
              <span className="text-5xl leading-none select-none">{homeFlag}</span>
              <p className="text-base font-bold text-white text-center">{match.home_team?.name ?? 'Home'}</p>
              <p className="text-[11px] text-slate-600 uppercase tracking-widest">{match.home_team?.country_code}</p>
            </div>

            {/* Center: score or time */}
            <div className="flex-shrink-0 text-center">
              {showScore ? (
                <span className={`font-display text-6xl font-black leading-none tracking-tight${
                  match.status === 'live' ? ' text-gold' : ' text-white'
                }`}>
                  {match.home_score ?? 0}–{match.away_score ?? 0}
                </span>
              ) : (
                <span className="font-display text-xl font-bold text-slate-600 tracking-widest">VS</span>
              )}
            </div>

            {/* Away */}
            <div className="flex-1 flex flex-col items-center gap-2">
              <span className="text-5xl leading-none select-none">{awayFlag}</span>
              <p className="text-base font-bold text-white text-center">{match.away_team?.name ?? 'Away'}</p>
              <p className="text-[11px] text-slate-600 uppercase tracking-widest">{match.away_team?.country_code}</p>
            </div>
          </div>
        </div>

        {/* ── AI Prediction ── */}
        {prediction && match.status !== 'finished' && (
          <div className="bg-card rounded-2xl border border-white/5 p-5 space-y-5">
            <div className="flex items-center justify-between">
              <p className="text-[10px] uppercase tracking-widest text-slate-600">AI Prediction</p>
              {prediction.expected_home_goals !== undefined && (
                <p className="text-[11px] text-slate-500">
                  xG: <span className="text-slate-300 font-medium tabular-nums">
                    {prediction.expected_home_goals.toFixed(1)} – {prediction.expected_away_goals.toFixed(1)}
                  </span>
                </p>
              )}
            </div>
            <ProbabilityBar
              homeWinProb={prediction.home_win_prob}
              drawProb={prediction.draw_prob}
              awayWinProb={prediction.away_win_prob}
              homeTeamName={match.home_team?.name ?? 'Home'}
              awayTeamName={match.away_team?.name ?? 'Away'}
              confidenceLow={prediction.confidence_low}
              confidenceHigh={prediction.confidence_high}
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
            <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-4">Probability Timeline</p>
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
        {(match.status === 'live' || match.status === 'halftime' || liveEvents.length > 0) && (
          <div className="bg-card rounded-2xl border border-white/5 p-5">
            <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-4">Match Events</p>
            <LiveEventLog events={liveEvents} />
          </div>
        )}
      </main>
    </div>
  );
}
