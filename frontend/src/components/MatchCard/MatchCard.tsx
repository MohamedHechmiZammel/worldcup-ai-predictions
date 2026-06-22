import React from 'react';
import type { Match, Factor } from '../../types';
import ProbabilityBar from '../ProbabilityBar';
import FactorsPanel from '../FactorsPanel';
import LiveBadge from '../LiveBadge';
import AIResultBadge from './AIResultBadge';
import { usePredictionsStore } from '../../store/predictions';

interface MatchCardProps {
  match: Match;
  onClick?: () => void;
}

const isScoreVisible = (status: Match['status']): boolean =>
  status === 'live' || status === 'halftime' || status === 'finished';

const MatchCard: React.FC<MatchCardProps> = ({ match, onClick }) => {
  const livePrediction = usePredictionsStore(s => s.predictions[match.id]);
  const effectivePrediction = livePrediction ?? match.prediction;

  const {
    home_team,
    away_team,
    home_score,
    away_score,
    status,
    stage,
    venue,
    city,
    scheduled_at,
  } = match;

  const showScore = isScoreVisible(status);
  const showPrediction = !!effectivePrediction && status !== 'finished';

  const topFactors: Factor[] = effectivePrediction?.top_factors?.slice(0, 3) ?? [];
  const hasLimitedData = showPrediction && topFactors.length < 3;

  const venueCity = [venue, city].filter(Boolean).join(', ');

  return (
    <div
      className={`bg-gray-800 rounded-lg p-4 border border-gray-700 flex flex-col gap-3${
        onClick ? ' cursor-pointer hover:ring-1 hover:ring-blue-500 transition-shadow' : ''
      }`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); } : undefined}
    >
      {/* Top row: LiveBadge + venue/city */}
      <div className="flex items-center justify-between gap-2">
        <LiveBadge status={status} scheduledAt={scheduled_at} />
        {venueCity && (
          <span className="text-xs text-gray-400 truncate text-right">{venueCity}</span>
        )}
      </div>

      {/* Teams row */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-white flex-1 text-left truncate">
          {home_team?.name ?? 'Home Team'}
        </span>

        {showScore ? (
          <span className={`text-2xl font-bold whitespace-nowrap${status === 'live' ? ' text-yellow-300' : ' text-white'}`}>
            {home_score ?? 0} – {away_score ?? 0}
          </span>
        ) : (
          <span className="text-sm text-gray-400 whitespace-nowrap">vs</span>
        )}

        <span className="text-sm font-semibold text-white flex-1 text-right truncate">
          {away_team?.name ?? 'Away Team'}
        </span>
      </div>

      {/* Stage label */}
      {stage && (
        <span className="text-xs text-gray-500 uppercase tracking-wide">{stage}</span>
      )}

      {/* Prediction section */}
      {showPrediction && effectivePrediction ? (
        <div className="flex flex-col gap-2">
          <ProbabilityBar
            homeWinProb={effectivePrediction.home_win_prob}
            drawProb={effectivePrediction.draw_prob}
            awayWinProb={effectivePrediction.away_win_prob}
            homeTeamName={home_team?.name ?? 'Home'}
            awayTeamName={away_team?.name ?? 'Away'}
            confidenceLow={effectivePrediction.confidence_low}
            confidenceHigh={effectivePrediction.confidence_high}
          />

          {topFactors.length > 0 && (
            <FactorsPanel factors={topFactors} />
          )}

          {hasLimitedData && (
            <span className="inline-flex self-start items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-900 text-yellow-300 border border-yellow-700">
              Limited data
            </span>
          )}
        </div>
      ) : status === 'finished' ? (
        <div className="flex flex-col gap-2">
          <span className="text-xs text-gray-500 italic">Final Result</span>
          {match.accuracy && (
            <AIResultBadge
              wasCorrect={match.accuracy.was_correct}
              predictedOutcome={match.accuracy.predicted_outcome}
              actualOutcome={match.accuracy.actual_outcome}
            />
          )}
        </div>
      ) : null}
    </div>
  );
};

export default MatchCard;
