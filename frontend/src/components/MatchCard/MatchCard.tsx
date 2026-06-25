import React from 'react';
import type { Match, Factor } from '../../types';
import LiveBadge from '../LiveBadge';
import AIResultBadge from './AIResultBadge';
import FlagIcon from '../FlagIcon';
import { usePredictionsStore } from '../../store/predictions';

interface MatchCardProps {
  match: Match;
  onClick?: () => void;
}

const isScoreVisible = (s: Match['status']) =>
  s === 'live' || s === 'halftime' || s === 'finished';

function pct(v: number) { return Math.round(v * 100); }

const MatchCard: React.FC<MatchCardProps> = ({ match, onClick }) => {
  const livePrediction = usePredictionsStore(s => s.predictions[match.id]);
  const effectivePrediction = livePrediction ?? match.prediction;

  const showScore = isScoreVisible(match.status);
  const showPrediction = !!effectivePrediction && match.status !== 'finished';

  const homePct = pct(effectivePrediction?.home_win_prob ?? 0);
  const drawPct = pct(effectivePrediction?.draw_prob ?? 0);
  const awayPct = pct(effectivePrediction?.away_win_prob ?? 0);

  const dominant =
    homePct >= awayPct && homePct >= drawPct ? 'home'
    : awayPct > homePct && awayPct >= drawPct ? 'away'
    : 'draw';

  const topFactors: Factor[] = effectivePrediction?.top_factors?.slice(0, 2) ?? [];

  return (
    <div
      className={`bg-card rounded-xl border border-white/5 flex flex-col overflow-hidden transition-all duration-200${
        onClick ? ' cursor-pointer hover:border-gold/40 hover:shadow-lg hover:shadow-black/40 hover:-translate-y-0.5' : ''
      }`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? e => { if (e.key === 'Enter' || e.key === ' ') onClick(); } : undefined}
    >
      {/* ── Meta row: date + city ── */}
      <div className="flex items-center justify-between px-4 pt-3 pb-1">
        <LiveBadge status={match.status} scheduledAt={match.scheduled_at} />
        {match.city && (
          <span className="text-[11px] text-slate-600 truncate ml-2 max-w-[130px] text-right">
            {match.city}
          </span>
        )}
      </div>

      {/* ── Teams row ── */}
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Home team */}
        <div className="flex-1 flex flex-col items-center gap-1.5 min-w-0">
          <FlagIcon countryCode={match.home_team?.country_code} size="lg" />
          <span className="text-xs font-semibold text-slate-200 text-center leading-tight w-full truncate">
            {match.home_team?.name ?? 'Home'}
          </span>
        </div>

        {/* Score / VS */}
        <div className="flex-shrink-0 text-center w-14">
          {showScore ? (
            <span className={`font-display text-3xl font-black leading-none tracking-tight${
              match.status === 'live' ? ' text-gold' : ' text-white'
            }`}>
              {match.home_score ?? 0}–{match.away_score ?? 0}
            </span>
          ) : (
            <span className="font-display text-sm font-bold text-slate-600 tracking-widest">VS</span>
          )}
        </div>

        {/* Away team */}
        <div className="flex-1 flex flex-col items-center gap-1.5 min-w-0">
          <FlagIcon countryCode={match.away_team?.country_code} size="lg" />
          <span className="text-xs font-semibold text-slate-200 text-center leading-tight w-full truncate">
            {match.away_team?.name ?? 'Away'}
          </span>
        </div>
      </div>

      {/* ── Prediction triptych ── */}
      {showPrediction && (
        <div className="border-t border-white/[0.06]">
          {/* Three probability columns */}
          <div className="grid grid-cols-3 px-3 pt-3 pb-1.5">
            {/* Home */}
            <div className={`flex flex-col items-center gap-0.5 transition-opacity ${dominant === 'home' ? 'opacity-100' : 'opacity-40'}`}>
              <span className="font-display text-4xl font-black leading-none text-blue-400">
                {homePct}
              </span>
              <span className="text-[9px] uppercase tracking-widest text-slate-500">Home</span>
            </div>
            {/* Draw */}
            <div className={`flex flex-col items-center gap-0.5 transition-opacity ${dominant === 'draw' ? 'opacity-100' : 'opacity-40'}`}>
              <span className="font-display text-4xl font-black leading-none text-slate-400">
                {drawPct}
              </span>
              <span className="text-[9px] uppercase tracking-widest text-slate-500">Draw</span>
            </div>
            {/* Away */}
            <div className={`flex flex-col items-center gap-0.5 transition-opacity ${dominant === 'away' ? 'opacity-100' : 'opacity-40'}`}>
              <span className="font-display text-4xl font-black leading-none text-red-400">
                {awayPct}
              </span>
              <span className="text-[9px] uppercase tracking-widest text-slate-500">Away</span>
            </div>
          </div>

          {/* Thin probability bar */}
          <div className="flex h-0.5 mx-4 mb-3 overflow-hidden rounded-full bg-slate-800">
            <div className="bg-blue-500 transition-all duration-700" style={{ width: `${homePct}%` }} />
            <div className="bg-slate-500 transition-all duration-700" style={{ width: `${drawPct}%` }} />
            <div className="bg-red-500 transition-all duration-700" style={{ width: `${awayPct}%` }} />
          </div>

          {/* Key factors */}
          {topFactors.length > 0 && (
            <div className="px-4 pb-3 space-y-0.5 border-t border-white/[0.04] pt-2">
              {topFactors.map(f => (
                <p key={f.feature} className="text-[10px] text-slate-500 leading-snug truncate">
                  {f.label}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Finished state ── */}
      {match.status === 'finished' && (
        <div className="border-t border-white/[0.06] px-4 py-2.5 flex flex-col gap-1.5">
          <span className="text-[10px] uppercase tracking-widest text-slate-600">Full Time</span>
          {match.accuracy && (
            <AIResultBadge
              wasCorrect={match.accuracy.was_correct}
              predictedOutcome={match.accuracy.predicted_outcome}
              actualOutcome={match.accuracy.actual_outcome}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default MatchCard;
