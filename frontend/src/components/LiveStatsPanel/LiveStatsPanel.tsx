import type { LiveMatchStateData } from '../../types';

interface LiveStatsPanelProps {
  matchState: LiveMatchStateData;
  homeTeamName: string;
  awayTeamName: string;
}

function StatRow({
  label,
  home,
  away,
}: {
  label: string;
  home: string | number | undefined;
  away: string | number | undefined;
}) {
  const h = home ?? '—';
  const a = away ?? '—';
  return (
    <div className="flex items-center justify-between text-[11px] tabular-nums">
      <span className="text-slate-300 font-medium w-8 text-right">{h}</span>
      <span className="text-slate-500 text-[10px] uppercase tracking-widest flex-1 text-center">{label}</span>
      <span className="text-slate-300 font-medium w-8 text-left">{a}</span>
    </div>
  );
}

export default function LiveStatsPanel({ matchState, homeTeamName, awayTeamName }: LiveStatsPanelProps) {
  const { minute, period_description, home_stats, away_stats } = matchState;

  const homePoss = parseFloat(String(home_stats?.possessionPct ?? 50));
  const awayPoss = parseFloat(String(away_stats?.possessionPct ?? 50));

  const clockLabel = minute != null && minute > 0
    ? `${minute}'${period_description ? ` · ${period_description}` : ''}`
    : period_description || 'Live';

  return (
    <div className="bg-card rounded-2xl border border-white/5 p-5 space-y-4">
      {/* Header with live clock */}
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-widest text-slate-600">Live Stats</p>
        <span className="text-[11px] font-bold text-gold tabular-nums">{clockLabel}</span>
      </div>

      {/* Team name labels */}
      <div className="flex justify-between text-[10px] text-slate-500 uppercase tracking-widest">
        <span className="truncate max-w-[120px]">{homeTeamName}</span>
        <span className="truncate max-w-[120px] text-right">{awayTeamName}</span>
      </div>

      {/* Possession bar */}
      <div>
        <div className="flex h-2 rounded-full overflow-hidden">
          <div
            className="bg-blue-500 transition-all duration-700"
            style={{ width: `${homePoss}%` }}
          />
          <div
            className="bg-red-500 transition-all duration-700"
            style={{ width: `${awayPoss}%` }}
          />
        </div>
        <div className="flex justify-between mt-1 text-[10px] text-slate-400 tabular-nums">
          <span>{homePoss.toFixed(0)}%</span>
          <span className="text-slate-600 uppercase tracking-widest text-[9px]">Possession</span>
          <span>{awayPoss.toFixed(0)}%</span>
        </div>
      </div>

      {/* Key stats */}
      <div className="space-y-2 pt-1 border-t border-white/[0.06]">
        <StatRow
          label="Shots on Target"
          home={home_stats?.shotsOnTarget}
          away={away_stats?.shotsOnTarget}
        />
        <StatRow
          label="Corners"
          home={home_stats?.wonCorners}
          away={away_stats?.wonCorners}
        />
        <StatRow
          label="Fouls"
          home={home_stats?.foulsCommitted}
          away={away_stats?.foulsCommitted}
        />
      </div>
    </div>
  );
}
