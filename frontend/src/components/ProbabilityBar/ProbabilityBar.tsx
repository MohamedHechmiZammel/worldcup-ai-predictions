import React from 'react';

interface ProbabilityBarProps {
  homeWinProb: number;   // 0-1
  drawProb: number;      // 0-1
  awayWinProb: number;   // 0-1
  homeTeamName: string;
  awayTeamName: string;
  confidenceLow?: number;
  confidenceHigh?: number;
}

function toPercent(value: number): number {
  return Math.round(value * 1000) / 10;
}

const ProbabilityBar: React.FC<ProbabilityBarProps> = ({
  homeWinProb,
  drawProb,
  awayWinProb,
  homeTeamName,
  awayTeamName,
  confidenceLow,
  confidenceHigh,
}) => {
  const homePct = toPercent(homeWinProb);
  const drawPct = toPercent(drawProb);
  const awayPct = toPercent(awayWinProb);

  const homeIsFavored = homeWinProb > 0.55 && homeWinProb >= awayWinProb;
  const awayIsFavored = awayWinProb > 0.55 && awayWinProb > homeWinProb;

  const showCI =
    confidenceLow !== undefined && confidenceHigh !== undefined;

  return (
    <div className="w-full space-y-2">
      {/* Team name labels */}
      <div className="flex justify-between items-start text-sm">
        {/* Home team */}
        <div className="flex flex-col items-start">
          <span className="font-semibold text-white truncate max-w-[120px]">
            {homeTeamName}
          </span>
          <span className="text-blue-400 font-mono text-xs">{homePct}%</span>
          {homeIsFavored && (
            <span className="mt-0.5 text-xs text-blue-300 font-medium tracking-wide uppercase">
              Favored
            </span>
          )}
        </div>

        {/* Draw label (center) */}
        <div className="flex flex-col items-center">
          <span className="text-gray-400 text-xs font-medium uppercase tracking-wider">
            Draw
          </span>
          <span className="text-gray-300 font-mono text-xs">{drawPct}%</span>
        </div>

        {/* Away team */}
        <div className="flex flex-col items-end">
          <span className="font-semibold text-white truncate max-w-[120px]">
            {awayTeamName}
          </span>
          <span className="text-red-400 font-mono text-xs">{awayPct}%</span>
          {awayIsFavored && (
            <span className="mt-0.5 text-xs text-red-300 font-medium tracking-wide uppercase">
              Favored
            </span>
          )}
        </div>
      </div>

      {/* Probability bar */}
      <div className="flex h-4 w-full overflow-hidden rounded-sm bg-gray-800">
        {/* Home segment */}
        <div
          className="bg-blue-600 transition-all duration-700 ease-in-out"
          style={{ width: `${homePct}%` }}
          role="presentation"
          aria-label={`${homeTeamName} win probability: ${homePct}%`}
        />
        {/* Draw segment */}
        <div
          className="bg-gray-500 transition-all duration-700 ease-in-out"
          style={{ width: `${drawPct}%` }}
          role="presentation"
          aria-label={`Draw probability: ${drawPct}%`}
        />
        {/* Away segment */}
        <div
          className="bg-red-600 transition-all duration-700 ease-in-out"
          style={{ width: `${awayPct}%` }}
          role="presentation"
          aria-label={`${awayTeamName} win probability: ${awayPct}%`}
        />
      </div>

      {/* Confidence interval */}
      {showCI && (
        <div className="flex justify-center">
          <span className="text-xs text-gray-500">
            CI: {toPercent(confidenceLow!)}%&ndash;{toPercent(confidenceHigh!)}%
          </span>
        </div>
      )}
    </div>
  );
};

export default ProbabilityBar;
