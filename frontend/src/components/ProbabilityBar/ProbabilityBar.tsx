import React from 'react';

interface ProbabilityBarProps {
  homeWinProb: number;
  drawProb: number;
  awayWinProb: number;
  homeTeamName: string;
  awayTeamName: string;
  confidenceLow?: number;
  confidenceHigh?: number;
}

function pct(v: number) { return Math.round(v * 100); }

const ProbabilityBar: React.FC<ProbabilityBarProps> = ({
  homeWinProb, drawProb, awayWinProb,
  homeTeamName, awayTeamName,
  confidenceLow, confidenceHigh,
}) => {
  const h = pct(homeWinProb);
  const d = pct(drawProb);
  const a = pct(awayWinProb);
  const dominant = h >= a && h >= d ? 'home' : a > h && a >= d ? 'away' : 'draw';

  return (
    <div className="space-y-3">
      {/* Big numbers */}
      <div className="grid grid-cols-3">
        <div className={`flex flex-col items-center gap-1 ${dominant === 'home' ? 'opacity-100' : 'opacity-50'}`}>
          <span className="font-display text-5xl font-black leading-none text-blue-400">{h}</span>
          <span className="text-[10px] uppercase tracking-widest text-slate-500">Home win</span>
          <span className="text-xs text-slate-400 font-medium truncate max-w-[90px] text-center">{homeTeamName}</span>
        </div>
        <div className={`flex flex-col items-center gap-1 ${dominant === 'draw' ? 'opacity-100' : 'opacity-50'}`}>
          <span className="font-display text-5xl font-black leading-none text-slate-400">{d}</span>
          <span className="text-[10px] uppercase tracking-widest text-slate-500">Draw</span>
        </div>
        <div className={`flex flex-col items-center gap-1 ${dominant === 'away' ? 'opacity-100' : 'opacity-50'}`}>
          <span className="font-display text-5xl font-black leading-none text-red-400">{a}</span>
          <span className="text-[10px] uppercase tracking-widest text-slate-500">Away win</span>
          <span className="text-xs text-slate-400 font-medium truncate max-w-[90px] text-center">{awayTeamName}</span>
        </div>
      </div>

      {/* Bar */}
      <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div className="bg-blue-500 transition-all duration-700" style={{ width: `${h}%` }} />
        <div className="bg-slate-500 transition-all duration-700" style={{ width: `${d}%` }} />
        <div className="bg-red-500 transition-all duration-700" style={{ width: `${a}%` }} />
      </div>

      {/* Confidence interval */}
      {confidenceLow !== undefined && confidenceHigh !== undefined && (
        <p className="text-center text-[11px] text-slate-600">
          Model confidence interval: {pct(confidenceLow)}%–{pct(confidenceHigh)}%
        </p>
      )}
    </div>
  );
};

export default ProbabilityBar;
